# CZI to OME-ZARR Converter — MagicGUI Application

A graphical interface built with **MagicGUI** (Qt/PyQt5 backend) for converting Carl Zeiss Image (CZI) files to OME-ZARR format.

## Features

- File browser for `.czi` file selection
- Automatic metadata extraction and validation
- Multiple conversion modes:
  - Standard OME-ZARR (single scene)
  - HCS (High Content Screening) multi-well plate layout
- Two backend libraries: **ngff-zarr** (recommended) and **ome-zarr-py**
- Single-file OME-ZARR archive (`.ozx`) output — ngff-zarr only
- Scene selector for multi-scene files (non-HCS mode)
- Live conversion log viewer updated in real time
- Optional napari visualization after conversion
- Smart UI state management (controls disabled/enabled based on mode and backend)

---

## Running the Application

```bash
# From within scripts_and_notebooks/
conda activate omezarr
python run_czi_converter_gui.py

# From repo root
conda run -n omezarr python scripts_and_notebooks/run_czi_converter_gui.py
```

### Integration as a napari dock widget

```python
import napari
from czi_to_omezarr_gui import create_gui

viewer = napari.Viewer()
converter_widget = create_gui()
viewer.window.add_dock_widget(converter_widget, name="CZI Converter")
napari.run()
```


## Workflow

1. **Select CZI File** — use the file browser (`.czi` filter)
2. **Read Metadata** — click the *Read Metadata* button to:
   - Parse CZI metadata via `CziMetadata`
   - Determine the number of scenes
   - Populate the metadata summary in the Status panel
   - Enable the *Convert to OME-ZARR* button
3. **Configure options** — see [Widget Reference](#widget-reference) below
4. **Convert** — click *Convert to OME-ZARR*; conversion runs in a background thread
   while the log viewer updates live every 500 ms
5. **View results** — check the Conversion Log panel; optionally open in napari

---

## Widget Reference

### `@magicgui` Widget — `czi_to_omezarr_converter`

| Widget                                | Type            | Description                                                                                |
| ------------------------------------- | --------------- | ------------------------------------------------------------------------------------------ |
| **CZI File**                          | File browser    | Input `.czi` file; filtered to `*.czi`                                                     |
| **OME-ZARR Package**                  | Dropdown        | Backend: *ngff-zarr (Recommended)* or *ome-zarr-py*                                        |
| **Write HCS Layout**                  | Checkbox        | Enable HCS multi-well plate output format                                                  |
| **Use Single-File OME-ZARR (.ozx)**   | Checkbox        | Master toggle for `.ozx` archive output (ngff-zarr only)                                   |
| **Create OZX archive during writing** | Checkbox        | Write directly into a zip archive while converting (disabled in HCS mode — see note below) |
| **Create OZX archive after writing**  | Checkbox        | Write a directory-based store first, then zip it into `.ozx` afterwards                    |
| **Scene ID**                          | Integer spinner | Scene index to convert (only visible in non-HCS mode with multiple scenes)                 |
| **Show in napari After Conversion**   | Checkbox        | Auto-open the result in a napari viewer (disabled when OZX output is selected)             |

### Additional Controls (outside the `@magicgui` widget)

| Widget                                       | Description                                                         |
| -------------------------------------------- | ------------------------------------------------------------------- |
| **Read Metadata** (`PushButton`)             | Loads CZI metadata, unlocks the convert button                      |
| **Convert to OME-ZARR** (`PushButton`)       | Starts the background conversion thread; disabled during conversion |
| **Status** (`TextEdit`, read-only)           | Shows metadata summary, conversion status, and errors               |
| **Conversion Log** (`TextEdit`, read-only)   | Live log viewer polling the log file every 500 ms                   |
| **Package Versions** (`TextEdit`, read-only) | Displays installed version of zarr, ome-zarr, ngff-zarr             |

---

## Smart UI State Rules

### OZX mode (`Use Single-File OME-ZARR (.ozx)`)

- Only enabled when backend is **ngff-zarr**; switching to ome-zarr-py disables and unchecks it.
- The two sub-options are **mutually exclusive** — checking one unchecks the other.
- When the master toggle is turned on, exactly one sub-option must be active.
  If neither is checked, *Create OZX archive after writing* is auto-selected as the safe default.
- **Create OZX archive during writing** is always **disabled in HCS mode**.
  The HCS pipeline (`convert_czi2hcs_ngff`) must write a complete directory tree before
  it can be zipped; streaming directly into a zip archive is not supported for HCS.
- A re-entrancy guard (`_ozx_state_updating`) prevents signal cascades when the auto-select
  logic changes a checkbox value and that change would otherwise trigger further callbacks.

### Scene selector visibility

Visible only when:
- NOT in HCS mode (`write_hcs == False`)
- AND the file has more than one scene

### napari integration

- *Show in napari After Conversion* is **disabled** whenever the conversion will produce an `.ozx`
  archive, because `napari-ome-zarr` can only open directory-based OME-ZARR stores.

### Convert button

- Disabled until *Read Metadata* has been successfully completed for the currently selected file.
- Disabled again while a conversion is running; re-enabled on completion.

---

## Output File Naming

| Mode           | Backend                | Output                                                           |
| -------------- | ---------------------- | ---------------------------------------------------------------- |
| Standard       | ome-zarr-py            | `{stem}.ome.zarr`                                                |
| Standard       | ngff-zarr (directory)  | `{stem}_ngff.ome.zarr`                                           |
| Standard       | ngff-zarr (OZX direct) | `{stem}_ngff.ozx`                                                |
| Standard       | ngff-zarr (OZX after)  | `{stem}_ngff.ome.zarr` → zipped to `{stem}_ngff.ozx`             |
| HCS            | ome-zarr-py            | `{stem}_HCSplate.ome.zarr`                                       |
| HCS            | ngff-zarr (directory)  | `{stem}_ngff_plate.ome.zarr`                                     |
| HCS            | ngff-zarr (OZX after)  | `{stem}_ngff_plate.ome.zarr` → zipped to `{stem}_ngff_plate.ozx` |
| Conversion log | any                    | `{stem}_conversion.log` (written alongside the input CZI)        |

---

## Threading and Logging Architecture

Conversion runs in a **daemon thread** to avoid blocking the Qt event loop:

1. `on_convert_clicked()` spawns `run_conversion()` in a `threading.Thread(daemon=True)`.
2. A `QTimer` fires every 500 ms on the **main thread** calling `check_conversion_status()`,
   which reads new bytes from the log file (incremental seek via `log_last_position`) and
   appends them to the Conversion Log widget.
3. When the thread sets `conversion_result["completed"] = True`, the timer triggers
   `finish_conversion()`, which stops the timer, does a final full read of the log file,
   and optionally opens napari.

> **Note:** Closing the application window terminates the daemon thread without cleanup.

---

## Global State Variables

| Variable              | Type                    | Purpose                                           |
| --------------------- | ----------------------- | ------------------------------------------------- |
| `metadata`            | `Optional[CziMetadata]` | Metadata for the currently loaded CZI             |
| `max_scenes`          | `int`                   | Scene count from the current CZI                  |
| `selected_file`       | `Optional[Path]`        | Path the metadata was read from                   |
| `conversion_running`  | `bool`                  | True while a conversion thread is active          |
| `log_file_path`       | `Optional[Path]`        | Path to the active conversion log                 |
| `log_last_position`   | `int`                   | Byte offset for incremental log reading           |
| `log_timer`           | `Optional[QTimer]`      | Timer driving the live log updates                |
| `napari_viewer_path`  | `Optional[str]`         | Kept for compatibility (currently unused)         |
| `_ozx_state_updating` | `bool`                  | Re-entrancy guard for `update_ozx_child_states()` |

---

## Callback Functions

| Function                                   | Trigger                         | Purpose                                                             |
| ------------------------------------------ | ------------------------------- | ------------------------------------------------------------------- |
| `on_file_changed(value)`                   | File selector changed           | Resets state; adjusts selector width; disables convert button       |
| `on_read_metadata_clicked()`               | Read Metadata button            | Loads `CziMetadata`, updates scene selector, enables convert button |
| `on_package_choice_changed(value)`         | Package dropdown changed        | Enables/disables OZX master toggle                                  |
| `on_write_hcs_changed(value)`              | HCS checkbox changed            | Controls scene selector visibility; adjusts OZX sub-options         |
| `on_use_ozx_format_changed(_)`             | OZX master toggle changed       | Synchronises child checkbox states                                  |
| `on_use_ozx_write_directly_changed(value)` | Direct-write checkbox changed   | Enforces mutual exclusion with after-writing option                 |
| `on_use_ozx_after_writing_changed(value)`  | After-writing checkbox changed  | Enforces mutual exclusion with direct-write option                  |
| `on_convert_clicked()`                     | Convert button                  | Validates state; starts thread and QTimer                           |
| `update_ozx_child_states()`                | Called by multiple callbacks    | Central logic for OZX enabled/value/auto-select rules               |
| `update_use_ozx_format_enabled_state()`    | Called by package/HCS callbacks | Controls master OZX toggle availability                             |
| `update_show_napari_enabled_state()`       | Called after OZX state changes  | Disables napari option when OZX output is configured                |
| `finish_conversion(output_path, ...)`      | QTimer (on completion)          | Stops timer, flushes log, optionally opens napari, re-enables UI    |

---

## Conversion Backends

### ngff-zarr (Recommended)

- Writes OME-NGFF v0.5
- Multi-resolution pyramid via `write_omezarr_ngff()` with configurable `scale_factors`
- Supports direct-to-zip `.ozx` output
- OMERO channel metadata embedded in `zarr.json`

> **Version warning:** `ngff-zarr 0.29.0` on PyPI has a null-byte bug in `from_ngff_zarr.py`.
> Pin to `ngff-zarr==0.28.1` until fixed upstream.

### ome-zarr-py

- Stable, widely used OME-ZARR writer
- Does **not** support `.ozx` output (OZX controls disabled when this backend is selected)

---

## Conversion Logic

`perform_conversion()` delegates to utility functions in `ome_zarr_utils.py`:

| Mode                   | Function                    |
| ---------------------- | --------------------------- |
| HCS + ome-zarr-py      | `convert_czi2hcs_omezarr()` |
| HCS + ngff-zarr        | `convert_czi2hcs_ngff()`    |
| HCS + OZX after        | `convert_hcs_omezarr2ozx()` |
| Standard + ome-zarr-py | `write_omezarr()`           |
| Standard + ngff-zarr   | `write_omezarr_ngff()`      |

---

## Error Handling

| Condition                                | Behaviour                                                 |
| ---------------------------------------- | --------------------------------------------------------- |
| File does not exist                      | Status panel shows error; convert blocked                 |
| Metadata read failed                     | Status panel shows error; convert blocked                 |
| Convert clicked before Read Metadata     | Status panel warning; convert blocked                     |
| OZX master on but no sub-option selected | Status panel warning; convert blocked                     |
| Conversion exception                     | Traceback printed to console; Status panel shows failure  |
| napari open failed                       | Warning printed to console; does not block result display |

---

## Requirements

```
magicgui >= 0.7.0
qtpy
PyQt5
napari >= 0.4.18
napari-ome-zarr
czitools >= 0.50.0
ome-zarr >= 0.8.0
ngff-zarr == 0.28.1   # 0.29.0 has a known null-byte bug on PyPI
zarr >= 3.0.0
```

---

## License

Copyright(c) 2025 Carl Zeiss AG, Germany. All Rights Reserved.

Permission is granted to use, modify and distribute this code,
as long as this copyright notice remains part of the code.


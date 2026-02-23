# GitHub Copilot Instructions — CZI OME-ZARR Playground

## Project Overview

This repository is a playground for converting Carl Zeiss Image (CZI) files to OME-ZARR format. It supports:

- Standard OME-ZARR and HCS (High Content Screening / multi-well plate) layouts
- Two backend libraries: **ngff-zarr** (recommended) and **ome-zarr-py**
- Single-file OME-ZARR archives (`.ozx` format, ngff-zarr only)
- A MagicGUI desktop application for interactive conversion
- CLI scripts for batch/automated conversion
- Jupyter and Marimo notebooks for exploration
- HCS plate analysis (object counting, heatmap generation)
- Optional napari visualization of results

---

## Repository Structure

```
omezarr_playground/
├── data/                           # Sample CZI input files
│   ├── CellDivision5D.czi          # Standard 5D CZI (TCZYX), no HCS
│   └── WP96_4Pos_B4-10_DAPI.czi   # 96-well plate CZI for HCS conversion
├── images/                         # Documentation images
├── scripts_and_notebooks/          # All working code lives here
│   ├── ome_zarr_utils.py           # Core conversion library (primary utility module)
│   ├── czi_to_omezarr_gui.py       # MagicGUI application (main GUI module)
│   ├── run_czi_converter_gui.py    # Launcher for the GUI application
│   ├── convert2omezarr.py          # CLI: standard OME-ZARR conversion
│   ├── convert2hcs_omezarr.py      # CLI: HCS plate conversion
│   ├── create_omezarr_example.py   # Standalone example script
│   ├── processing_tools.py         # Image analysis utilities (ArrayProcessor)
│   ├── plotting_utils.py           # Heatmap/visualization utilities
│   ├── process_hcs_omezarr.py      # HCS plate processing script
│   ├── process_hcsplate_example.py # HCS plate processing example
│   ├── visualize_omezarr_heatmap_marimo.py  # Marimo notebook for heatmaps
│   ├── create_omezarr_marimo.py    # Marimo notebook for conversion
│   └── *.ipynb                     # Jupyter notebooks for exploration
├── env_omezarr.yml                 # Conda environment definition
├── README.md
└── _archive/                       # Older/reference scripts (do not modify)
```

---

## Python Environment

- **Conda environment name:** `omezarr`
- **Python version:** 3.13
- **Environment file:** `env_omezarr.yml`

### Environment Management

```bash
# Create
conda env create --file env_omezarr.yml

# Update
conda env update --name omezarr --file env_omezarr.yml --prune

# Activate
conda activate omezarr

# Remove
conda remove --name omezarr --all
```

### Key Dependencies

| Package | Role |
|---|---|
| `ngff-zarr` (≤0.28.x recommended) | Primary OME-ZARR write backend |
| `ome-zarr` | Secondary OME-ZARR write backend |
| `czitools` | CZI metadata parsing and array reading |
| `pylibCZIrw` | Low-level CZI reading via libCZIrw |
| `aicspylibczi` | Alternative CZI reader |
| `zarr` | Zarr v3 storage backend |
| `dask` | Lazy parallel array computation |
| `xarray` | Labelled N-D arrays (dimension names: STCZYX) |
| `magicgui` | Qt-based GUI widget framework |
| `napari` | Interactive image viewer |
| `napari-ome-zarr` | napari plugin to open OME-ZARR files |
| `scikit-image` | Image processing (filtering, segmentation, morphology) |
| `marimo` | Reactive notebook framework |

> **Note:** `ngff-zarr 0.29.0` on PyPI has a known bug — `from_ngff_zarr.py` in the published wheel contains null bytes. Use `ngff-zarr==0.28.1` until this is fixed upstream.

---

## Core Module: `ome_zarr_utils.py`

This is the primary utility module. All conversion functions should be imported from here.

### Enums

```python
from ome_zarr_utils import omezarr_package

omezarr_package.NGFF_ZARR  # ngff-zarr backend (recommended)
omezarr_package.OME_ZARR   # ome-zarr-py backend
```

### Key Functions

| Function | Description |
|---|---|
| `setup_logging(log_file_path, force_reconfigure)` | Configure root logger with file + console handlers |
| `write_omezarr(array, zarr_path, metadata, overwrite)` | Write 5D xarray (TCZYX) using ome-zarr-py |
| `write_omezarr_ngff(array, zarr_path, metadata, scale_factors, overwrite)` | Write 5D xarray using ngff-zarr with multi-resolution pyramid |
| `convert_czi2hcs_omezarr(czi_filepath, overwrite, log_file_path)` | Full CZI→HCS-ZARR pipeline using ome-zarr-py |
| `convert_czi2hcs_ngff(czi_filepath, overwrite, write_ozx_directly, log_file_path)` | Full CZI→HCS-ZARR pipeline using ngff-zarr |
| `convert_hcs_omezarr2ozx(zarr_path, remove_omezarr)` | Convert existing HCS-ZARR directory to `.ozx` zip archive |
| `extract_well_coordinates(well_counter)` | Parse well IDs (e.g. `"B4"`) into row/col/path lists |

### Array Convention

All arrays are **5D xarray DataArrays** with labelled dimensions in order `(T, C, Z, Y, X)`. When reading from CZI with `read_tools.read_6darray()`, the result is a 6D array `(S, T, C, Z, Y, X)` — squeeze the `S` (Scene) dimension before passing to write functions:

```python
array, mdata = read_tools.read_6darray(filepath, planes={"S": (scene_id, scene_id)}, use_xarray=True)
array = array.squeeze("S")  # → 5D (T, C, Z, Y, X)
```

---

## GUI Application: `czi_to_omezarr_gui.py`

Built with **MagicGUI** on a Qt backend (PyQt5/qtpy). The application runs a background thread for conversion to avoid blocking the UI, and uses a `QTimer` to poll the log file and update the log widget on the main thread.

### Module-Level Global State

| Variable | Type | Purpose |
|---|---|---|
| `metadata` | `Optional[CziMetadata]` | Metadata from the currently loaded CZI file |
| `max_scenes` | `int` | Scene count from current CZI |
| `selected_file` | `Optional[Path]` | Path of the file metadata was read from |
| `conversion_running` | `bool` | Conversion in-progress flag |
| `log_file_path` | `Optional[Path]` | Path to the active conversion log |
| `log_last_position` | `int` | Byte offset for incremental log reading |
| `log_timer` | `Optional[QTimer]` | Timer for periodic log polling |

### Widget Interaction Pattern

1. User selects a `.czi` file → `on_file_changed()` clears state
2. User clicks **Read Metadata** → `on_read_metadata_clicked()` loads `CziMetadata`, updates scene selector
3. User clicks **Convert to OME-ZARR** → `on_convert_clicked()` starts background thread, starts `QTimer`
4. `QTimer` calls `check_conversion_status()` every 500 ms → updates log viewer
5. On completion, `finish_conversion()` stops timer, flushes final log, optionally opens napari

### OZX Option Rules (enforced by UI callbacks)

- `.ozx` is only available when backend is `NGFF_ZARR`
- **Write directly** and **Write afterwards** are mutually exclusive
- **Write directly** is disabled in HCS mode (HCS uses write-afterwards only)

### Running the GUI

```bash
# From within scripts_and_notebooks/
conda activate omezarr
python run_czi_converter_gui.py

# From repo root
conda run -n omezarr python scripts_and_notebooks/run_czi_converter_gui.py
```

---

## CLI Scripts

### Standard OME-ZARR Conversion

```bash
python convert2omezarr.py --czifile ../data/CellDivision5D.czi --use_ngffzarr --scales [2,4] --overwrite
```

Options: `--czifile`, `--use_ngffzarr` / `--use_omezarr`, `--zarr`, `--scales`, `--overwrite`, `--validate`, `--scene`

### HCS Plate Conversion

```bash
python convert2hcs_omezarr.py --czifile ../data/WP96_4Pos_B4-10_DAPI.czi --use_ngffzarr --plate "MyPlate" --overwrite
```

Options: `--czifile`, `--use_ngffzarr` / `--use_omezarr`, `--zarr`, `--plate`, `--overwrite`, `--validate`

---

## Output File Naming Conventions

| Mode | Backend | Output filename |
|---|---|---|
| Standard | ome-zarr-py | `<stem>.ome.zarr` |
| Standard | ngff-zarr | `<stem>_ngff.ome.zarr` |
| Standard (OZX direct) | ngff-zarr | `<stem>_ngff.ozx` |
| HCS | ome-zarr-py | `<stem>_HCSplate.ome.zarr` |
| HCS | ngff-zarr | `<stem>_ngff_plate.ome.zarr` |
| Conversion log | any | `<stem>_conversion.log` |

---

## Image Analysis

### `processing_tools.py` — `ArrayProcessor`

Operates on 2D NumPy arrays. Chain operations via method calls:

```python
proc = ArrayProcessor(array_2d)
filtered = proc.apply_gaussian_filter(sigma=2)
```

Methods: `apply_gaussian_filter`, `apply_median_filter`, `apply_triangle_threshold`, `apply_threshold`, `count_objects`

### `plotting_utils.py` — `create_well_plate_heatmap`

Renders a seaborn heatmap from a `Dict[str, float]` with well keys in `"row/col"` format (e.g. `"B/4"`):

```python
from plotting_utils import create_well_plate_heatmap
fig = create_well_plate_heatmap(results, num_rows=8, num_cols=12)
```

---

## Coding Conventions

- **Type hints** on all function signatures; use `Optional[T]` for nullable values
- **Google-style docstrings** with `Args:`, `Returns:`, and `Note:` sections
- **`pathlib.Path`** for all file paths (not raw strings), except where third-party APIs require strings
- **`logging`** module throughout (not `print`) in library code; `print` is acceptable in GUI callbacks for user-facing messages
- `setup_logging()` must be called before any log output is expected; pass `force_reconfigure=True` when starting a new conversion job
- Guard all top-level script execution with `if __name__ == "__main__":`
- Use **`@unique`** decorator on all `Enum` classes
- Pydantic `validate_arguments` / `Field` used in `processing_tools.py` for runtime validation
- **Dask arrays** are preferred for large data; avoid materialising full arrays into memory

---

## Common Patterns

### Reading a CZI file

```python
from czitools.read_tools import read_tools
array, mdata = read_tools.read_6darray(filepath, planes={"S": (0, 0)}, use_xarray=True)
array = array.squeeze("S")  # → 5D xarray (T, C, Z, Y, X)
```

### Writing with ngff-zarr (recommended)

```python
from ome_zarr_utils import write_omezarr_ngff
write_omezarr_ngff(array, zarr_output_path, mdata, scale_factors=[2, 4], overwrite=True)
```

### Writing with ome-zarr-py

```python
from ome_zarr_utils import write_omezarr
write_omezarr(array, zarr_path=str(zarr_output_path), metadata=mdata, overwrite=True)
```

### Validating output with ngff-zarr

```python
import ngff_zarr as nz
multiscales = nz.from_ngff_zarr(zarr_output_path, validate=True)
hcs = nz.from_hcs_zarr(zarr_output_path, validate=True)  # for HCS
```

### Opening in napari

```python
import napari
viewer = napari.Viewer()
viewer.open(zarr_output_path, plugin="napari-ome-zarr")
napari.run()
```

---

## Known Issues & Notes

- **`ngff-zarr 0.29.0` is broken** — `from_ngff_zarr.py` contains null bytes in the PyPI wheel. Pin to `ngff-zarr==0.28.1`.
- `zarr` v3 is installed; some older ome-zarr-py patterns expecting zarr v2 store APIs may need adjustment (`parse_url`, `zarr.open_group` kwargs differ slightly).
- The `~ygments-*.dist-info` ghost directory can appear in the conda env if a `pip install` is interrupted mid-run. Remove it with `Remove-Item -LiteralPath` (PowerShell) or `rm -rf` (bash).
- The GUI uses **PyQt5** via `qtpy`. Do not mix Qt bindings — keep `QT_API=pyqt5` consistent.
- Background conversion threads are `daemon=True` — closing the window will terminate them without cleanup.
- Log files are written alongside the input CZI file (same directory).

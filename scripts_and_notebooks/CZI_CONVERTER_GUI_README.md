# CZI to OME-ZARR Converter - MagicGUI Application

A user-friendly graphical interface for converting Carl Zeiss Image (CZI) files to OME-ZARR format with support for HCS (High Content Screening) layouts and multiple backend libraries.

## Features

✨ **Key Capabilities:**
- 📁 File browser for CZI file selection
- 🔍 Automatic metadata extraction and validation
- 🎛️ Multiple conversion options:
  - Single-file OME-ZARR (.ozx format)
  - HCS multi-well plate layouts
  - Choice of backend (ngff-zarr or ome-zarr-py)
  - Scene selection for multi-scene files
- 🖼️ Optional napari visualization after conversion
- 📊 Real-time status updates and metadata display
- 🔒 Smart UI state management (disabled controls until metadata is loaded)

## Installation

```bash
# Install required dependencies
pip install magicgui napari[all] czitools ome-zarr-py ngff-zarr

# Or if using conda
conda install -c conda-forge magicgui napari czitools
pip install ome-zarr-py ngff-zarr
```

## Usage

### Standalone Application

```bash
python czi_to_omezarr_gui.py
```

Or use the launcher script:

```bash
python run_czi_converter_gui.py
```

### Integration with napari

```python
import napari
from czi_to_omezarr_gui import create_gui

# Create napari viewer
viewer = napari.Viewer()

# Add converter as docked widget
converter_widget = create_gui()
viewer.window.add_dock_widget(converter_widget, name="CZI Converter")

napari.run()
```

### Programmatic Usage

```python
from pathlib import Path
from czi_to_omezarr_gui import create_gui

# Create the GUI
gui = create_gui()

# Access the main converter widget
converter = gui[0]  # First widget in container

# Programmatically set values
converter.czi_file.value = Path("path/to/file.czi")
converter.write_hcs.value = True
converter.package_choice.value = omezarr_package.NGFF_ZARR

# Show the GUI
gui.show(run=True)
```

## Workflow

1. **Select CZI File**: Use the file browser to choose your input CZI file

2. **Read Metadata**: Click "Read Metadata" button to:
   - Load file metadata
   - Determine number of scenes
   - Enable conversion options
   - Display file information

3. **Configure Options**:
   - ☑️ **Use Single-File OME-ZARR (.ozx)**: Enable OZX format
   - ☑️ **Write HCS Layout**: For multi-well plate data
   - ☑️ **Show in napari After Conversion**: Auto-open result
   - 📦 **OME-ZARR Package**: Choose backend (ngff-zarr recommended)
   - 🔢 **Scene ID**: Select scene (only visible for multi-scene, non-HCS files)

4. **Convert**: Click "Convert to OME-ZARR" to start processing

5. **View Results**: Check status display and optionally view in napari

## UI Components

### Main Converter Widget
- **CZI File**: File browser with .czi filter
- **Use Single-File OME-ZARR (.ozx)**: Checkbox for OZX format
- **Write HCS Layout**: Checkbox for HCS multi-well format
- **Show in napari After Conversion**: Checkbox for auto-visualization
- **OME-ZARR Package**: Dropdown with backend choices
- **Scene ID**: Slider (conditional visibility)
- **Convert to OME-ZARR**: Main action button (disabled until metadata read)

### Additional Controls
- **Read Metadata**: Button to load and validate CZI metadata
- **Status Display**: Text area showing metadata info and conversion status

## Smart UI Behavior

### Scene Selector Visibility
The scene ID slider is only visible when:
- NOT in HCS mode (`write_hcs == False`)
- AND file has multiple scenes (`num_scenes > 1`)

### Button State Management
- **Convert button**: Disabled until metadata is successfully read
- Ensures users follow correct workflow

### Status Updates
Real-time feedback during:
- Metadata loading
- Conversion progress
- Error conditions
- Success confirmation

## Output

### File Naming Convention
- **HCS OME-ZARR**: `{input_name}_HCSplate.ome.zarr`
- **Standard OME-ZARR (ome-zarr-py)**: `{input_name}.ome.zarr`
- **Standard OME-ZARR (ngff-zarr)**: `{input_name}_ngff.ome.zarr`

### Log Files
Conversion log saved as: `{input_name}_conversion.log`

## Backend Packages

### ngff-zarr (Recommended)
- ✅ Latest OME-NGFF v0.5 specification
- ✅ Multi-resolution pyramids
- ✅ Optimized chunking
- ✅ OMERO metadata support

### ome-zarr-py
- ✅ Stable and widely used
- ✅ Comprehensive OME-ZARR support
- ✅ Good napari integration

## Examples

### Example 1: Simple Conversion
```python
# 1. Select file: "sample.czi"
# 2. Click "Read Metadata"
# 3. Keep default settings (ngff-zarr, no HCS)
# 4. Click "Convert to OME-ZARR"
# Result: sample_ngff.ome.zarr
```

### Example 2: HCS Plate Conversion
```python
# 1. Select file: "plate_scan.czi"
# 2. Click "Read Metadata"
# 3. Enable "Write HCS Layout"
# 4. Click "Convert to OME-ZARR"
# Result: plate_scan_HCSplate.ome.zarr (with plate/well structure)
```

### Example 3: Multi-Scene Selection
```python
# 1. Select file: "multi_scene.czi" (e.g., 10 scenes)
# 2. Click "Read Metadata"
# 3. Scene ID slider appears (range 0-9)
# 4. Select scene 5
# 5. Click "Convert to OME-ZARR"
# Result: Converts only scene 5
```

## Error Handling

The application provides clear error messages for:
- ❌ File not found
- ❌ Metadata reading failures
- ❌ Conversion errors
- ⚠️ Attempting conversion before reading metadata

## Technical Details

### Global State Management
- `metadata`: Stores loaded CziMetadata object
- `max_scenes`: Number of scenes in current file
- `selected_file`: Path to current CZI file

### Callback Functions
- `on_read_metadata_clicked()`: Handles metadata loading
- `on_write_hcs_changed()`: Controls scene selector visibility

### Conversion Logic
Delegates to utility functions in `ome_zarr_utils.py`:
- `convert_czi2hcs_omezarr()`: HCS with ome-zarr-py
- `convert_czi2hcs_ngff()`: HCS with ngff-zarr
- `write_omezarr()`: Standard with ome-zarr-py
- `write_omezarr_ngff()`: Standard with ngff-zarr

## Requirements

```
magicgui >= 0.7.0
napari >= 0.4.18
czitools >= 0.50.0
ome-zarr-py >= 0.8.0
ngff-zarr >= 0.5.0
```

## License

Copyright(c) 2025 Carl Zeiss AG, Germany. All Rights Reserved.

Permission is granted to use, modify and distribute this code,
as long as this copyright notice remains part of the code.

## Support

For issues or questions:
- Check the console output for detailed error messages
- Review the conversion log file
- Verify CZI file is not corrupted

## Future Enhancements

Potential features for future versions:
- [ ] Batch conversion of multiple files
- [ ] Custom output path selection
- [ ] Advanced chunking options
- [ ] Progress bar for long conversions
- [ ] Preset configurations
- [ ] Export settings to JSON

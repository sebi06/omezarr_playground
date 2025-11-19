# -*- coding: utf-8 -*-

#################################################################
# File        : czi_to_omezarr_gui.py
# Author      : sebi06
# Institution : Carl Zeiss Microscopy GmbH
#
# Copyright(c) 2025 Carl Zeiss AG, Germany. All Rights Reserved.
#
# Permission is granted to use, modify and distribute this code,
# as long as this copyright notice remains part of the code.
#################################################################

"""
MagicGUI Application for CZI to OME-ZARR Conversion

This application provides a graphical user interface for converting Carl Zeiss Image (CZI)
files to OME-ZARR format with support for:
- Single-file OME-ZARR (.ozx) format
- HCS (High Content Screening) multi-well plate layouts
- Multiple conversion backends (ome-zarr-py and ngff-zarr)
- Interactive visualization with napari
"""

from pathlib import Path
from typing import Optional
from magicgui import magicgui, widgets
from czitools.metadata_tools.czi_metadata import CziMetadata
from ome_zarr_utils import (
    omezarr_package,
    convert_czi2hcs_omezarr,
    convert_czi2hcs_ngff,
    write_omezarr,
    write_omezarr_ngff,
    setup_logging,
)
from czitools.read_tools import read_tools
import logging
import threading
from qtpy.QtCore import QTimer
import ome_zarr.format
import zarr
import ngff_zarr as nz
from importlib.metadata import version


# Module-level variables to store application state
metadata: Optional[CziMetadata] = None
max_scenes: int = 1
selected_file: Optional[Path] = None
conversion_running: bool = False
log_file_path: Optional[Path] = None
log_last_position: int = 0
log_timer: Optional[QTimer] = None
napari_viewer_path: Optional[str] = None  # Store path for napari to open on main thread

try:
    parent_dir = Path(__file__).parent.parent / "data"
except ValueError:
    parent_dir = None


def update_log_display():
    """Update log viewer with new content from log file (called by timer)."""
    global log_last_position, log_file_path

    if log_file_path and log_file_path.exists():
        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                f.seek(log_last_position)
                new_content = f.read()
                if new_content:
                    log_viewer.value += new_content
                    log_last_position = f.tell()
        except Exception as e:
            print(f"Log update error: {e}")


def read_czi_metadata(filepath: Path):
    """Read metadata from a CZI file and determine the number of scenes.

    Args:
        filepath: Path to the CZI file

    Returns:
        tuple: (CziMetadata object or None, maximum number of scenes)

    Note:
        Returns (None, 1) if metadata reading fails
    """
    try:
        # Read CZI metadata using czitools
        mdata = CziMetadata(filepath)

        # Determine number of scenes
        num_scenes = mdata.image.SizeS if hasattr(mdata.image, "SizeS") else None

        # Calculate max_scenes: if None or 0, default to 1
        max_scenes = num_scenes if num_scenes and num_scenes > 0 else 1

        print("✓ Metadata loaded successfully")
        print(f"  - File: {filepath.name}")
        print(f"  - Dimensions: {mdata.aics_dims_shape}")
        print(f"  - Number of scenes: {max_scenes}")

        return mdata, max_scenes

    except Exception as e:
        print(f"✗ Error reading metadata: {e}")
        return None, 1


def perform_conversion(
    filepath: Path,
    use_ozx: bool,
    write_hcs: bool,
    show_napari: bool,
    package_choice: omezarr_package,
    scene_id: int,
) -> Optional[str]:
    """
    Perform the CZI to OME-ZARR conversion with specified parameters.

    Args:
        filepath: Path to input CZI file
        use_ozx: Enable single-file OME-ZARR format (.ozx)
        write_hcs: Enable HCS (multi-well plate) layout
        show_napari: Open result in napari viewer after conversion
        package_choice: Backend package (OME_ZARR or NGFF_ZARR)
        scene_id: Scene index to convert (for non-HCS mode with multiple scenes)

    Returns:
        str: Path to output OME-ZARR file, or None if conversion failed
    """
    try:
        # Setup logging
        log_file_path = filepath.parent / f"{filepath.stem}_conversion.log"
        setup_logging(str(log_file_path), force_reconfigure=True)
        logger = logging.getLogger(__name__)

        logger.info("=" * 80)
        logger.info("CZI to OME-ZARR Conversion Started")
        logger.info("=" * 80)
        logger.info(f"Input file: {filepath}")
        logger.info(f"Package: {package_choice.name}")
        logger.info(f"HCS mode: {write_hcs}")
        logger.info(f"Single-file (.ozx): {use_ozx}")
        logger.info(f"Scene ID: {scene_id}")

        output_path = None

        # ========== HCS Format Conversion ==========
        if write_hcs:
            print(f"🔄 Converting to HCS-ZARR format using {package_choice.name}...")

            if package_choice == omezarr_package.OME_ZARR:
                output_path = convert_czi2hcs_omezarr(
                    czi_filepath=str(filepath), overwrite=True, log_file_path=str(log_file_path)
                )
            elif package_choice == omezarr_package.NGFF_ZARR:
                output_path = convert_czi2hcs_ngff(
                    czi_filepath=str(filepath), overwrite=True, log_file_path=str(log_file_path)
                )

            print(f"✅ HCS-ZARR created: {output_path}")

        # ========== Standard OME-ZARR Conversion ==========
        else:
            print(f"🔄 Converting scene {scene_id} to OME-ZARR format using {package_choice.name}...")

            # Read the CZI file as a 6D array
            array, mdata = read_tools.read_6darray(str(filepath), planes={"S": (scene_id, scene_id)}, use_xarray=True)

            # Extract the specified scene (remove Scene dimension to get 5D array)
            array = array.squeeze("S")
            print(f"📊 Array shape: {array.shape}, dtype: {array.dtype}")

            if package_choice == omezarr_package.OME_ZARR:
                # Generate output path
                zarr_output_path = Path(str(filepath)[:-4] + ".ome.zarr")

                # Write OME-ZARR using ome-zarr-py backend
                output_path = write_omezarr(array, zarr_path=str(zarr_output_path), metadata=mdata, overwrite=True)
                print(f"✅ OME-ZARR created: {output_path}")

            elif package_choice == omezarr_package.NGFF_ZARR:
                # Generate output path
                zarr_output_path = Path(str(filepath)[:-4] + "_ngff.ome.zarr")

                # Write OME-ZARR using ngff-zarr backend
                _ = write_omezarr_ngff(array, zarr_output_path, mdata, scale_factors=[2, 4], overwrite=True)
                output_path = str(zarr_output_path)
                print(f"✅ OME-ZARR created: {output_path}")

        # Note: napari viewer will be opened on main thread after conversion completes

        logger.info("=" * 80)
        logger.info("Conversion completed successfully!")
        logger.info(f"Output: {output_path}")
        logger.info("=" * 80)

        return output_path

    except Exception as e:
        print(f"✗ Conversion failed: {e}")
        import traceback

        traceback.print_exc()
        return None


# ============================================================================
# MagicGUI Widget Definition
# ============================================================================


@magicgui(
    call_button=False,
    layout="vertical",
    czi_file={
        "label": "CZI File",
        "mode": "r",
        "filter": "*.czi",
    },
    use_ozx={
        "label": "Use Single-File OME-ZARR (.ozx)",
        "tooltip": "Enable OZX format for single-file OME-ZARR storage",
    },
    write_hcs={
        "label": "Write HCS Layout",
        "tooltip": "Enable HCS (High Content Screening) multi-well plate format",
    },
    show_napari={
        "label": "Show in napari After Conversion",
        "tooltip": "Automatically open the result in napari viewer",
    },
    package_choice={
        "label": "OME-ZARR Package",
        "choices": [("ngff-zarr (Recommended)", omezarr_package.NGFF_ZARR), ("ome-zarr-py", omezarr_package.OME_ZARR)],
        "tooltip": "Choose the backend library for OME-ZARR writing",
    },
    scene_id={
        "label": "Scene ID",
        "min": 0,
        "max": 0,
        "tooltip": "Select scene to convert (only for non-HCS mode with multiple scenes)",
        "visible": False,
    },
)
def czi_to_omezarr_converter(
    czi_file: Path = Path(),
    use_ozx: bool = False,
    write_hcs: bool = False,
    show_napari: bool = False,
    package_choice: omezarr_package = omezarr_package.NGFF_ZARR,
    scene_id: int = 0,
):
    """
    Main widget for CZI to OME-ZARR conversion configuration.

    This widget holds all the conversion parameters.
    The @magicgui decorator creates the actual widget from the parameter definitions above.
    The function parameters must match the decorator configuration keys.
    """
    pass  # This function doesn't need to do anything - it just holds the widgets


# ============================================================================
# Additional Control Widgets
# ============================================================================

# Create "Read Metadata" button
read_metadata_button = widgets.PushButton(
    text="Read Metadata",
    tooltip="Load CZI file metadata and enable conversion options",
)

# Create info display widget
info_display = widgets.TextEdit(
    value="Select a CZI file and click 'Read Metadata' to begin",
    label="Status",
    enabled=False,
)

# Create "Convert to OME-ZARR" button (separate from the main widget)
convert_button = widgets.PushButton(
    text="Convert to OME-ZARR",
    tooltip="Start the conversion process",
    enabled=False,  # Disabled until metadata is read
)

# Create log viewer widget
log_viewer = widgets.TextEdit(
    value="",
    label="Conversion Log",
    enabled=True,  # Enable to allow scrolling
)
log_viewer.min_height = 200  # Set minimum height for the log viewer
log_viewer.read_only = True  # Make it read-only but scrollable

# Create version info widget
try:
    version_info = f"""NGFF Version: {ome_zarr.format.CurrentFormat().version}
ZARR Package: {zarr.__version__}
NGFF-ZARR Package: {nz.__version__}
OME-ZARR Package: {version('ome-zarr')}"""
except Exception:
    version_info = "Version information unavailable"

version_grid = widgets.TextEdit(
    value=version_info,
    label="Package Versions",
    enabled=False,
)
version_grid.min_height = 60
version_grid.max_height = 80


def on_read_metadata_clicked():
    """
    Callback function for the 'Read Metadata' button.

    Reads CZI metadata and updates the GUI state accordingly.
    """
    global metadata, max_scenes, selected_file

    # Get current file path
    filepath = czi_to_omezarr_converter.czi_file.value

    if not filepath.exists():
        info_display.value = "❌ Error: File does not exist"
        return

    # Read metadata
    info_display.value = "⏳ Reading metadata..."
    metadata, max_scenes = read_czi_metadata(filepath)
    selected_file = filepath

    if metadata is None:
        info_display.value = "❌ Error: Failed to read metadata"
        return

    # Update scene slider visibility and range
    write_hcs = czi_to_omezarr_converter.write_hcs.value
    scene_selector_visible = (not write_hcs) and (max_scenes > 1)

    # Update scene_id widget
    czi_to_omezarr_converter.scene_id.visible = scene_selector_visible
    if max_scenes > 1:
        czi_to_omezarr_converter.scene_id.max = max_scenes - 1
        czi_to_omezarr_converter.scene_id.value = 0

    # Enable the convert button
    convert_button.enabled = True

    # Update info display with metadata summary
    info_text = f"""✅ Metadata loaded successfully!

📁 File: {filepath.name}
📐 Dimensions: {metadata.pyczi_dims}
🔢 Number of scenes: {max_scenes}
📊 Image size: {metadata.image.SizeX} × {metadata.image.SizeY}
🎨 Channels: {metadata.image.SizeC}
📚 Z-slices: {metadata.image.SizeZ}
⏱️ Time points: {metadata.image.SizeT}

Ready to convert!
"""
    info_display.value = info_text


def finish_conversion(output_path: Optional[str], should_open_napari: bool = False):
    """Finish conversion and update UI (called from main thread via timer)."""
    global log_timer, log_file_path

    # Stop the timer
    if log_timer:
        log_timer.stop()
        log_timer = None

    # Final log file read to ensure we got everything
    if log_file_path and log_file_path.exists():
        try:
            with open(log_file_path, "r", encoding="utf-8") as f:
                log_viewer.value = f.read()
        except Exception as e:
            log_viewer.value += f"\n⚠️ Could not read log file: {e}"

    # Open napari viewer if requested (on main thread)
    if should_open_napari and output_path:
        import napari

        print("🎨 Opening in napari viewer...")
        try:
            viewer = napari.Viewer()
            viewer.open(output_path, plugin="napari-ome-zarr")
            print("✅ Napari viewer opened successfully")
        except Exception as e:
            print(f"⚠️ Failed to open in napari: {e}")

    # Update UI
    if output_path:
        info_display.value = f"✅ Conversion successful!\n\nOutput: {output_path}"
    else:
        info_display.value = "❌ Conversion failed. Check console for details."

    # Re-enable convert button
    convert_button.enabled = True


def on_convert_clicked():
    """
    Callback function for the 'Convert to OME-ZARR' button.

    Validates inputs and performs the conversion.
    """
    global metadata, selected_file, conversion_running, log_file_path, log_last_position, log_timer

    # Get current values from the widget
    czi_file = czi_to_omezarr_converter.czi_file.value
    use_ozx = czi_to_omezarr_converter.use_ozx.value
    write_hcs = czi_to_omezarr_converter.write_hcs.value
    show_napari = czi_to_omezarr_converter.show_napari.value
    package_choice = czi_to_omezarr_converter.package_choice.value
    scene_id = czi_to_omezarr_converter.scene_id.value

    # Validate that file exists
    if not czi_file.exists():
        info_display.value = "❌ Error: Selected file does not exist"
        return

    # Validate that metadata has been read
    if metadata is None or selected_file != czi_file:
        info_display.value = "⚠️ Please click 'Read Metadata' first"
        return

    # Clear log viewer and update status
    log_viewer.value = "Starting conversion...\n"
    info_display.value = "⏳ Converting... Please wait."
    log_last_position = 0

    # Disable convert button during conversion
    convert_button.enabled = False

    # Setup log file path
    log_file_path = czi_file.parent / f"{czi_file.stem}_conversion.log"
    conversion_running = True

    # Store conversion result
    conversion_result = {"output_path": None, "completed": False, "show_napari": show_napari}

    # Start timer to update log display every 500ms
    log_timer = QTimer()

    def check_conversion_status():
        """Check if conversion is complete and update UI accordingly."""
        update_log_display()  # Update log

        # Check if conversion is complete
        if conversion_result["completed"]:
            finish_conversion(conversion_result["output_path"], conversion_result["show_napari"])

    log_timer.timeout.connect(check_conversion_status)
    log_timer.start(500)  # Update every 500ms

    def run_conversion():
        """Run conversion in background thread."""
        global conversion_running

        # Perform conversion
        output_path = perform_conversion(
            filepath=czi_file,
            use_ozx=use_ozx,
            write_hcs=write_hcs,
            show_napari=show_napari,
            package_choice=package_choice,
            scene_id=scene_id,
        )

        # Store result and mark as complete
        conversion_result["output_path"] = output_path
        conversion_result["completed"] = True
        conversion_running = False

    # Start conversion in a separate thread
    conversion_thread = threading.Thread(target=run_conversion, daemon=True)
    conversion_thread.start()


def on_write_hcs_changed(value: bool):
    """
    Callback for write_hcs checkbox changes.

    Controls visibility of scene selector based on HCS mode and scene count.
    Also disables the single-file OME-ZARR option when HCS mode is enabled.
    """
    global max_scenes

    # Show scene selector only if NOT in HCS mode AND multiple scenes exist
    scene_selector_visible = (not value) and (max_scenes > 1)
    czi_to_omezarr_converter.scene_id.visible = scene_selector_visible

    # Disable single-file OME-ZARR option when HCS mode is enabled
    czi_to_omezarr_converter.use_ozx.enabled = not value
    if value:
        czi_to_omezarr_converter.use_ozx.value = False


def on_package_choice_changed(value: omezarr_package):
    """
    Callback for package_choice changes.

    Disables the single-file OME-ZARR option when ome-zarr-py is selected.
    """
    # Disable single-file option for ome-zarr-py package
    if value == omezarr_package.OME_ZARR:
        czi_to_omezarr_converter.use_ozx.value = False
        czi_to_omezarr_converter.use_ozx.enabled = False
    else:
        # Re-enable if not in HCS mode
        write_hcs = czi_to_omezarr_converter.write_hcs.value
        czi_to_omezarr_converter.use_ozx.enabled = not write_hcs


def on_file_changed(value: Path):
    """
    Callback for file selector changes.

    Adjusts the width of the file selector to accommodate the selected file path.
    Also clears the metadata info display and log viewer when a new file is selected.
    """
    global metadata, max_scenes

    if value and value.exists():
        # Calculate width based on file path length
        # Approximate: 7 pixels per character, with min 600 and max 1200
        path_length = len(str(value))
        new_width = min(max(600, path_length * 7), 1200)
        czi_to_omezarr_converter.czi_file.min_width = new_width

        # Clear previous metadata and logs
        metadata = None
        max_scenes = 1
        info_display.value = "Select a CZI file and click 'Read Metadata' to begin."
        log_viewer.value = ""

        # Reset convert button state
        convert_button.enabled = False


# Set initial width of file selector
# The @magicgui decorator creates widget attributes from the parameter definitions
try:
    czi_to_omezarr_converter.czi_file.min_width = 600
except AttributeError as e:
    print(f"Warning: Could not set file selector width: {e}")

# Connect callbacks
read_metadata_button.clicked.connect(on_read_metadata_clicked)
convert_button.clicked.connect(on_convert_clicked)
czi_to_omezarr_converter.write_hcs.changed.connect(on_write_hcs_changed)
czi_to_omezarr_converter.package_choice.changed.connect(on_package_choice_changed)
czi_to_omezarr_converter.czi_file.changed.connect(on_file_changed)


# ============================================================================
# Main Application Container
# ============================================================================


def create_gui():
    """
    Create and return the complete GUI application.

    Returns:
        widgets.Container: The main application widget container
    """
    # Create container with all widgets
    container = widgets.Container(
        widgets=[
            version_grid,
            czi_to_omezarr_converter,
            read_metadata_button,
            info_display,
            convert_button,
            log_viewer,
        ],
        labels=False,
    )

    return container


# ============================================================================
# Standalone Execution
# ============================================================================

if __name__ == "__main__":
    """
    Run the application as a standalone Qt window.
    """
    # Create and show the GUI
    gui = create_gui()

    print("=" * 60)
    print("CZI to OME-ZARR Converter")
    print("=" * 60)
    print("\nApplication started. Close the window to exit.")

    # Set window title before showing (this blocks until the window is closed)
    gui.native.setWindowTitle("CZI --> OME-ZARR Converter Playground")
    gui.show(run=True)

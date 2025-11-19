#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple launcher script for the CZI to OME-ZARR Converter GUI.

Usage:
    python run_czi_converter_gui.py

Or integrate into napari:
    viewer = napari.Viewer()
    viewer.window.add_dock_widget(czi_to_omezarr_gui.create_gui(), name="CZI Converter")
"""

if __name__ == "__main__":
    from czi_to_omezarr_gui import create_gui

    # Create and show the GUI
    gui = create_gui()

    print("=" * 80)
    print("CZI to OME-ZARR Converter - MagicGUI Application")
    print("=" * 80)
    print("\nInstructions:")
    print("1. Select a CZI file")
    print("2. Click 'Read Metadata' to load file information")
    print("3. Configure conversion options:")
    print("   - Single-File .ozx format (optional)")
    print("   - HCS Layout for multi-well plates")
    print("   - Package choice (ngff-zarr recommended)")
    print("   - Scene ID (if multiple scenes and not HCS)")
    print("4. Click 'Convert to OME-ZARR'")
    print("\nClose the window to exit.")
    print("=" * 80)

    # Show the GUI (blocks until window is closed)
    gui.show(run=True)

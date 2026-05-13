"""
Example script demonstrating CZI to OME-ZARR conversion.

This script provides examples for converting CZI (Carl Zeiss Image) files to OME-ZARR format
in two modes:
1. HCS (High Content Screening) format - for multi-well plate data
2. Standard OME-ZARR format - for single scene data

Supports two backend libraries:
- ome-zarr-py (OME_ZARR)
- ngff-zarr (NGFF_ZARR)
"""

import logging
from czi_omezarr_utils import (
    convert_czi2hcs_omezarr,
    convert_czi2hcs_ngff,
    omezarr_package,
    write_omezarr,
    write_omezarr_ngff,
    setup_logging,
    convert_hcs_omezarr2ozx,
)
import ngff_zarr as nz
from pathlib import Path
from czitools.read_tools import read_tools
from typing import Optional


def main() -> None:
    """Main function to execute CZI to OME-ZARR conversion."""

    # ========== Configuration Parameters ==========
    # Toggle to display the result in napari viewer (requires napari installation)
    # Attention: Does not work reliably due to the napari-ome-zarr plugin !!!
    show_napari: bool = False

    # Mode selection: True for HCS (multi-well plate), False for standard OME-ZARR
    write_hcs: bool = True
    convert_hc2ozx_after_writing = False
    platename: str = "Test_Plate_01"

    # use OZX (single file zipped OME-ZARR) - only works with NGFF-ZARR package (2025-11-19)
    # NOTE: Writing directly to .ozx during HCS conversion is broken on Windows (ngff-zarr issue #241).
    # The workaround is to write to .ome.zarr first and then convert afterwards via convert_hcs_omezarr2ozx.
    # convert_czi2hcs_ngff applies this workaround automatically on Windows.
    write_ozx_directly: bool = False  # keep False on Windows; True only works reliably on Linux/macOS

    # Backend library selection: OME_ZARR (ome-zarr-py) or NGFF_ZARR (ngff-zarr)
    # NOTE: OME_ZARR (ome-zarr-py) only writes OME-NGFF spec v0.4.
    #       Use NGFF_ZARR to get spec v0.5 + zarr v3 store format.
    # ome_package = omezarr_package.OME_ZARR
    ome_package = omezarr_package.NGFF_ZARR

    # Scene ID for non-HCS format (ignored if write_hcs=True)
    scene_id: int = 0

    # ========== Input File Path ==========
    # Option 1: Use relative path to test data in repository
    # filepath: str = str(Path(__file__).parent.parent.parent / "data" / "WP96_4Pos_B4-10_DAPI.czi")

    # Option 2: Use absolute path to external test data
    # filepath: str = r"F:\Github\omezarr_playground\data\CellDivision5D.czi"
    filepath: str = r"F:\Github\omezarr_playground\data\WP96_4Pos_B4-10_DAPI.czi"
    # filepath: str = r"F:\Testdata_Zeiss\OME_ZARR_Testfiles\384well_DAPI_sm.czi"

    # ========== Validate Input File ==========
    if not Path(filepath).exists():
        raise FileNotFoundError(f"CZI file not found: {filepath}")

    # ========== Setup Logging (Master Log File) ==========
    czi_path = Path(filepath)
    log_file_path = czi_path.parent / f"{czi_path.stem}_conversion.log"

    # Configure logging explicitly - this will be the ONLY log file
    setup_logging(str(log_file_path), force_reconfigure=True)
    logger = logging.getLogger(__name__)

    # ========== HCS Format Conversion ==========
    if write_hcs:
        logger.info(f"Converting CZI to HCS-ZARR format using {ome_package.name}...")

        if ome_package == omezarr_package.OME_ZARR:
            logger.info("Using ome-zarr package for HCS conversion...")
            zarr_output_path = convert_czi2hcs_omezarr(czi_path, overwrite=True)

        elif ome_package == omezarr_package.NGFF_ZARR:
            logger.info("Using ngff-zarr package for HCS conversion...")
            zarr_output_path = convert_czi2hcs_ngff(
                czi_path,
                plate_name=platename,
                overwrite=True,
                write_ozx_directly=write_ozx_directly,
                output_dir=None,
                version="0.5",
            )
        else:
            raise ValueError(f"Unsupported ome_package: {ome_package}")

        logger.info(f"Converted to OME-ZARR HCS format at: {zarr_output_path}")

        # Optional: Convert the HCS-ZARR directory to single-file OZX format
        if convert_hc2ozx_after_writing:
            ozx_path = convert_hcs_omezarr2ozx(zarr_output_path, remove_omezarr=True)
            if ozx_path is not None:
                zarr_output_path = ozx_path
            else:
                logger.warning("convert_hcs_omezarr2ozx returned None; keeping original OME-ZARR path")

        # Validate the HCS-ZARR file against OME-NGFF v0.5 specification
        # nz.from_hcs_zarr validates against the NGFF v0.5 schema; only applicable
        # to NGFF_ZARR output (ome-zarr-py writes v0.4 and will not pass v0.5 validation).
        if ome_package == omezarr_package.NGFF_ZARR:
            logger.info("Validating created HCS-ZARR file against OME-NGFF v0.5 schema...")
            hcs_plate = nz.from_hcs_zarr(zarr_output_path, validate=True)
            logger.info("Validation successful - HCS metadata conforms to OME-NGFF v0.5 specification.")

    # ========== Standard OME-ZARR Conversion (Non-HCS) ==========
    elif not write_hcs:
        logger.info(f"Converting CZI scene {scene_id} to standard OME-ZARR format...")

        # Read the CZI file as a 6D array with dimension order STCZYX(A)
        # S=Scene, T=Time, C=Channel, Z=Z-stack, Y=Height, X=Width
        array, mdata = read_tools.read_6darray(filepath, planes={"S": (scene_id, scene_id)}, use_xarray=True)

        # Extract the specified scene (remove Scene dimension to get 5D array)
        # write_omezarr requires 5D array (TCZYX), not 6D (STCZYX)
        array = array.squeeze("S")  # Remove the Scene dimension
        logger.info(f"Array Type: {type(array)}, Shape: {array.shape}, Dtype: {array.dtype}")

        if ome_package == omezarr_package.OME_ZARR:
            # Generate output path with .ome.zarr extension
            zarr_output_path = Path(str(filepath)[:-4] + ".ome.zarr")

            # Write OME-ZARR using ome-zarr-py backend
            written_path = write_omezarr(array, zarr_path=zarr_output_path, metadata=mdata, overwrite=True)
            logger.info(f"Written OME-ZARR using ome-zarr-py: {written_path}")

        elif ome_package == omezarr_package.NGFF_ZARR:

            if write_ozx_directly:
                # Generate output path with _ngff.ozx extension
                zarr_output_path: Path = Path(str(filepath)[:-4] + "_ngff.ozx")
            else:
                # Generate output path with _ngff.ome.zarr extension
                zarr_output_path: Path = Path(str(filepath)[:-4] + "_ngff.ome.zarr")

            # Write OME-ZARR using ngff-zarr backend with multi-resolution pyramid
            # scale_factors=[2, 4] creates 3 resolution levels (1x, 2x, 4x downsampled)
            # version="0.5" explicitly selects OME-NGFF spec v0.5; zarr v3 store format
            # is used automatically because zarr >= 3 is installed.
            _ = write_omezarr_ngff(array, zarr_output_path, mdata, scale_factors=[2, 4], overwrite=True, version="0.5")
            logger.info(f"Written OME-ZARR using ngff-zarr: {zarr_output_path}")
        else:
            raise ValueError(f"Unsupported ome_package: {ome_package}")

    # ========== Optional: Visualize in napari ==========
    # Open the converted ZARR file in napari viewer for interactive visualization
    if show_napari:
        try:
            import napari

            logger.info("Opening ZARR file in napari viewer...")
            viewer = napari.Viewer()
            viewer.open(zarr_output_path, plugin="napari-ome-zarr")
            napari.run()
        except ImportError:
            logger.warning("Napari is not installed. Skipping visualization.")
            logger.info("Install with: pip install napari[all] napari-ome-zarr")


if __name__ == "__main__":
    main()

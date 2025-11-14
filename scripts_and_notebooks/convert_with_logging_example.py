#!/usr/bin/env python3
"""
Example script showing how to ensure logging when calling conversion functions directly.

This approach guarantees that logs are created whether you use the command-line tool
or call the functions from another script.
"""

import logging
from pathlib import Path
from ome_zarr_utils import setup_logging, convert_czi2hcs_ngff, convert_czi2hcs_omezarr


def convert_with_guaranteed_logging(czi_file_path: str, use_ngff: bool = True, plate_name: str = "My Plate"):
    """
    Convert a CZI file with guaranteed logging output.

    Args:
        czi_file_path: Path to the CZI file
        use_ngff: If True, use NGFF-ZARR format; if False, use OME-ZARR format
        plate_name: Name for the plate metadata

    Returns:
        str: Path to the output ZARR file
    """

    # Set up the log file path
    czi_path = Path(czi_file_path)
    log_file_path = czi_path.parent / f"{czi_path.stem}_conversion.log"

    # Configure logging explicitly
    setup_logging(str(log_file_path))
    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("Starting CZI conversion with guaranteed logging")
    logger.info(f"Input file: {czi_file_path}")
    logger.info(f"Using NGFF format: {use_ngff}")
    logger.info(f"Plate name: {plate_name}")
    logger.info("=" * 80)

    try:
        if use_ngff:
            result_path = convert_czi2hcs_ngff(
                czi_filepath=czi_file_path, plate_name=plate_name, overwrite=True, log_file_path=str(log_file_path)
            )
        else:
            result_path = convert_czi2hcs_omezarr(
                czi_filepath=czi_file_path, overwrite=True, log_file_path=str(log_file_path)
            )

        logger.info("=" * 80)
        logger.info("Conversion completed successfully!")
        logger.info(f"Output file: {result_path}")
        logger.info(f"Log file: {log_file_path}")
        logger.info("=" * 80)

        return result_path

    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"Conversion failed: {e}")
        logger.error("=" * 80)
        raise


if __name__ == "__main__":
    # Example usage
    czi_file = "../data/WP96_4Pos_B4-10_DAPI.czi"

    try:
        output_path = convert_with_guaranteed_logging(
            czi_file_path=czi_file, use_ngff=True, plate_name="Example Conversion"
        )
        print(f"✅ Success! Output: {output_path}")

    except Exception as e:
        print(f"❌ Failed: {e}")

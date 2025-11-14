#!/usr/bin/env python3
"""
Simple wrapper that ensures logging without creating duplicate log files.
"""

from pathlib import Path
from ome_zarr_utils import convert_czi2hcs_ngff, convert_czi2hcs_omezarr


def convert_czi_simple(czi_file_path: str, use_ngff: bool = True, plate_name: str = "My Plate"):
    """
    Convert a CZI file with guaranteed logging (creates only ONE log file).

    Args:
        czi_file_path: Path to the CZI file
        use_ngff: If True, use NGFF-ZARR format; if False, use OME-ZARR format
        plate_name: Name for the plate metadata

    Returns:
        str: Path to the output ZARR file
    """

    print(f"🔄 Starting CZI conversion...")
    print(f"📁 Input file: {czi_file_path}")
    print(f"🔧 Format: {'NGFF-ZARR' if use_ngff else 'OME-ZARR'}")
    print(f"🏷️  Plate name: {plate_name}")

    try:
        if use_ngff:
            # Let the function create its own log file (no duplicates)
            result_path = convert_czi2hcs_ngff(czi_filepath=czi_file_path, plate_name=plate_name, overwrite=True)
            log_suffix = "_hcs_ngff.log"
        else:
            # Let the function create its own log file (no duplicates)
            result_path = convert_czi2hcs_omezarr(czi_filepath=czi_file_path, overwrite=True)
            log_suffix = "_hcs_omezarr.log"

        # Find the log file that was created
        czi_path = Path(czi_file_path)
        log_file = czi_path.parent / f"{czi_path.stem}{log_suffix}"

        print(f"✅ Conversion completed successfully!")
        print(f"📁 Output file: {result_path}")

        if log_file.exists():
            print(f"📝 Log file: {log_file}")

        return result_path

    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        raise


if __name__ == "__main__":
    # Example usage
    czi_file = "../data/WP96_4Pos_B4-10_DAPI.czi"

    try:
        output_path = convert_czi_simple(czi_file_path=czi_file, use_ngff=True, plate_name="Example Conversion")
        print(f"✅ Success! Output: {output_path}")

    except Exception as e:
        print(f"❌ Failed: {e}")

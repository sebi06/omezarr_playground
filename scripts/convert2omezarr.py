"""
CZI to OME-ZARR HCS Converter

This script converts CZI (Carl Zeiss Image) files containing High Content Screening (HCS)
plate data into the OME-ZARR format. The output follows the OME-NGFF specification for
HCS data, organizing images in a plate/well/field hierarchy.

Usage:
    python convert2hcs_omezarr.py --czifile path/to/file.czi [OPTIONS]

Example:
    python convert2hcs_omezarr.py --czifile WP96_plate.czi --plate_name "Experiment_001" --overwrite
"""

import argparse
import ast
import sys
import logging
from pathlib import Path
from ome_zarr_utils import write_omezarr, write_omezarr_ngff
import ngff_zarr as nz
from czitools.read_tools import read_tools


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Convert CZI files to OME-ZARR format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic conversion with default NGFF-ZARR format and default scales
    python convert2omezarr.py --czifile WP96_plate.czi

    # Use specific multiscale factors
    python convert2omezarr.py --czifile WP96_plate.czi --scales [2,4,8]

    # Use OME-ZARR format explicitly with custom scales
    python convert2omezarr.py --czifile WP96_plate.czi --use_omezarr --scales [1,2,4,8]

    # Use NGFF-ZARR format explicitly  
    python convert2omezarr.py --czifile WP96_plate.czi --use_ngffzarr --scales [2,4]

    # Specify custom output path and scales
    python convert2omezarr.py --czifile WP96_plate.czi --zarr /path/to/output.ome.zarr --scales [1,2,4]

    # Enable overwrite mode to replace existing files
    python convert2omezarr.py --czifile WP96_plate.czi --overwrite --scales [2,4,8,16]

Notes:
    - If no format is specified, NGFF-ZARR format is used by default (recommended)
    - Scales must be specified as a list in brackets: [2,4,8] or [1,2,4]
    - The output format follows the OME-NGFF specification
    - Data is organized in a plate/well/field hierarchy
    - All conversion logs are saved to '<input_filename>_hcs_omezarr.log'
        """,
    )

    # Required arguments
    parser.add_argument(
        "--czifile",
        type=str,
        required=True,
        help="Path to the input CZI file to convert (required)",
    )

    # Create mutually exclusive group for format selection
    format_group = parser.add_mutually_exclusive_group()
    format_group.add_argument(
        "--use_ngffzarr",
        action="store_true",
        help="Use NGFF-ZARR package",
    )
    format_group.add_argument(
        "--use_omezarr",
        action="store_true",
        help="Use OME-ZARR package",
    )
    # Optional arguments
    parser.add_argument(
        "--zarr",
        type=str,
        default=None,
        help="Output path for the OME-ZARR file (default: <czifile>_ngff_plate.ome.zarr)",
    )
    parser.add_argument(
        "--scales",
        type=str,
        default="[1,2,4]",
        help="Multiscale downsampling factors as JSON-style list (default: [1,2,4]). Example: --scales [2,4,8]",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing OME-ZARR files if they exist (default: False)",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate the output OME-ZARR files (default: False)",
    )

    parser.add_argument(
        "--scene",
        type=int,
        default=0,
        help="Scene index to process (default: 0)",
    )

    args = parser.parse_args()

    # Parse scales argument
    try:
        scales = ast.literal_eval(args.scales)
        if not isinstance(scales, list) or not all(isinstance(x, int) for x in scales):
            raise ValueError("scales must be a list of integers")
    except (ValueError, SyntaxError) as e:
        print(f"Error parsing scales argument: {e}")
        print("Expected format: [2,4,8] etc. or [1,2,4]")
        sys.exit(1)

    # Validate input CZI file exists
    czi_filepath = Path(args.czifile)
    if not czi_filepath.exists():
        print(f"Input CZI file not found: {czi_filepath}")
        raise FileNotFoundError(f"CZI file does not exist: {czi_filepath}")

    # Derive log file path from CZI file location and name
    log_file_path = czi_filepath.parent / f"{czi_filepath.stem}_omezarr.log"

    # Configure logging with both console and file output
    # Note: We need to configure the root logger and add handlers manually
    # because ome_zarr_utils.py has already called basicConfig()
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Clear any existing handlers to avoid conflicts
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set up formatters
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler
    file_handler = logging.FileHandler(str(log_file_path))
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info("CZI to OME-ZARR Conversion Started")
    logger.info("=" * 80)

    if not czi_filepath.suffix.lower() == ".czi":
        logger.warning(f"Input file does not have .czi extension: {czi_filepath}")

    logger.info(f"Input CZI file: {czi_filepath.absolute()}")
    logger.info(f"Multiscale factors: {scales}")

    # Determine output path
    if args.zarr is None:
        # Generate default output path based on input filename
        zarr_output_path = str(czi_filepath.with_suffix("")) + ".ome.zarr"
        logger.info(f"No output path specified, using default: {zarr_output_path}")
    else:
        zarr_output_path = args.zarr
        logger.info(f"Using specified output path: {zarr_output_path}")

    # Log plate name and overwrite settings
    logger.info(f"Overwrite mode: {args.overwrite}")

    if args.overwrite:
        logger.warning("Overwrite enabled: Existing OME-ZARR files will be removed!")

    # Perform the conversion
    try:
        logger.info("Starting conversion process...")

        # Read the CZI file as a 6D array with dimension order STCZYX(A)
        # S=Scene, T=Time, C=Channel, Z=Z-stack, Y=Height, X=Width, A=Angle (optional)
        array, mdata = read_tools.read_6darray(
            czi_filepath, planes={"S": (args.scene, args.scene)}, use_xarray=True, adapt_metadata=True
        )

        # Extract the specified scene (remove Scene dimension to get 5D array)
        # write_omezarr requires 5D array (TCZYX), not 6D (STCZYX)
        array = array.squeeze("S")  # Remove the Scene dimension
        logger.info(f"Array Type: {type(array)}, Shape: {array.shape}, Dtype: {array.dtype}")

        # Determine which format to use based on arguments
        if args.use_omezarr:
            logger.info("Using OME-ZARR package.")
            result_path = write_omezarr(
                array5d=array,
                zarr_path=str(zarr_output_path),
                metadata=mdata,
                overwrite=args.overwrite,
            )
        elif args.use_ngffzarr:
            logger.info("Using NGFF-ZARR package.")
            result_path = write_omezarr_ngff(
                array5d=array,
                zarr_path=str(zarr_output_path),
                scale_factors=[2, 4],  # Example scale factors for multi-resolution
                metadata=mdata,
                overwrite=args.overwrite,
            )
        else:
            # Default behavior - use NGFF-ZARR as recommended
            logger.info("Using NGFF-ZARR package.")
            result_path = write_omezarr_ngff(
                array5d=array,
                zarr_path=str(zarr_output_path),
                scale_factors=[2, 4, 8],  # Example scale factors for multi-resolution
                metadata=mdata,
                overwrite=args.overwrite,
            )

        # Log successful completion
        logger.info("=" * 80)
        logger.info("Conversion completed successfully!")
        logger.info(f"Output OME-ZARR file: {result_path}")
        logger.info("=" * 80)

        # Optional validation step
        if args.validate:
            logger.info("Validating created OME-ZARR file against schema...")
            hcs_plate = nz.from_hcs_zarr(zarr_output_path, validate=args.validate)
            logger.info("Validation successful.")

    except Exception as e:
        # Log any errors that occur during conversion
        logger.error("=" * 80)
        logger.error(f"Conversion failed with error: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("=" * 80)
        raise

# -*- coding: utf-8 -*-
"""
czi_omezarr_utils
=================
Utility package for converting Carl Zeiss Image (CZI) files to OME-ZARR format.

Public API — import everything from here so callers need only one import line:

    from czi_omezarr_utils import (
        omezarr_package,
        setup_logging,
        write_omezarr,
        write_omezarr_ngff,
        convert_czi2hcs_omezarr,
        convert_czi2hcs_ngff,
        convert_hcs_omezarr2ozx,
        extract_well_coordinates,
        PlateConfiguration,
        PlateType,
        define_plate,
        define_plate_by_well_count,
        get_fieldimage,
        get_display,
        create_channel_list,
        ArrayProcessor,
        create_well_plate_heatmap,
        process_hcs_omezarr,
        validate_ome_zarr,
    )
"""

from .logging_utils import setup_logging, omezarr_package
from .conversion import (
    write_omezarr,
    write_omezarr_ngff,
    convert_czi2hcs_omezarr,
    convert_czi2hcs_ngff,
)
from .hcs import (
    extract_well_coordinates,
    PlateConfiguration,
    PlateType,
    define_plate,
    define_plate_by_well_count,
    convert_hcs_omezarr2ozx,
)
from .display import get_fieldimage, get_display, create_channel_list
from .processing import ArrayProcessor, process_hcs_omezarr
from .plotting import create_well_plate_heatmap
from .validation import validate_ome_zarr

__all__ = [
    "omezarr_package",
    "setup_logging",
    "write_omezarr",
    "write_omezarr_ngff",
    "convert_czi2hcs_omezarr",
    "convert_czi2hcs_ngff",
    "convert_hcs_omezarr2ozx",
    "extract_well_coordinates",
    "PlateConfiguration",
    "PlateType",
    "define_plate",
    "define_plate_by_well_count",
    "get_fieldimage",
    "get_display",
    "create_channel_list",
    "ArrayProcessor",
    "process_hcs_omezarr",
    "create_well_plate_heatmap",
    "validate_ome_zarr",
]

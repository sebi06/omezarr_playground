# -*- coding: utf-8 -*-
"""
czi_omezarr_utils.conversion
==============================
Core CZI → OME-ZARR conversion functions.

  - convert_czi2hcs_omezarr   — HCS pipeline using ome-zarr-py
  - convert_czi2hcs_ngff      — HCS pipeline using ngff-zarr
  - write_omezarr             — write 5D xarray using ome-zarr-py
  - write_omezarr_ngff        — write 5D xarray using ngff-zarr with pyramid
"""

import gc
import logging
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Union

import numpy as np
import xarray as xr
import dask.array as da
import zarr
import ngff_zarr as nz
from ngff_zarr.v04.zarr_metadata import Plate, PlateColumn, PlateRow, PlateWell
from ngff_zarr.hcs import HCSPlate, HCSPlateWriter, to_hcs_zarr
from ome_zarr.io import parse_url
from ome_zarr.writer import write_image, write_plate_metadata, write_well_metadata
import ome_zarr.writer
import ome_zarr.format
from czitools.read_tools import read_tools
from czitools.metadata_tools.czi_metadata import CziMetadata

from .logging_utils import setup_logging
from .hcs import extract_well_coordinates
from .display import get_fieldimage, create_channel_list

logger = logging.getLogger(__name__)


def _to_ome_zarr_image(array: Union[np.ndarray, xr.DataArray, da.Array]) -> Union[np.ndarray, da.Array]:
    """Return an array type accepted by ome-zarr writer functions."""
    if isinstance(array, xr.DataArray):
        data = array.data
        if isinstance(data, (np.ndarray, da.Array)):
            return data
        return np.asarray(data)
    return array


def _ensure_plate_version_metadata(zarr_path: Union[str, os.PathLike, Path], version: str) -> None:
    """Ensure nested ome.plate.version exists in root metadata."""
    parsed = parse_url(Path(zarr_path), mode="r+")
    assert parsed is not None, f"Failed to open zarr store at {zarr_path}"

    root = zarr.group(store=parsed.store)
    attrs = root.attrs.asdict()
    ome_attrs = attrs.get("ome")
    if not isinstance(ome_attrs, dict):
        return

    plate_attrs = ome_attrs.get("plate")
    if not isinstance(plate_attrs, dict) or plate_attrs.get("version") is not None:
        return

    plate_attrs["version"] = version
    ome_attrs["plate"] = plate_attrs
    attrs["ome"] = ome_attrs
    root.attrs.update(attrs)


# ---------------------------------------------------------------------------
# ome-zarr-py HCS conversion
# ---------------------------------------------------------------------------


def convert_czi2hcs_omezarr(
    czi_filepath: Union[str, os.PathLike, Path],
    overwrite: bool = True,
    log_file_path: Optional[Union[str, os.PathLike, Path]] = None,
    pad_columns: bool = True,
) -> Path:
    """Convert a CZI file to OME-ZARR HCS format using the ome-zarr-py backend.

    Args:
        czi_filepath: Path to the input CZI file.
        overwrite: Remove existing output directory if True.
        log_file_path: Path to log file. Defaults to ``<stem>_hcs_omezarr.log``.
        pad_columns: Zero-pad column numbers in well paths (e.g. ``"04"`` instead of
            ``"4"``). Default is ``True``.

    Returns:
        Path to the output OME-ZARR HCS directory (``<stem>_HCSplate.ome.zarr``).

    Note:
        Output is organized in a plate/row/column/field hierarchy following
        the OME-NGFF HCS specification.
    """
    czi_path = Path(czi_filepath)
    if log_file_path is None:
        log_file_path = czi_path.parent / f"{czi_path.stem}_hcs_omezarr.log"
    else:
        log_file_path = Path(log_file_path)

    setup_logging(log_file_path)

    logger.info("=" * 80)
    logger.info("CZI to HCS OME-ZARR Conversion Started (OME-ZARR format)")
    logger.info("=" * 80)
    logger.info(f"Input CZI file: {czi_path.absolute()}")

    zarr_output_path = czi_path.parent / f"{czi_path.stem}_HCSplate.ome.zarr"

    if zarr_output_path.exists():
        if overwrite:
            logger.info(f"Removing existing directory: {zarr_output_path}")
            shutil.rmtree(zarr_output_path)
        else:
            logger.info(f"File exists at {zarr_output_path}. Set overwrite=True to remove.")
            return zarr_output_path

    array6d, mdata = read_tools.read_6darray(str(czi_path), use_xarray=True)

    assert mdata.sample is not None, "CZI metadata is missing sample/plate information"
    assert isinstance(array6d, xr.DataArray), "Expected xarray DataArray from read_6darray with use_xarray=True"

    row_names, col_names, well_paths = extract_well_coordinates(mdata.sample.well_counter, pad_columns=pad_columns)
    field_paths = [str(i) for i in range(mdata.sample.well_counter[mdata.sample.well_array_names[0]])]

    parsed = parse_url(zarr_output_path, mode="w")
    assert parsed is not None, f"Failed to open zarr store at {zarr_output_path}"
    store = parsed.store
    root = zarr.group(store=store)

    columns_metadata = [PlateColumn(name=str(col)) for col in sorted(col_names, key=int)]
    rows_metadata = [PlateRow(name=row) for row in sorted(row_names)]

    write_plate_metadata(root, row_names, col_names, well_paths)  # type: ignore[arg-type]

    plate_attrs = root.attrs.asdict()
    plate_attrs["rows"] = [{"name": r.name} for r in rows_metadata]
    plate_attrs["columns"] = [{"name": c.name} for c in columns_metadata]
    root.attrs.update(plate_attrs)

    for wp in well_paths:
        row, col = wp.split("/")
        well_group = root.require_group(row).require_group(col)
        write_well_metadata(well_group, field_paths)  # type: ignore[arg-type]

        # Strip leading zeros to match the CZI well_scene_indices key (e.g. "B4", not "B04")
        current_well_id = f"{row}{int(col)}"
        for fi, field in enumerate(field_paths):
            image_group = well_group.require_group(str(field))
            current_scene_index = mdata.sample.well_scene_indices[current_well_id][fi]
            logger.info(f"Writing Well: {wp}, Field: {field}, Scene Index: {current_scene_index}")

            image = array6d[current_scene_index, ...]

            write_image(
                image=_to_ome_zarr_image(image),
                group=image_group,
                axes="".join(str(d).lower() for d in image.dims),
                storage_options=dict(chunks=(1, 1, 1, array6d.sizes["Y"], array6d.sizes["X"])),
            )

    logger.info("=" * 80)
    logger.info("Conversion completed successfully!")
    logger.info(f"Output HCS OME-ZARR file: {zarr_output_path}")
    logger.info("=" * 80)

    return zarr_output_path


# ---------------------------------------------------------------------------
# ngff-zarr HCS conversion
# ---------------------------------------------------------------------------


def convert_czi2hcs_ngff(
    czi_filepath: Union[str, os.PathLike, Path],
    plate_name: str = "Automated Plate",
    overwrite: bool = True,
    log_file_path: Optional[Union[str, os.PathLike, Path]] = None,
    write_ozx_directly: bool = False,
    version: str = "0.5",
    output_dir: Optional[Union[str, os.PathLike, Path]] = None,
    pad_columns: bool = True,
) -> Path:
    """Convert a CZI file to OME-ZARR HCS format using the ngff-zarr backend.

    Args:
        czi_filepath: Path to the input CZI file.
        plate_name: Name for the well plate in metadata.
        overwrite: Remove existing output if True.
        log_file_path: Path to log file. Defaults to ``<stem>_hcs_ngff.log``.
        write_ozx_directly: If True, write a single-file ``.ozx`` archive directly
            (not supported for HCS in the GUI — use convert_hcs_omezarr2ozx instead).
        version: NGFF version string (default: "0.5").
        output_dir: Optional directory for the output file. Defaults to the CZI file's
            parent directory.
        pad_columns: Zero-pad column numbers in well paths (e.g. ``"04"`` instead of
            ``"4"``). Default is ``True``.

    Returns:
        Path to the output OME-ZARR HCS directory (``<stem>_ngff_plate.ome.zarr``) or
        OZX file (``<stem>_ngff_plate.ozx``) when *write_ozx_directly* is True.

    Note:
        The ngff-zarr backend uses the ``_ngff_plate`` suffix to avoid colliding with the
        ome-zarr-py output (``_HCSplate.ome.zarr``), allowing both backends to coexist.
    """
    czi_path = Path(czi_filepath)
    output_path_obj: Optional[Path] = Path(output_dir) if output_dir is not None else None

    if log_file_path is None:
        if output_path_obj is not None:
            log_file_path = output_path_obj / f"{czi_path.stem}_hcs_ngff.log"
        else:
            log_file_path = czi_path.parent / f"{czi_path.stem}_hcs_ngff.log"
    else:
        log_file_path = Path(log_file_path)

    setup_logging(log_file_path)

    logger.info("=" * 80)
    logger.info("CZI to HCS OME-ZARR Conversion Started (NGFF-ZARR format)")
    logger.info("=" * 80)
    logger.info(f"Input CZI file: {czi_path.absolute()}")
    logger.info(f"Plate name: {plate_name}")

    stem = czi_path.stem
    suffix = "_ngff_plate.ozx" if write_ozx_directly else "_ngff_plate.ome.zarr"
    base_dir = output_path_obj if output_path_obj is not None else czi_path.parent
    zarr_output_path = base_dir / f"{stem}{suffix}"

    if zarr_output_path.exists():
        if overwrite:
            logger.info(f"Removing existing file/directory: {zarr_output_path}")
            if zarr_output_path.is_dir():
                shutil.rmtree(zarr_output_path)
            else:
                os.remove(zarr_output_path)
            gc.collect()
            time.sleep(0.5)
            logger.info("File removed successfully")
        else:
            logger.info(f"File exists at {zarr_output_path}. Set overwrite=True to remove.")
            return zarr_output_path

    array6d, mdata = read_tools.read_6darray(str(czi_path), use_xarray=True)

    assert mdata.sample is not None, "CZI metadata is missing sample/plate information"
    assert isinstance(array6d, xr.DataArray), "Expected xarray DataArray from read_6darray with use_xarray=True"

    row_names, col_names, well_paths = extract_well_coordinates(mdata.sample.well_counter, pad_columns=pad_columns)
    field_paths = [str(i) for i in range(mdata.sample.well_counter[mdata.sample.well_array_names[0]])]

    columns = [PlateColumn(name=str(col)) for col in sorted(col_names, key=int)]
    rows = [PlateRow(name=row) for row in sorted(row_names)]

    wells = []
    for row in rows:
        row_index = 0
        for i, char in enumerate(reversed(row.name.upper())):
            row_index += (ord(char) - ord("A") + 1) * (26**i)
        row_index -= 1

        for col in columns:
            col_index = int(col.name) - 1
            wells.append(
                PlateWell(
                    path=f"{row.name}/{col.name}",
                    rowIndex=row_index,
                    columnIndex=col_index,
                )
            )

    plate_metadata = Plate(
        columns=columns,
        rows=rows,
        wells=wells,
        name=plate_name,
        field_count=len(field_paths),
        version=version,
    )

    # On Windows, HCSPlateWriter.__exit__ calls write_store_to_zip while the internal
    # temp store is still open, which causes a PermissionError (ngff-zarr issue #241).
    # Workaround: always write to a .ome.zarr directory on Windows, then zip afterwards.
    _win_ozx_workaround = write_ozx_directly and sys.platform == "win32"
    if _win_ozx_workaround:
        logger.warning(
            "write_ozx_directly=True is not supported on Windows (ngff-zarr issue #241). "
            "Writing to .ome.zarr first, then converting to .ozx."
        )
        write_path = base_dir / f"{stem}_ngff_plate.ome.zarr"
        # Remove any pre-existing intermediate directory
        if write_path.exists():
            shutil.rmtree(write_path)
            gc.collect()
            time.sleep(0.2)
    else:
        write_path = zarr_output_path

    hcs_plate = HCSPlate(store=write_path, plate_metadata=plate_metadata)
    to_hcs_zarr(hcs_plate, write_path)

    with HCSPlateWriter(str(write_path), plate_metadata) as writer:
        for well in wells:
            row_name, col_name = well.path.split("/")
            # Strip leading zeros to match the CZI well_scene_indices key (e.g. "B4", not "B04")
            current_well_id = f"{row_name}{int(col_name)}"
            logger.info(f"Creating WellID: {current_well_id} Row: {row_name}, Column: {col_name}")
            for fi, field in enumerate(field_paths):
                current_scene_index = mdata.sample.well_scene_indices[current_well_id][fi]
                logger.info(f"Writing Well: {well.path}, Field: {field}, Scene Index: {current_scene_index}")
                multiscales = get_fieldimage(array6d, current_scene_index, mdata)
                writer.write_well_image(
                    multiscales=multiscales,
                    row_name=row_name,
                    column_name=col_name,
                    field_index=fi,
                )

    _ensure_plate_version_metadata(write_path, version)

    if _win_ozx_workaround:
        # All file handles are now closed; safe to zip on Windows
        from .hcs import convert_hcs_omezarr2ozx

        logger.info("Converting intermediate .ome.zarr to .ozx (Windows workaround)...")
        gc.collect()
        time.sleep(0.5)  # give Windows a moment to release remaining handles
        zarr_output_path = convert_hcs_omezarr2ozx(write_path, remove_omezarr=True)

    logger.info("=" * 80)
    logger.info("Conversion completed successfully!")
    logger.info(f"Output HCS OME-ZARR file: {zarr_output_path}")
    logger.info("=" * 80)

    return zarr_output_path


# ---------------------------------------------------------------------------
# write_omezarr (ome-zarr-py single image)
# ---------------------------------------------------------------------------


def write_omezarr(
    array5d: Union[np.ndarray, xr.DataArray, da.Array],
    zarr_path: Union[str, Path],
    metadata: CziMetadata,
    overwrite: bool = False,
    log_file_path: Optional[Union[str, Path]] = None,
) -> Optional[Path]:
    """Write a 5D array to OME-ZARR format using the ome-zarr-py backend.

    Args:
        array5d: Input xarray DataArray with named dimensions (T, C, Z, Y, X).
        zarr_path: Output path for the OME-ZARR file.
        metadata: CziMetadata with channel and scale information.
        overwrite: Remove existing output if True.
        log_file_path: Path to log file. Defaults to ``<stem>_omezarr.log``.

    Returns:
        Path to the written OME-ZARR file, or None on failure.
    """
    if log_file_path is None:
        zarr_path_obj = Path(zarr_path)
        log_file_path = zarr_path_obj.parent / f"{zarr_path_obj.stem}_omezarr.log"

    setup_logging(log_file_path)

    logger.info("=" * 80)
    logger.info("Writing OME-ZARR format (ome-zarr-py)")
    logger.info("=" * 80)
    logger.info(f"Input array shape: {array5d.shape}")
    logger.info(f"Output path: {zarr_path}")

    assert isinstance(array5d, xr.DataArray), "write_omezarr requires an xarray DataArray"

    zarr_path = Path(zarr_path)

    if len(array5d.shape) > 5:
        logger.info("Input array has more than 5 dimensions.")
        return None

    if zarr_path.exists() and overwrite:
        logger.info(f"Removing existing file/directory: {zarr_path}")
        if zarr_path.is_dir():
            shutil.rmtree(zarr_path, ignore_errors=False, onexc=None)
        else:
            os.remove(zarr_path)
    elif zarr_path.exists() and not overwrite:
        logger.info(f"File already exists at {zarr_path}. Set overwrite=True to remove.")
        return None

    ngff_version = ome_zarr.format.CurrentFormat().version
    logger.info(f"Using ngff format version: {ngff_version}")

    parsed = parse_url(zarr_path, mode="w")
    assert parsed is not None, f"Failed to open zarr store at {zarr_path}"
    store = parsed.store
    root = zarr.group(store=store, overwrite=overwrite)

    ome_zarr.writer.write_image(
        image=_to_ome_zarr_image(array5d),
        group=root,
        axes="".join(str(d).lower() for d in array5d.dims),
        storage_options=dict(chunks=(1, 1, 1, array5d.sizes["Y"], array5d.sizes["X"])),
    )

    channels_list = create_channel_list(metadata)
    ome_zarr.writer.add_metadata(
        root,
        {
            "omero": {
                "name": metadata.filename,
                "channels": channels_list,
            }
        },
    )

    logger.info("=" * 80)
    logger.info("OME-ZARR writing completed successfully!")
    logger.info(f"Output file: {zarr_path}")
    logger.info("=" * 80)

    return zarr_path


# ---------------------------------------------------------------------------
# write_omezarr_ngff (ngff-zarr single image with pyramid)
# ---------------------------------------------------------------------------


def write_omezarr_ngff(
    array5d: Union[np.ndarray, xr.DataArray, da.Array],
    zarr_path: Union[Path, str],
    metadata: CziMetadata,
    scale_factors: list[int] = [2, 4, 8],
    overwrite: bool = False,
    version: str = "0.5",
    chunks: Union[tuple, None] = None,
    chunks_per_shard: Union[Dict[str, int], int, None] = 2,
    log_file_path: Union[Path, str, None] = None,
) -> Optional[nz.NgffImage]:
    """Write a 5D array to OME-ZARR NGFF format with multi-scale pyramids.

    Args:
        array5d: Input 5D array (numpy, xarray, or dask) with dimensions (t, c, z, y, x).
        zarr_path: Output path for the OME-ZARR NGFF file.
        metadata: CziMetadata with scale and channel information.
        scale_factors: Downscaling factors for the multi-scale pyramid (default: [2, 4, 8]).
        overwrite: Remove existing output if True.
        version: NGFF version string (default: "0.5").
        chunks: Explicit chunk shape (default: None — auto-computed).
        chunks_per_shard: Chunks per shard for sharding storage (default: 2).
        log_file_path: Path to log file. Defaults to ``<stem>_ngff.log``.

    Returns:
        The NgffImage object written, or None on failure.
    """
    if log_file_path is None:
        zarr_path_obj = Path(zarr_path)
        log_file_path = zarr_path_obj.parent / f"{zarr_path_obj.stem}_ngff.log"

    setup_logging(log_file_path)

    logger.info("=" * 80)
    logger.info("Writing OME-ZARR NGFF format with multiscale")
    logger.info("=" * 80)
    logger.info(f"Input array shape: {array5d.shape}")
    logger.info(f"Output path: {zarr_path}")
    logger.info(f"Scale factors: {scale_factors}")

    if len(array5d.shape) > 5:
        logger.info("Input array has more than 5 dimensions.")
        return None

    if Path(zarr_path).exists() and overwrite:
        shutil.rmtree(zarr_path, ignore_errors=False, onexc=None)
    elif Path(zarr_path).exists() and not overwrite:
        logger.info(f"File already exists at {zarr_path}. Set overwrite=True to remove.")
        return None

    _scale = metadata.scale
    _filename = metadata.filename or "image.czi"

    image = nz.to_ngff_image(
        array5d.data if isinstance(array5d, xr.DataArray) else array5d,  # type: ignore[arg-type]
        dims=["t", "c", "z", "y", "x"],
        scale={
            "y": float(_scale.Y) if (_scale is not None and _scale.Y is not None) else 1.0,
            "x": float(_scale.X) if (_scale is not None and _scale.X is not None) else 1.0,
            "z": float(_scale.Z) if (_scale is not None and _scale.Z is not None) else 1.0,
        },
        name=_filename[:-4] + ".ome.zarr",
    )

    if chunks is None:
        chunks = (1, array5d.shape[1], array5d.shape[2], array5d.shape[3], array5d.shape[4])  # type: ignore[misc]

    multiscales = nz.to_multiscales(
        image,
        scale_factors=scale_factors,
        chunks=chunks,
        method=nz.Methods.DASK_IMAGE_GAUSSIAN,  # type: ignore[attr-defined]
    )

    channels_list = create_channel_list(metadata)
    channels = []
    for ch in channels_list:
        omero_channel = nz.OmeroChannel(
            color=ch["color"],
            window=nz.OmeroWindow(
                min=ch["window"]["min"],
                max=ch["window"]["max"],
                start=ch["window"]["start"],
                end=ch["window"]["end"],
            ),
            label=ch["label"],
        )
        channels.append(omero_channel)
    multiscales.metadata.omero = nz.Omero(channels=channels)

    nz.to_ngff_zarr(
        zarr_path,
        version=version,
        chunks_per_shard=chunks_per_shard,
        use_tensorstore=False,
        multiscales=multiscales,
    )

    logger.info("=" * 80)
    logger.info("NGFF OME-ZARR writing completed successfully!")
    logger.info(f"Output file: {zarr_path}")
    logger.info("=" * 80)

    return image

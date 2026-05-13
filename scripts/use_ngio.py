import ngio
from ngio.utils import download_ome_zarr_dataset, list_ome_zarr_datasets
from ngio import open_ome_zarr_plate
import os
from czi_omezarr_utils.validation import validate_ome_zarr
from pathlib import Path

# define path to local OME-ZARR file
omezarr_path = Path(r"data/WP96_4Pos_B4-10_DAPI_ngff_plate.ome.zarr")

# validate the OME-ZARR file
is_valid = validate_ome_zarr(omezarr_path)
if not is_valid:
    print(f"❌ Invalid OME-ZARR file: {omezarr_path}")

# define path to a field image group inside the plate (s0 is a raw array level, not an image)
image_path = omezarr_path / "B" / "04" / "0"

# validate image path
is_valid = validate_ome_zarr(image_path)
if not is_valid:
    print(f"❌ Invalid Image path inside OME-ZARR file: {image_path}")


plate = ngio.open_ome_zarr_plate(omezarr_path)
hcs_zarr = open_ome_zarr_plate(omezarr_path)
print(hcs_zarr)
print(f"Rows: {hcs_zarr.rows}, Columns: {hcs_zarr.columns}")

ome_zarr_container = ngio.open_ome_zarr_container(image_path)
image = ome_zarr_container.get_image()

print(f"Image shape: {image.shape}, dtype: {image.dtype}")

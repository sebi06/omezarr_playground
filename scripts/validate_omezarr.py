import zarr
from ome_zarr_models.v05.image import Image
from ome_zarr_models.v05.plate import Plate
from pydantic import ValidationError
from typing import Any, cast


def validate_ome_zarr(path: str) -> bool:
    """Validate a local OME-ZARR file."""
    try:
        group = zarr.open_group(path, mode="r")
        root_attrs = group.attrs.asdict()
        ome_attrs = root_attrs.get("ome", {})

        if isinstance(ome_attrs, dict) and "plate" in ome_attrs:
            plate = Plate.model_validate(ome_attrs["plate"])
            for well in plate.wells:
                well_group = group[well.path]
                if not isinstance(well_group, zarr.Group):
                    raise TypeError(f"Expected well group at {well.path}, got {type(well_group).__name__}")

                well_ome_attrs = well_group.attrs.asdict().get("ome", {})
                well_attrs: Any = well_ome_attrs.get("well", {}) if isinstance(well_ome_attrs, dict) else {}
                image_entries = well_attrs.get("images", []) if isinstance(well_attrs, dict) else []

                for image_info in image_entries:
                    if not isinstance(image_info, dict) or "path" not in image_info:
                        continue
                    image_group = well_group[cast(str, image_info["path"])]
                    if not isinstance(image_group, zarr.Group):
                        raise TypeError(
                            f"Expected image group at {well.path}/{image_info['path']}, got {type(image_group).__name__}"
                        )
                    Image.from_zarr(image_group)

            print(f"✅ Valid OME-ZARR HCS plate: {path}")
        else:
            Image.from_zarr(group)
            print(f"✅ Valid OME-ZARR image: {path}")
        return True
    except ValidationError as e:
        print(f"❌ Validation failed: {path}")
        print(e)
        return False
    except Exception as e:
        print(f"❌ Error opening file: {e}")
        return False


omezarr_path = r"F:\GitHub\omezarr_playground\data\WP96_4Pos_B4-10_DAPI_ngff_plate.ome.zarr"
# omezarr_path = r"F:\GitHub\omezarr_playground\data\WP96_4Pos_B4-10_DAPI_HCSplate.ome.zarr"

validate_ome_zarr(omezarr_path)

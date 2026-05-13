# CZI OME-ZARR Playground

This is a "playground" to try out and play with CZI image files and OME-ZARR related. It contains scripts and notebooks:

![CZI & OME-ZARR Playground](images/title_image.png)

- convert CZI --> OME-ZARR using
  - [OME-ZARR](https://pypi.org/project/ome-zarr/) python package
  - [NGFF-ZARR](https://pypi.org/project/ngff-zarr/) python package
  - convert to "normal" OME-ZARR files or to OME-ZARR using the HCS layout (wellplates)
  - resulting images will be opened inside the [Napari Viewer](https://napari.org/stable/) using the [napari-ome-zarr](https://napari-hub.org/plugins/napari-ome-zarr.html) plugin
  - example CZI image data for both cases are provided - see "./data" folder
- the conversions can be test by running:
  - scripts
  - CMD tools
  - notebooks
- "analyze" HCS OME-ZARR by using simple processing functions
- visualize the results as an heatmap

## Disclaimer

This content of this repository is free to use for everybody and purely experimental. The authors undertakes no warranty concerning the use of those scripts or notebooks. Use them on your own risk.

**By using any of those examples you agree to this disclaimer.**

## Prerequisites

### Install python base  environment (miniconda etc.)

- Download and install Miniconda if needed: [Download Miniconda](https://www.anaconda.com/download/success)
- Install Jupyter & Co

```cmd
conda activate base
conda install jupyterlab jupyter_server nb_conda_kernels
```

To run the notebooks locally it is recommended to create a fresh conda environment. Please feel free to use the provided [YML file](env_omezarr.yml) (at your own risk) to create such an environment:

```cmd
conda env create --file env_omezarr.yml
```

Alternatively, a [pixi.toml](pixi.toml) file is provided for use with the [pixi](https://prefix.dev/docs/pixi/overview) package manager:

```cmd
pixi install
pixi run python scripts/create_omezarr_example.py
```

## Utilities: czi_omezarr_utils

Installable utility package for converting CZI to OME-ZARR. Install in editable mode from the repo root:

```bash
conda activate omezarr
pip install -e .
```

Example Usage:

```python
from czi_omezarr_utils import (
    convert_czi2hcs_ngff,
    write_omezarr_ngff,
    omezarr_package,
    setup_logging,
    validate_ome_zarr,
)
from pathlib import Path
from czitools.read_tools import read_tools
import logging

# --- HCS plate conversion (ngff-zarr, OME-NGFF v0.5) ---
czi_path = Path("data/WP96_4Pos_B4-10_DAPI.czi")
setup_logging(czi_path.parent / "conversion.log", force_reconfigure=True)
zarr_path = convert_czi2hcs_ngff(czi_path, plate_name="MyPlate", overwrite=True, version="0.5")
print(f"Written: {zarr_path}")

# --- Standard 5D image conversion (ngff-zarr, OME-NGFF v0.5) ---
czi_path = Path("data/CellDivision5D.czi")
array, mdata = read_tools.read_6darray(str(czi_path), planes={"S": (0, 0)}, use_xarray=True)
array = array.squeeze("S")  # 6D (STCZYX) → 5D (TCZYX)
write_omezarr_ngff(array, czi_path.with_suffix("").with_suffix(".ome.zarr"), mdata,
                   scale_factors=[2, 4], overwrite=True, version="0.5")

# --- Validate any OME-ZARR file ---
validate_ome_zarr(zarr_path)  # True if valid, False otherwise
```

## Convert CZI from a Wellplate to HCS OME-ZARR: convert2hcs_omezarr.py

> **Note:** The standard single-scene `convert2omezarr.py` script has been moved to `_archive/`. For standard (non-HCS) conversions, use `scripts/create_omezarr_example.py` or import directly from `czi_omezarr_utils`.

General Usage Instructions:

```bash
python convert2hcs_omezarr.py --czifile ../data/WP96_4Pos_B4-10_DAPI.czi --use_ngffzarr --plate "MyPlate" --overwrite
```

Usage:

```txt
usage: convert2hcs_omezarr.py [-h] --czifile CZIFILE [--use_ngffzarr | --use_omezarr] [--zarr ZARR] [--plate PLATE] [--overwrite] [--validate]

Convert CZI files to OME-ZARR HCS (High Content Screening) format

options:
  -h, --help         show this help message and exit
  --czifile CZIFILE  Path to the input CZI file to convert (required)
  --use_ngffzarr     Use NGFF-ZARR format to create the HCS Plate Layout
  --use_omezarr      Use OME-ZARR format to create the HCS Plate Layout
  --zarr ZARR        Output path for the OME-ZARR file (default: <czifile>_ngff_plate.ome.zarr)
  --plate PLATE      Name of the well plate for metadata (default: 'Automated Plate')
  --overwrite        Overwrite existing OME-ZARR files if they exist (default: False)
  --validate         Validate the output OME-ZARR files (default: False)

Examples:
    # Basic conversion with default NGFF-ZARR format
    python convert2hcs_omezarr.py --czifile WP96_plate.czi

    # Use OME-ZARR format explicitly
    python convert2hcs_omezarr.py --czifile WP96_plate.czi --use_omezarr

    # Use NGFF-ZARR format explicitly
    python convert2hcs_omezarr.py --czifile WP96_plate.czi --use_ngffzarr

    # Specify custom output path and plate name
    python convert2hcs_omezarr.py --czifile WP96_plate.czi --zarr /path/to/output.ome.zarr --plate "Experiment_001"

    # Enable overwrite mode to replace existing files
    python convert2hcs_omezarr.py --czifile WP96_plate.czi --overwrite

Notes:
    - If no format is specified, NGFF-ZARR format is used by default
    - The output format follows the OME-NGFF specification for HCS data
    - Data is organized in a plate/well/field hierarchy
    - All conversion logs are saved to '<input_filename>_hcs_omezarr.log'
```

### Validate OME-ZARR output: validate_omezarr.py

After conversion, the resulting OME-ZARR files can be validated against the OME-NGFF v0.5
specification. The `validate_ome_zarr` function lives in `czi_omezarr_utils` and is also
exposed as a CLI via `scripts/validate_omezarr.py`:

```python
from czi_omezarr_utils import validate_ome_zarr

validate_ome_zarr("path/to/output.ome.zarr")
```

```bash
# CLI usage
python scripts/validate_omezarr.py data/WP96_4Pos_B4-10_DAPI_ngff_plate.ome.zarr
```

Both standard image and HCS plate layouts are supported.

### CZI - Normal Conversion Example Notebook

The process of converting an CZI to a normal OME-ZARR is explained in more detail here:

Jupyter Notebook - Conversion: [convert_czi2_omezarr.ipynb](notebooks/convert_czi2_omezarr.ipynb)

### CZI - HCS Conversion Example Notebook

The process of converting an CZI to a HCS OME-ZARR is explained in more detail here:

Jupyter Notebook - HCS Conversion: [convert_czi2hcs_omezarr.ipynb](notebooks/convert_czi2hcs_omezarr.ipynb)

## Analyze and HCS OME-ZARR

After the conversion it is very straight forward to analyze the resulting HCS OME-ZARR.

Jupyter Notebook - Image Analysis: [process_omezarr_HCS_plate.ipynb](notebooks/process_omezarr_HCS_plate.ipynb)

## Access HCS OME-ZARR with ngio

The [ngio](https://pypi.org/project/ngio/) package (≥ 0.5.9) provides a high-level API for
reading OME-ZARR HCS plates. An example is in `scripts/use_ngio.py`.

```python
import ngio

plate = ngio.open_ome_zarr_plate("data/WP96_4Pos_B4-10_DAPI_ngff_plate.ome.zarr")
container = ngio.open_ome_zarr_container("data/WP96_4Pos_B4-10_DAPI_ngff_plate.ome.zarr/B/04/0")
image = container.get_image()
```

The final result for that example is this heatmap:

![Heatmap from HCS OME-ZARR](images/heatmap.png)
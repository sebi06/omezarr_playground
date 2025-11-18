import marimo

__generated_with = "0.17.8"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(r"""
    ### Create OME-ZARR from a CZI image file

    * Select the OME-Package to be used
      * OME-ZARR: https://pypi.org/project/ome-zarr/
      * NGFF-ZARR: https://pypi.org/project/ngff-zarr/
    * Select the desired OME-ZARR Layout
      * `Normal Layout`: https://ngff.openmicroscopy.org/0.5/index.html#image-layout
      * `HCS Layout`: https://ngff.openmicroscopy.org/0.5/index.html#hcs-layout
    * Select the `SceneID` when using `Normal Layout`
    * read the CZI image & metadata
    * write array & metadata into an OME-ZARR file

    ---
    """)
    return


@app.cell
def _():
    import marimo as mo
    from czitools.read_tools import read_tools
    from czitools.metadata_tools.czi_metadata import CziMetadata
    import logging
    from ome_zarr_utils import (
        convert_czi2hcs_omezarr,
        convert_czi2hcs_ngff,
        omezarr_package,
        write_omezarr,
        write_omezarr_ngff
    )
    import ngff_zarr as nz
    from pathlib import Path
    from typing import Optional
    from importlib.metadata import version
    import ome_zarr
    import zarr
    return (
        CziMetadata,
        Path,
        convert_czi2hcs_ngff,
        convert_czi2hcs_omezarr,
        mo,
        nz,
        ome_zarr,
        read_tools,
        version,
        write_omezarr,
        write_omezarr_ngff,
        zarr,
    )


@app.cell
def _(mo, nz, ome_zarr, version, zarr):
    # show currently used version of NGFF specification
    mo.vstack(
        [
            mo.md(f"Using ngff format version: {ome_zarr.format.CurrentFormat().version}"),
            mo.md(f"ZARR Version: {zarr.__version__}"),
            mo.md(f"NGFF-ZARR Version: {nz.__version__}"),
            mo.md(f"OME-ZARR Version: {version('ome-zarr')}"),
            mo.md("---")
        ]
    )
    return


@app.cell
def _(Path, mo):
    try:
        parent_dir = Path(__file__).parent.parent / "data"
    except ValueError:
        parent_dir = None

    file_browser = mo.ui.file_browser(
        multiple=False, filetypes=[".czi"], restrict_navigation=False, initial_path=parent_dir, selection_mode="file", label="Select CZI file for conversion to OME-ZARR"
    )

    # Display the file browser
    mo.vstack([file_browser])
    return (file_browser,)


@app.cell
def _(file_browser):
    filepath = str(file_browser.path(0))
    return (filepath,)


@app.cell
def _(mo):
    dropdown_package = mo.ui.dropdown(
        options=["OME-ZARR Package", "NGFF-ZARR Package"], value="OME-ZARR Package", label="Choose Package for Conversion"
    )
    dropdown_hcs = mo.ui.dropdown(
        options=["Normal OME-ZARR", "HCS OME-ZARR (WellPlates)"], value="Normal OME-ZARR", label="Choose OME-ZARR Type"
    )
    return dropdown_hcs, dropdown_package


@app.cell
def _(dropdown_hcs, dropdown_package, mo):
    mo.vstack(
        [
            dropdown_package,
            dropdown_hcs,
        ]
    )
    return


@app.cell
def _(CziMetadata, dropdown_hcs, filepath, mo):
    mdata_tmp = CziMetadata(filepath)
    max_scenes = mdata_tmp.image.SizeS
    disable_scene = False

    if dropdown_hcs.value == "Normal OME-ZARR":
        if max_scenes is None:
            disable_scene = True
        else:
            disable_scene = False

    if dropdown_hcs.value == "Normal OME-ZARR":
        number = mo.ui.number(start=1, stop=mdata_tmp.image.SizeS, step=1, label="Scene Id (not used for HCS)", disabled=disable_scene)
    return max_scenes, number


@app.cell
def _(dropdown_hcs, mo, number):
    _output = None

    if dropdown_hcs.value == "Normal OME-ZARR":
        _output = mo.hstack([number, mo.md(f"Scene ID: {number.value}")])

    _output
    return


@app.cell
def _(
    Path,
    dropdown_hcs,
    dropdown_package,
    filepath,
    max_scenes,
    mo,
    number,
    read_tools,
    write_omezarr,
    write_omezarr_ngff,
):
    with mo.redirect_stderr():

        if dropdown_hcs.value == "Normal OME-ZARR":

            if max_scenes is None:
                scene_id = 0
            else:
                scene_id = number.value - 1

            # Read the CZI file as a 6D array with dimension order STCZYX(A)
            # S=Scene, T=Time, C=Channel, Z=Z-stack, Y=Height, X=Width
            array, mdata = read_tools.read_6darray(filepath, planes={"S": (scene_id, scene_id)}, use_xarray=True)

            # Extract the specified scene (remove Scene dimension to get 5D array)
            # write_omezarr requires 5D array (TCZYX), not 6D (STCZYX)
            array = array.squeeze("S")  # Remove the Scene dimension

            if dropdown_package.value == "OME-ZARR Package":

                # Generate output path with .ome.zarr extension
                zarr_output_path_normal: Path = Path(str(filepath)[:-4] + ".ome.zarr")

                # Write OME-ZARR using ome-zarr-py backend
                _ = write_omezarr(
                    array, zarr_path=str(zarr_output_path_normal), metadata=mdata, overwrite=True
                )

            elif dropdown_package.value == "NGFF-ZARR Package":

                # Generate output path with _ngff.ome.zarr extension
                zarr_output_path_normal: Path = Path(str(filepath)[:-4] + "_ngff.ome.zarr")

                # Write OME-ZARR using ngff-zarr backend with multi-resolution pyramid
                # scale_factors=[2, 4] creates 3 resolution levels (1x, 2x, 4x downsampled)
                _ = write_omezarr_ngff(array, zarr_output_path_normal, mdata, scale_factors=[2, 4], overwrite=True)
    return


@app.cell
def _(
    convert_czi2hcs_ngff,
    convert_czi2hcs_omezarr,
    dropdown_hcs,
    dropdown_package,
    filepath,
    mo,
):
    with mo.redirect_stderr():

        if dropdown_hcs.value == "HCS OME-ZARR (WellPlates)":

            if dropdown_package.value == "OME-ZARR Package":

                zarr_output_path_hcs = convert_czi2hcs_omezarr(filepath, overwrite=True)

            elif dropdown_package.value == "NGFF-ZARR Package":

                zarr_output_path_hcs = convert_czi2hcs_ngff(filepath, plate_name="TestWell96", overwrite=True)
    return (zarr_output_path_hcs,)


@app.cell
def _(dropdown_hcs, mo, nz, zarr_output_path_hcs):
    with mo.redirect_stderr():

        if dropdown_hcs.value == "HCS OME-ZARR (WellPlates)":

            # Validate the HCS-ZARR file against OME-NGFF specification
            # This ensures proper metadata structure for multi-well plate data
            hcs_plate = nz.from_hcs_zarr(zarr_output_path_hcs, validate=True)
    return (hcs_plate,)


@app.cell
def _(hcs_plate):
    hcs_plate.name
    return


@app.cell
def _(hcs_plate):
    hcs_plate.wells
    return


@app.cell
def _(hcs_plate):
    hcs_plate.field_count
    return


if __name__ == "__main__":
    app.run()

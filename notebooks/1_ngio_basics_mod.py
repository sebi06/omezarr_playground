# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "ngio==0.5.9",
#     "marimo",
#     "matplotlib",
#     "scikit-image",
#     "altair",
# ]
# ///

import marimo

__generated_with = "0.23.6"
app = marimo.App(width="full", auto_download=["html"])


@app.cell
def _():
    import marimo as mo
    from pathlib import Path

    return Path, mo


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div style="display:inline-block;font-family:'DM Mono',ui-monospace,monospace;font-size:0.7rem;font-weight:500;letter-spacing:0.1em;text-transform:uppercase;color:#3DBDB8;background:rgba(61,189,184,0.10);border:1px solid rgba(61,189,184,0.30);border-radius:99px;padding:2px 10px;">MODULE 01</div>

    # Introduction to ngio

    **ngio** is a Python library that provides a clean, object-oriented API for reading,
    writing, and exploring [OME-Zarr](https://ngff.openmicroscopy.org/) files.

    ### Goals of this notebook
    - Become familiar with ngio, its abstractions, and APIs.
    - Open, explore, and process an OME-Zarr container.
    - Integrate tabular data (ROIs, feature tables, and more).
    - Implement a basic image-processing pipeline:
      Maximum Intensity Projection → Basic segmentation → Feature extraction.
    - Perform quality control by linking image that and quantification in an interactive scatter plot.
    """)
    return


@app.cell(hide_code=True)
def _():
    # BVC matplotlib defaults — applied once for the whole notebook (STYLE.md §9).
    import matplotlib.pyplot as plt
    import numpy as np

    BVC_NAVY = "#1B2A4A"
    BVC_TEAL = "#3DBDB8"
    BVC_PALETTE = [
        "#3DBDB8",  # teal
        "#4A8FD4",  # blue
        "#5CB87A",  # green
        "#F4956A",  # orange
        "#FF7B9C",  # pink
        "#B6A3FF",  # purple
    ]
    BVC_FIGSIZE = (8, 8)

    from matplotlib import font_manager

    _installed_fonts = {f.name for f in font_manager.fontManager.ttflist}
    _font_family = [f for f in ("Inter", "DejaVu Sans", "sans-serif") if f in _installed_fonts or f == "sans-serif"]

    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": BVC_NAVY,
            "axes.labelcolor": BVC_NAVY,
            "axes.titlecolor": BVC_NAVY,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.linewidth": 0.8,
            "xtick.color": "#6B7A99",
            "ytick.color": "#6B7A99",
            "font.family": _font_family,
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "legend.frameon": False,
            "savefig.dpi": 150,
            "savefig.bbox": "tight",
            "image.cmap": "viridis",
        }
    )
    plt.rcParams["axes.prop_cycle"] = plt.cycler(color=BVC_PALETTE)
    return BVC_TEAL, np, plt


@app.cell(hide_code=True)
def _(mo):
    ngio_classes = mo.mermaid("""
        graph TD
            %% === STYLE DEFINITIONS (Easy to modify!) ===
            %% Container nodes - Main containers (BVC navy)
            classDef containerStyle fill:#1B2A4A,stroke:#0D1826,stroke-width:3px,color:#fff,font-weight:bold

            %% Multiscale nodes - Collections of pyramid levels (BVC teal)
            classDef multiscaleStyle fill:#3DBDB8,stroke:#278784,stroke-width:2px,color:#fff,font-weight:bold

            %% Image/Label nodes - Individual pyramid levels (BVC blue)
            classDef imageStyle fill:#4A8FD4,stroke:#2E5C8A,stroke-width:2px,color:#fff

            %% Table nodes - Data tables (BVC green)
            classDef tableStyle fill:#5CB87A,stroke:#3D7A54,stroke-width:2px,color:#fff,font-weight:bold

            %% === GRAPH STRUCTURE ===
            OZC["OmeZarrContainer"]

            OZC --> IMG["MultiscaleImage"]
            IMG --> IMGL0["Image(path='0')"]
            IMG --> IMGL1["Image(path='1')"]
            IMG --> IMGL2["..."]

            OZC --> LC["LabelsContainer"]
            LC --> OZLC-nuc["nuclei"]
            OZLC-nuc --> OZLC-nucL0["Label(path='0')"]
            OZLC-nuc --> OZLC-nucL1["Label(path='1')"]
            OZLC-nuc --> OZLC-nucL2["..."]
            LC --> OZLC-other["..."]

            OZC --> TBL["TablesContainer"]
            TBL --> TBL-roi["RoiTable"]
            TBL --> TBL-features["FeaturesTable"]
            TBL --> TBL-other["..."]

            %% === APPLY STYLES ===
            class OZC,LC,TBL containerStyle
            class IMG,OZLC-nuc,OZLC-other multiscaleStyle
            class IMGL0,IMGL1,IMGL2,OZLC-nucL0,OZLC-nucL1,OZLC-nucL2 imageStyle
            class TBL-roi,TBL-features,TBL-other tableStyle
        """)
    return (ngio_classes,)


@app.cell(hide_code=True)
def _(mo, ngio_classes):
    mo.md(rf"""
    ## 1 Overview

    ### Why OME-Zarr?

    OME-Zarr is the community-standardised file format for bioimaging
    ([NGFF](https://ngff.openmicroscopy.org/)). It stores images in **chunks**
    (so viewers and pipelines only read what they need), keeps a **multiscale
    pyramid** for fast zoom-out, and lives equally well on a local disk or in
    cloud object storage. ngio is a Pythonic layer on top of it.

    ### What is the OME-Zarr container?

    The `OmeZarrContainer` is your entry point. From it you can:

    - **Inspect** the OME-Zarr file: pyramid levels, channels, available labels and tables.
    - **Read images** at any resolution level / pixel size.
    - **Manage labels**: list, read, and create new segmentation masks.
    - **Manage tables**: list, read, and add ROI / feature / condition tables.
    - **Derive** new OME-Zarr images that share the source's metadata.
    - **Edit** OME-Zarr metadata through high-level APIs.

    {ngio_classes}

    ### What it isn't

    The container does **not** expose the pixel data directly — for that you
    ask it for an `Image`, `Label`, or `Table` object. The diagram above is
    the mental model to keep in mind for the rest of this notebook.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2 Setup

    We will use a small sample HCS plate (`CardiomyocyteTiny`) that ships with
    ngio's test datasets. The helper `download_ome_zarr_dataset` fetches it
    into a local temp directory the first time it runs (subsequent runs reuse
    the cached copy).

    We then open a single well image (`B/03/0`) as an `OmeZarrContainer`.
    HCS plates are organised as **row letter / column number / image
    index**, so `B/03/0` is *row B, column 3, image 0* — one well image out
    of the plate. This is the object we will work with throughout the
    notebook.
    """)
    return


@app.cell
def _(Path, mo):
    import ngio
    from ngio.utils import download_ome_zarr_dataset, list_ome_zarr_datasets
    from ngio import open_ome_zarr_plate
    import os

    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    # hcs_path = download_ome_zarr_dataset("CardiomyocyteTiny", download_dir=data_dir)
    hcs_path = Path(r"data\WP96_4Pos_B4-10_DAPI_ngff_plate.ome.zarr")
    image_path = hcs_path / "B" / "04" / "0"
    # hcs_path = Path(r"data\WP96_4Pos_B4-10_DAPI_ngff_plate.ome.zarr")

    os.path.exists(hcs_path)
    plate = ngio.open_ome_zarr_plate(hcs_path)
    hcs_zarr = open_ome_zarr_plate(hcs_path)
    print(hcs_zarr)
    print(f"Rows: {hcs_zarr.rows}, Columns: {hcs_zarr.columns}")

    ome_zarr_container = ngio.open_ome_zarr_container(image_path)
    image = ome_zarr_container.get_image()

    # Write an FOV_ROI_table if one doesn't already exist.
    # The CardiomyocyteTinyMip reference dataset ships with this table pre-baked
    # (written by Fractal during conversion). Our CZI-derived plate does not, so
    # we create a single ROI covering the full image for each well/position here.
    from ngio.tables import RoiTable as _RoiTable

    if "FOV_ROI_table" not in ome_zarr_container.list_tables():
        _shape = image.shape
        _axes = image.axes
        _y_len = float(_shape[_axes.index("y")])
        _x_len = float(_shape[_axes.index("x")])
        _z_len = float(_shape[_axes.index("z")]) if "z" in _axes else 1.0
        _fov_roi_table = _RoiTable(
            rois=[
                ngio.Roi(
                    name="FOV_0",
                    slices=[
                        ngio.RoiSlice(axis_name="x", start=0.0, length=_x_len),
                        ngio.RoiSlice(axis_name="y", start=0.0, length=_y_len),
                        ngio.RoiSlice(axis_name="z", start=0.0, length=_z_len),
                    ],
                    space="pixel",
                ).to_world(pixel_size=image.pixel_size)
            ]
        )
        ome_zarr_container.add_table(
            name="FOV_ROI_table",
            table=_fov_roi_table,
            overwrite=True,
        )

    # show actual Path
    mo.md(f"""Path: {hcs_path}""")
    plate.get_wells()
    return data_dir, image, image_path, ngio, ome_zarr_container


@app.cell(hide_code=True)
def _(ome_zarr_container, plot_image):
    plot_image(
        ome_zarr_container,
        # title="CardiomyocyteTiny, well B/03/0 (original image, level 0)",
        title="WP96_4Pos_B4-10_DAPI, well B04",
        axes_order="yx",
        z=0,
    )
    return


@app.cell(hide_code=True)
def _(image_path, mo):
    mo.md(f"""
    Opened container: `{image_path}`
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3 The ngio object model

    We will look at four pieces in turn:

    1. **`OmeZarrContainer`** — the file-level handle.
    2. **`Image`** and **`Label`** — pixel data, one resolution level at a time.
    3. **`Table`** — the tabular companion (ROIs, features, conditions, …).
    4. **`Deriving`** — how to spawn a new OME-Zarr that mirrors the source.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 3.1 OmeZarrContainer

    The container exposes the file's structure as plain Python attributes
    and methods. The most useful ones at a glance:
    """)
    return


@app.cell(hide_code=True)
def _(mo, ome_zarr_container):
    _rows = [
        "| Property | Value |",
        "|---|---|",
        f"| `levels` | `{ome_zarr_container.levels}` |",
        f"| `level_paths` | `{ome_zarr_container.level_paths}` |",
        f"| `is_3d` | `{ome_zarr_container.is_3d}` |",
        f"| `is_time_series` | `{ome_zarr_container.is_time_series}` |",
        f"| `channel_labels` | `{ome_zarr_container.channel_labels}` |",
        f"| `list_labels()` | `{ome_zarr_container.list_labels()}` |",
        f"| `list_tables()` | `{ome_zarr_container.list_tables()}` |",
    ]
    mo.md("\n".join(_rows))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### A note on multiscale pyramids

    `levels = 5` means this image is stored at **5 resolutions**: level `0`
    is the full-resolution data, and each subsequent level is a downsampled
    copy (typically a factor of 2 in XY).

    Throughout this notebook, `path="0"` means *full resolution*; pass
    `path="1"`, `"2"`, … to read a coarser, smaller copy.
    """)
    return


@app.cell
def _():
    from ngio import create_ome_zarr_from_array, create_empty_ome_zarr

    # TODOs Create a sample image container
    return


@app.cell(hide_code=True)
def _(image, mo):
    mo.md(rf"""
    ### 3.2 Images and Labels

    An **`Image`** represents **one resolution level** of the multiscale
    pyramid. Get it from the container:

    ```python
    image = ome_zarr_container.get_image()                              # full resolution (default)
    image = ome_zarr_container.get_image(path="1")                      # specific pyramid level
    image = ome_zarr_container.get_image(pixel_size=ps, strict=False)   # nearest matching resolution
    ```

    Key properties of the image we just opened:

    | Property | Value |
    |---|---|
    | `dimensions` | `{image.dimensions}` |
    | `pixel_size` | `{image.pixel_size}` |
    | `shape` | `{image.shape}` |
    | `axes` | `{image.axes}` |
    | `dtype` | `{image.dtype}` |

    `pixel_size` is given in physical units (here micrometers) and is the
    bridge between **world coordinates** (ROI tables, scale bars) and
    **pixel coordinates** (numpy slices). `axes` tells you the order of
    the array axes — in our case `c, z, y, x`.

    Key methods:

    - **`image.get_as_numpy(...)`** — eager read into RAM. Use this for
      small ROIs you'll work on in memory.
    - **`image.get_as_dask(...)`** — lazy read. Use it when the array is
      larger than RAM, or when you want to compose lazy operations (the
      MIP further down is a good example).
    - **`image.set_array(...)`** — write data back into the OME-Zarr.
    - **`image.consolidate()`** — rebuild the lower-resolution pyramid
      levels from the data you just wrote at level 0.

    A **`Label`** stores **integer segmentation masks**. It shares the
    image's multiscale pyramid but sometimes has no channel axis. The API
    mirrors `Image` exactly:

    ```python
    ome_zarr_container.list_labels()                                            # discover labels
    label = ome_zarr_container.get_label("nuclei")                              # full resolution
    label = ome_zarr_container.get_label("nuclei", path="1")                    # specific level
    label = ome_zarr_container.get_label("nuclei", pixel_size=image.pixel_size) # matching resolution
    ```
    """)
    return


@app.cell
def _():
    # TODOs let's play with the sample OME-Zarr container
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 3.3 Tables

    Tables in ngio are described along **three independent axes** — any
    combination is valid, so you can pick the storage you need without
    giving up the in-memory view or the semantic structure you want.

    - **Backend** *(on-disk storage)*: `AnnData` (default), `CSV`,
      `Parquet`, `JSON`, …your own.
    - **Object** *(in-memory view)*: `AnnData`, `pandas.DataFrame`,
      `polars.LazyFrame`. Every table exposes all three via `.anndata`,
      `.dataframe`, and `.lazy_frame` regardless of the backend.
    - **Type** *(expected layout)*: `FeatureTable`, `RoiTable`,
      `MaskingRoiTable`, `ConditionTable`, …your own.

    A short note on two ROI table flavours we will use later:

    - A **`RoiTable`** lists arbitrary regions (e.g. one ROI per
      field-of-view).
    - A **`MaskingRoiTable`** is **derived from a label image** — one
      bounding ROI per object — and is what you want for "zoom into one
      nucleus" workflows.

    The three axes meet at the read/write idiom:

    ```python
    ome_zarr_container.add_table(
        name="my_features",
        table=FeatureTable(feature_df, reference_label="basic_segmentation"),
        backend="parquet",          # any backend
        overwrite=True,
    )

    table = ome_zarr_container.get_feature_table("my_features")  # type-aware access
    table.dataframe                                              # or .lazy_frame / .anndata
    ```

    Use `ome_zarr_container.list_tables()` (optionally with
    `filter_types="masking_roi_table"`, `"feature_table"`, …) to discover
    what's already on a container.
    """)
    return


@app.cell
def _():
    from ngio.tables import RoiTable, MaskingRoiTable, FeatureTable
    import pandas as pd

    # TODOs Create a couple of sample tables
    return FeatureTable, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 3.4 Deriving new Images and Labels

    `derive_image` creates a **new OME-Zarr container** that clones the
    pyramid structure, pixel sizes, and channel metadata of the source —
    ready to be filled with processed data:

    ```python
    derived = ome_zarr_container.derive_image("output.zarr", overwrite=True)
    ```

    Typical write-back pattern:

    ```python
    out_image = derived.get_image()
    out_image.set_array(processed_data)   # write to level 0
    out_image.consolidate()               # rebuild the coarser pyramid levels
    ```

    > **Why call `consolidate()`?** When you write to level 0, the lower
    > pyramid levels (1, 2, …) still hold the *old* data. `consolidate()`
    > re-downsamples level 0 into all remaining levels so the pyramid is
    > internally consistent. You can skip it if you only ever read level
    > 0, but viewers will show stale data at lower resolutions.

    `derive_label` is the analogous helper for adding a new **empty label**
    to an existing container:

    ```python
    new_label = ome_zarr_container.derive_label("my_segmentation", overwrite=True)
    new_label.set_array(mask)
    new_label.consolidate()
    ```

    Below we derive a new container that project along the Z axes (we'll
    store a 2-D Maximum Intensity Projection in it) and bumps the metadata
    to NGFF v0.5. The shape of a derived container can differ from the
    source but must keep the **same number of axes** (channels excepted).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4 Putting it together — a basic 2D nuclei pipeline

    We now chain three steps that mirror a typical 2-D
    nuclei-counting workflow:

    1. **Derive** — setup a new ome-zarr container
    2. **Maximum Intensity Projection** — collapse the Z stack into a 2-D image.
    3. **Basic segmentation** — detect each nucleus.
    4. **Feature extraction** — measure size, intensity, shape per object.
    5. **Interactive feature exploration**
    """)
    return


@app.cell(hide_code=True)
def _(ngio, np, plt):
    from matplotlib import colors as _colors
    from matplotlib.patches import Rectangle as _Rectangle

    _BVC_TEAL = "#3DBDB8"
    _cycled = np.random.rand(1000, 3)
    _cycled[0] = [0, 0, 0]  # background is always black
    _LABEL_CMAP = _colors.ListedColormap(_cycled)

    def _add_scale_bar(ax, pixel_size_um, length_um=50.0):
        bar_px = length_um / pixel_size_um
        x_max = ax.get_xlim()[1]
        y_max = ax.get_ylim()[0]  # imshow origin='upper': bottom == max
        pad_x = 0.04 * x_max
        pad_y = 0.04 * y_max
        x0 = x_max - pad_x - bar_px
        y0 = y_max - pad_y
        ax.plot(
            [x0, x0 + bar_px],
            [y0, y0],
            color="white",
            linewidth=3,
            solid_capstyle="butt",
        )
        ax.text(
            x0 + bar_px / 2,
            y0 - 0.015 * y_max,
            f"{length_um:g} µm",
            color="white",
            ha="center",
            va="bottom",
            fontsize=9,
            fontweight="bold",
        )

    def plot_image(
        ome_zarr,
        path=None,
        title="",
        label=None,
        roi_table=None,
        figsize=(8, 8),
        scale_bar_um=50.0,
        **kwargs,
    ):
        image = ome_zarr.get_image(path=path)
        img = image.get_as_numpy(**kwargs)

        fig, ax = plt.subplots(figsize=figsize)
        ax.imshow(img, cmap="gray")
        ax.set_title(title)
        ax.axis("off")

        if label is not None:
            lbl = ome_zarr.get_label(label, path=path)
            label_kwargs = {k: v for k, v in kwargs.items() if k != "channel_selection"}
            lbl_img = lbl.get_as_numpy(**label_kwargs)
            ax.imshow(lbl_img, cmap=_LABEL_CMAP, interpolation="nearest", alpha=0.5)

        if roi_table is not None:
            table = ome_zarr.get_generic_roi_table(roi_table)
            for roi in table.rois():
                px_roi = roi.to_pixel(pixel_size=image.pixel_size)
                xs, ys = px_roi.get("x"), px_roi.get("y")
                if xs is None or ys is None or xs.start is None or ys.start is None:
                    continue
                ax.add_patch(
                    _Rectangle(
                        (xs.start, ys.start),
                        xs.length,
                        ys.length,
                        fill=False,
                        edgecolor=_BVC_TEAL,
                        linewidth=0.8,
                    )
                )

        if scale_bar_um is not None and getattr(image.pixel_size, "x", None):
            _add_scale_bar(ax, pixel_size_um=image.pixel_size.x, length_um=scale_bar_um)

        fig.tight_layout()
        plt.show()

    def compare_containers(orig: ngio.OmeZarrContainer, deriv: ngio.OmeZarrContainer):
        attrs = ("levels", "level_paths", "is_3d", "channel_labels")
        rows = [
            "| Attribute | Original | Derived |  |",
            "|---|---|---|---:|",
        ]
        for attr in attrs:
            o, d = getattr(orig, attr), getattr(deriv, attr)
            marker = "✅ same" if o == d else "🔄 changed"
            rows.append(f"| `{attr}` | `{o}` | `{d}` | {marker} |")
        orig_img = orig.get_image()
        deriv_img = deriv.get_image()
        for attr in ("dimensions", "shape", "axes", "dtype"):
            o, d = getattr(orig_img, attr), getattr(deriv_img, attr)
            marker = "✅ same" if o == d else "🔄 changed"
            rows.append(f"| `image.{attr}` | `{o}` | `{d}` | {marker} |")

        o = orig_img.meta.version
        d = deriv.meta.version
        marker = "✅ same" if o == d else "🔄 changed"
        rows.append(f"| `image.meta.version` | `{o}` | `{d}` | {marker} |")

        o = orig_img.zarr_array.metadata.zarr_format
        d = deriv_img.zarr_array.metadata.zarr_format
        marker = "✅ same" if o == d else "🔄 changed"
        rows.append(f"| `zarr_version` | `{o}` | `{d}` | {marker} |")
        return "\n".join(rows)

    return compare_containers, plot_image


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 4.1 Derive a new container

    We will create a new OME-Zarr container that holds the Maximum Intensity Projection.
    """)
    return


@app.cell
def _(data_dir, image, ome_zarr_container):
    # Source axes are (c, z, y, x). The derived MIP keeps the same layout
    # but reduces both c and z to length 1 (we only keep DAPI-MIP and
    # collapse Z). YX is taken from the source so it stays in lockstep
    # with the sample dataset.
    _y, _x = image.shape[-2], image.shape[-1]
    derived_ome_zarr = ome_zarr_container.derive_image(
        data_dir / "derived.zarr",
        shape=(1, 1, 1, _y, _x),
        channels_meta=["DAPI-MIP"],
        ngff_version="0.5",
        overwrite=True,
    )
    return (derived_ome_zarr,)


@app.cell(hide_code=True)
def _(compare_containers, derived_ome_zarr, mo, ome_zarr_container):
    mo.md(
        "**Original vs derived container.** The derived container keeps the "
        "multiscale + channel structure of the source but updates shape, "
        "channel labels, and NGFF version:\n\n" + compare_containers(ome_zarr_container, derived_ome_zarr)
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 4.2 Maximum Intensity Projection

    We project the source image along the Z axis to get a single 2-D
    image per channel, then write the result back into our derived
    container.
    """)
    return


@app.cell
def _(derived_ome_zarr, ome_zarr_container, plot_image):
    image_origin = ome_zarr_container.get_image()
    image_data_lazy = image_origin.get_as_dask()  # axes: (c, z, y, x)

    # Max intensity projection on the fly with dask, without loading the
    # whole image into RAM. `axis=1` is Z (axes are CZYX, so axis 0 = C,
    # axis 1 = Z).
    image_data_lazy_mip = image_data_lazy.max(axis=1)

    # `set_array` requires the destination axis layout (C, Z, Y, X) — we
    # collapsed Z but the derived container still has a length-1 Z axis,
    # so re-introduce a singleton axis at position 1.
    image_data_lazy_mip = image_data_lazy_mip[:, None, ...]

    derived_image = derived_ome_zarr.get_image()
    derived_image.set_array(image_data_lazy_mip)
    derived_image.consolidate()  # build the pyramid levels

    plot_image(
        derived_ome_zarr,
        title="Maximum Intensity Projection (derived image, level 0)",
        axes_order="yx",
    )
    return (derived_image,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 4.3 Basic segmentation

    `basic_segmentation` chains a small set of `scikit-image` primitives.
    The five steps, in plain language:

    1. **Smooth** the image with a Gaussian filter to suppress noise.
    2. **Threshold** with Otsu's method to get a foreground mask.
    3. **Find object centres** via the distance transform + local-peak
       detection.
    4. **Watershed** from those centres to split touching nuclei.
    5. **Clean up** by dropping objects below 500 pixels.

    We then write the resulting label image back to the container as
    `basic_segmentation`, and build a `MaskingRoiTable` from it — one
    bounding box per nucleus, which we will reuse in §4.4.
    """)
    return


@app.cell
def _(derived_image, derived_ome_zarr, np, plot_image):
    from scipy import ndimage as ndi
    from skimage.feature import peak_local_max
    from skimage.filters import threshold_otsu
    from skimage.morphology import remove_small_objects
    from skimage.segmentation import watershed

    def basic_segmentation(image_data):
        # Smooth → Otsu threshold → distance transform → seeded watershed → cleanup
        image_data = ndi.gaussian_filter(image_data, sigma=4)
        mask = image_data > threshold_otsu(image_data)
        distance = ndi.distance_transform_edt(mask)
        coords = peak_local_max(distance, min_distance=20, labels=mask)
        markers = np.zeros(distance.shape, dtype=np.int32)
        markers[tuple(coords.T)] = np.arange(1, len(coords) + 1)
        seg = watershed(-distance, markers, mask=mask).astype(np.uint16)
        seg = remove_small_objects(seg, max_size=500)
        return seg

    image_data = derived_image.get_as_numpy(channel_selection="DAPI-MIP", axes_order="yx")
    segmentation_mask = basic_segmentation(image_data)

    # Derive a new label and write the segmentation mask back to the OME-Zarr
    derived_label = derived_ome_zarr.derive_label("basic_segmentation", overwrite=True)
    derived_label.set_array(segmentation_mask, axes_order="yx")
    derived_label.consolidate()

    plot_image(
        derived_ome_zarr,
        title="Basic segmentation (derived label, level 0)",
        label="basic_segmentation",
        axes_order="yx",
    )

    # Build one bounding ROI per labelled nucleus and store it on the container.
    roi_table = derived_ome_zarr.build_masking_roi_table(label="basic_segmentation")
    derived_ome_zarr.add_table(
        name="basic_segmentation_ROI_table",
        table=roi_table,
        overwrite=True,
        backend="csv",
    )

    plot_image(
        derived_ome_zarr,
        title="Per-object ROIs from the masking ROI table",
        roi_table="basic_segmentation_ROI_table",
        axes_order="yx",
    )
    return (derived_label,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 4.4 Feature extraction

    For each segmented nucleus we measure a handful of region properties
    with `scikit-image.regionprops_table`, and store them as a typed
    `FeatureTable` on the container. The `reference_label` argument links
    back to the label image from which the measurements come from.
    """)
    return


@app.cell
def _(derived_ome_zarr):
    # List what's already on the container — we will add to this.
    derived_ome_zarr.list_tables()
    return


@app.cell
def _(FeatureTable, derived_image, derived_label, derived_ome_zarr, np, pd):
    from skimage.measure import regionprops_table

    def compute_region_props(segmentation_mask: np.ndarray, image_data: np.ndarray):
        props = regionprops_table(
            segmentation_mask,
            intensity_image=image_data,
            properties=(
                "label",
                "area",
                "mean_intensity",
                "max_intensity",
                "min_intensity",
                "centroid",
                "eccentricity",
                "solidity",
            ),
        )
        return pd.DataFrame(props)

    segmentation_mask2 = derived_label.get_as_numpy(axes_order="yx")
    image_data2 = derived_image.get_as_numpy(channel_selection="DAPI-MIP", axes_order="yx")
    feature_df = compute_region_props(segmentation_mask2, image_data2)

    feature_table = FeatureTable(feature_df, reference_label="basic_segmentation")
    derived_ome_zarr.add_table(
        name="basic_segmentation_features",
        table=feature_table,
        backend="csv",
        overwrite=True,
    )

    # Only for marimo display
    feature_table.lazy_frame.collect()  # compute the table (if there are lazy computations)
    return (feature_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### 4.5 Interactive feature exploration

    Pick any two numeric columns to scatter the per-object features.
    **Click a single point** in the scatter on the left to render the
    matching segmented object on the right (use the `Zoom` slider to
    widen the field of view around it). The selected object's
    segmentation boundary is outlined in BVC teal.
    """)
    return


@app.cell
def _(derived_ome_zarr):
    derived_image_plot = derived_ome_zarr.get_image()
    derived_label_plot = derived_ome_zarr.get_label("basic_segmentation")

    feature_table_plot = derived_ome_zarr.get_feature_table("basic_segmentation_features")
    masking_roi_table_plot = derived_ome_zarr.get_masking_roi_table("basic_segmentation_ROI_table")
    return (
        derived_image_plot,
        derived_label_plot,
        feature_table_plot,
        masking_roi_table_plot,
    )


@app.cell(hide_code=True)
def _(feature_df, mo):
    numeric_cols = list(feature_df.select_dtypes("number").columns)
    x_axis = mo.ui.dropdown(numeric_cols, value="area", label="X axis")
    y_axis = mo.ui.dropdown(numeric_cols, value="mean_intensity", label="Y axis")
    zoom = mo.ui.slider(1.0, 15.0, value=2.0, step=0.1, label="Zoom (preview)")
    mo.hstack([x_axis, y_axis, zoom], justify="start")
    return x_axis, y_axis, zoom


@app.cell(hide_code=True)
def _(feature_table_plot, mo, x_axis, y_axis):
    import altair as alt

    feature_df_alt = feature_table_plot.dataframe

    feature_chart = mo.ui.altair_chart(
        alt.Chart(feature_df_alt)
        .mark_circle(size=40, opacity=0.9, color="#3DBDB8")
        .encode(
            x=alt.X(f"{x_axis.value}:Q", title=x_axis.value),
            y=alt.Y(f"{y_axis.value}:Q", title=y_axis.value),
            tooltip=list(feature_df_alt.columns),
        )
        .properties(width=700, height=400)
        .interactive(),
        chart_selection="point",
    )
    return (feature_chart,)


@app.cell(hide_code=True)
def _(
    BVC_TEAL,
    derived_image_plot,
    derived_label_plot,
    feature_chart,
    masking_roi_table_plot,
    mo,
    plt,
    zoom,
):
    _selection = feature_chart.value
    _selection = _selection.reset_index() if _selection is not None and len(_selection) else None
    _selected_labels = _selection["label"].tolist() if _selection is not None and len(_selection) else []

    if len(_selected_labels) != 1:
        mo.md(
            "No point or multiple points selected. Please select a single point "
            "on the scatter plot to preview the corresponding segmented object."
        )
        _selected_labels = [1]

    _lbl = _selected_labels[0]
    _fig, _ax = plt.subplots(figsize=(6, 6))
    _roi = masking_roi_table_plot.get_label(_lbl).zoom(zoom.value)
    _img = derived_image_plot.get_roi_as_numpy(_roi, channel_selection="DAPI-MIP", axes_order="yx")
    _mask = derived_label_plot.get_roi_as_numpy(_roi, axes_order="yx")
    _ax.imshow(_img, cmap="gray")
    _ax.contour(_mask == _lbl, levels=[0.5], colors=BVC_TEAL, linewidths=1.5)
    _ax.set_title(f"label {_lbl}")
    _ax.axis("off")
    _fig.tight_layout()
    preview = _fig

    mo.hstack([feature_chart, preview], align="start", widths=[1, 1])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5 Next steps

    That covers ngio's core: containers, images, labels, tables, and the
    derive APIs that let you write a full pipeline back into a single
    OME-Zarr file.

    **Next:** [`2_iterators.py`](./2_iterators.py) covers ngio's
    **iterators** — the pattern that lets you scale this same MIP →
    segment → measure pipeline to images that don't fit in RAM.
    """)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "ngio==0.5.9",
#     "marimo",
#     "matplotlib",
#     "scikit-image",
#     "altair",
#     "pandas",
# ]
# ///

import marimo

__generated_with = "0.23.4"
app = marimo.App(
    width="full",
    layout_file="layouts/2_iterators.grid.json",
    auto_download=["html"],
)


@app.cell
def _():
    import marimo as mo
    from pathlib import Path

    return Path, mo


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    <div style="display:inline-block;font-family:'DM Mono',ui-monospace,monospace;font-size:0.7rem;font-weight:500;letter-spacing:0.1em;text-transform:uppercase;color:#3DBDB8;background:rgba(61,189,184,0.10);border:1px solid rgba(61,189,184,0.30);border-radius:99px;padding:2px 10px;">MODULE 02</div>

    # Iterators in ngio

    ### Goals of this notebook
    - Understand when ngio iterators are needed and what problems they solve.
    - Learn how to set up and use a ngio iterator.
    - Use `SegmentationIterator` to build an instance segmentation, both with the
      stateless `map_as_numpy` API and the stateful `iter_as_numpy` loop.

    > **Note:** iterators in ngio are very new and the API surface may still
    > shift between releases.
    """)
    return


@app.cell(hide_code=True)
def _():
    # BVC matplotlib defaults — applied once for the whole notebook (STYLE.md §9).
    import matplotlib.pyplot as plt

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
    return (plt,)


@app.cell(hide_code=True)
def _(plt):
    from matplotlib import colors as _colors
    from matplotlib.patches import Rectangle as _Rectangle
    import numpy as np

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
        path="0",
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

    return np, plot_image


@app.cell(hide_code=True)
def _(mo):
    iter_builder_image = mo.image(
        src="https://raw.githubusercontent.com/BioVisionCenter/ngio-workshop/refs/heads/main/notebooks/assets/iterators-builder.png"
    )

    iter_run_graph = mo.mermaid(r"""
    graph LR
        %% === STYLE DEFINITIONS ===
        classDef multiscaleStyle fill:#3DBDB8,stroke:#278784,stroke-width:2px,color:#fff,font-weight:bold
        classDef imageStyle fill:#4A8FD4,stroke:#2E5C8A,stroke-width:2px,color:#fff
        classDef tableStyle fill:#5CB87A,stroke:#3D7A54,stroke-width:2px,color:#fff,font-weight:bold

        %% === GRAPH STRUCTURE ===
        READ["read_patch"] --> FN["my_fn"]
        FN --> WRITE["write_patch"]
        WRITE -->|next patch| READ
        WRITE -->|all patches done| CONS["consolidate"]

        %% === APPLY STYLES ===
        class READ,WRITE imageStyle
        class FN multiscaleStyle
        class CONS tableStyle
    """)

    iter_t_run_graph = mo.mermaid(r"""
    graph LR
        %% === STYLE DEFINITIONS ===
        classDef multiscaleStyle fill:#3DBDB8,stroke:#278784,stroke-width:2px,color:#fff,font-weight:bold
        classDef imageStyle fill:#4A8FD4,stroke:#2E5C8A,stroke-width:2px,color:#fff
        classDef tableStyle fill:#5CB87A,stroke:#3D7A54,stroke-width:2px,color:#fff,font-weight:bold

        %% === GRAPH STRUCTURE ===
        READ["read_patch"] --> TF1[In-Transform]
        TF1 --> TF2[...]
        TF2 --> FN["my_fn"]
        FN --> TF3[...]
        TF3 --> TF4[Out-Transform]
        TF4 --> WRITE["write_patch"]
        WRITE -->|next patch| READ

        %% === APPLY STYLES ===
        class READ,WRITE imageStyle
        class FN multiscaleStyle
        class CONS tableStyle
    """)
    return iter_builder_image, iter_run_graph, iter_t_run_graph


@app.cell(hide_code=True)
def _(iter_builder_image, iter_run_graph, mo):
    mo.md(rf"""
    ## 1 Why iterators?

    - **Reusable processing units** — make it very simple to write image processing routine that generalize.
    - **Larger-than-RAM images** — process the images in small patches.
    - **(Future) Free optimization** — parallelization, efficient read/write.

    > **Warning!** Iterators are very much work in progress!

    ### 1.1 Two phases

    An iterator has two phases — a **builder phase** where you declare *what*
    to iterate over, and an **execution phase** where the actual processing
    function runs patch by patch.

    ### 1.2 Builder phase

    {iter_builder_image}

    *The schematic above shows how a builder is composed: you start from an
    input image (and, for write-back iterators, an output image or label),
    then chain region selectors (`.product`, `.by_yx`, `.by_zyx`, …) to
    decide which patches the execution phase will visit.*

    Instantiate an iterator:

    ```python
    iterator = SomeIterator(input_image=..., output=...)
    ```

    Build the regions it will visit:

    ```python
    iterator = (
        iterator
        .product(roi_table)   # one patch per ROI in roi_table (e.g. one per FOV)
        .by_zyx()             # for each ROI, hand out a 3-D ZYX block
                              #   (use .by_yx() for 2-D YX patches instead)
    )
    ```

    `.product(...)` restricts the iteration to a list of spatial regions
    (any `RoiTable` or list of `Roi` objects). `.by_yx()` / `.by_zyx()` then
    declares the **patch shape** the user code will receive — broadcasting
    over the remaining axes (time, z, …).

    ### 1.3 Execution phase

    {iter_run_graph}

    Run **stateless** — apply a pure function to every patch. ngio handles
    reading, applying, and writing back:

    ```python
    iterator.map_as_numpy(my_fn)
    ```

    Run **stateful** — drive the loop yourself when you need state across
    patches (e.g. a running counter), and call the writer manually:

    ```python
    for patch, writer in iterator.iter_as_numpy():
        result = my_stateful_fn(patch)
        writer(patch=result)
    ```

    ### 1.4 Built-in iterators

    ngio ships four iterator types. This notebook focuses on
    `SegmentationIterator`; the other three follow the same builder /
    execution pattern.

    | Iterator | Use case |
    |---|---|
    | `ImageProcessingIterator` | Image-to-image operations (filtering, intensity correction, …) |
    | `SegmentationIterator` | Image-to-label operations (segmentation) |
    | `MaskedSegmentationIterator` | Image-to-label operations restricted to a masking ROI table |
    | `FeatureExtractorIterator` | Read-only per-object measurements and aggregation |
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2 Setup

    We use the `CardiomyocyteTinyMip` sample dataset — a single well image
    with one DAPI channel, one Z-plane (MIP), and an `FOV_ROI_table`. The
    FOV ROI table is one entry per microscope field of view; we will use it
    as the default iteration grid when no custom ROIs are drawn.
    """)
    return


@app.cell
def _(Path):
    import ngio
    from ngio.utils import download_ome_zarr_dataset

    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    # hcs_path = download_ome_zarr_dataset(
    #     "CardiomyocyteTinyMip", download_dir=data_dir
    # )
    # image_path = hcs_path / "B" / "03" / "0"
    hcs_path = Path(r"data\WP96_4Pos_B4-10_DAPI_ngff_plate.ome.zarr")
    image_path = hcs_path / "B" / "04" / "0"
    ome_zarr = ngio.open_ome_zarr_container(image_path)

    image = ome_zarr.get_image()
    try:
        fov_table = ome_zarr.get_roi_table("FOV_ROI_table")
    except Exception:
        # No FOV_ROI_table in this image — create a synthetic one covering
        # the full field of view so downstream cells still work.
        from ngio.tables import RoiTable

        _shape = image.shape
        _axes = image.axes
        _y_len = float(_shape[_axes.index("y")])
        _x_len = float(_shape[_axes.index("x")])
        _z_len = float(_shape[_axes.index("z")]) if "z" in _axes else 1.0
        fov_table = RoiTable(
            rois=[
                ngio.Roi(
                    name="full_fov",
                    slices=[
                        ngio.RoiSlice(axis_name="x", start=0.0, length=_x_len),
                        ngio.RoiSlice(axis_name="y", start=0.0, length=_y_len),
                        ngio.RoiSlice(axis_name="z", start=0.0, length=_z_len),
                    ],
                    space="pixel",
                ).to_world(pixel_size=image.pixel_size)
            ]
        )
    return fov_table, image, ngio, ome_zarr


@app.cell(hide_code=True)
def _(fov_table, image, mo):
    mo.md(f"""
    **Sample image opened.**

    | Property | Value |
    |---|---|
    | `shape` | `{image.shape}` |
    | `axes` | `{image.axes}` |
    | `channel_labels` | `{image.channel_labels}` |
    | `FOV_ROI_table` regions | `{[r.name for r in fov_table.rois()]}` |
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3 SegmentationIterator — stateless `map_as_numpy`

    We will run the same `basic_segmentation` function used in notebook 1
    over a `SegmentationIterator`. First we let the user pick the ROIs the
    iterator should visit, then we hand the function to `map_as_numpy(...)`.

    ### 3.1 Draw your own ROIs
    """)
    return


@app.cell
def _(np):
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

    return (basic_segmentation,)


@app.cell(hide_code=True)
def _(image, mo):
    import base64
    from io import BytesIO

    import altair as alt
    import pandas as pd
    from matplotlib import image as mpimg

    iter_raw = image.get_as_numpy(axes_order=["y", "x"], c=0, z=0)
    iter_H, iter_W = iter_raw.shape

    _ds = max(1, max(iter_H, iter_W) // 1280)
    _png_buf = BytesIO()
    mpimg.imsave(_png_buf, iter_raw[::_ds, ::_ds], cmap="gray", format="png")
    _data_url = "data:image/png;base64," + base64.b64encode(_png_buf.getvalue()).decode()

    _chart_w = 720
    _chart_h = max(120, int(_chart_w * iter_H / iter_W))

    _scale_x = alt.Scale(domain=[0, iter_W], nice=False)
    _scale_y = alt.Scale(domain=[0, iter_H], reverse=True, nice=False)

    _img_layer = (
        alt.Chart(pd.DataFrame([{"url": _data_url, "x": 0, "y": 0}]))
        .mark_image(width=_chart_w, height=_chart_h, align="left", baseline="top")
        .encode(
            url="url:N",
            x=alt.X("x:Q", scale=_scale_x, title="x (px)"),
            y=alt.Y("y:Q", scale=_scale_y, title="y (px)"),
        )
    )

    _anchor_layer = (
        alt.Chart(pd.DataFrame({"x": [0, iter_W], "y": [0, iter_H]}))
        .mark_point(opacity=0)
        .encode(
            x=alt.X("x:Q", scale=_scale_x),
            y=alt.Y("y:Q", scale=_scale_y),
        )
    )

    _base_chart = alt.layer(_img_layer, _anchor_layer).properties(width=_chart_w, height=_chart_h)

    iter_roi_chart = mo.ui.altair_chart(_base_chart, chart_selection="interval")
    iter_add_btn = mo.ui.run_button(label="Add ROI", kind="success")
    iter_reset_btn = mo.ui.run_button(label="Reset", kind="warn")
    iter_get_rois, iter_set_rois = mo.state([])
    return (
        iter_H,
        iter_W,
        iter_add_btn,
        iter_get_rois,
        iter_raw,
        iter_reset_btn,
        iter_roi_chart,
        iter_set_rois,
    )


@app.cell(hide_code=True)
def _(
    fov_table,
    image,
    iter_H,
    iter_W,
    iter_add_btn,
    iter_get_rois,
    iter_raw,
    iter_reset_btn,
    iter_roi_chart,
    iter_set_rois,
    mo,
    ngio,
    plt,
):
    from matplotlib.patches import Rectangle
    from ngio.tables import RoiTable

    def _brush_extent(selections):
        if not selections:
            return None
        for _val in selections.values():
            if isinstance(_val, dict) and "x" in _val and "y" in _val:
                _xs, _ys = _val["x"], _val["y"]
                if len(_xs) == 2 and len(_ys) == 2:
                    return tuple(_xs), tuple(_ys)
        return None

    _prev = iter_get_rois()
    if iter_reset_btn.value:
        _rois = []
        iter_set_rois(_rois)
    elif iter_add_btn.value:
        _extent = _brush_extent(iter_roi_chart.selections)
        if _extent is not None:
            (_xa, _xb), (_ya, _yb) = _extent
            _x0 = max(0, int(round(min(_xa, _xb))))
            _x1 = min(iter_W, int(round(max(_xa, _xb))))
            _y0 = max(0, int(round(min(_ya, _yb))))
            _y1 = min(iter_H, int(round(max(_ya, _yb))))
            if _x1 > _x0 and _y1 > _y0:
                _rois = _prev + [(_x0, _y0, _x1 - _x0, _y1 - _y0)]
                iter_set_rois(_rois)
            else:
                _rois = _prev
        else:
            _rois = _prev
    else:
        _rois = _prev

    if _rois:
        iter_roi_table = RoiTable(
            rois=[
                ngio.Roi(
                    name=f"user_roi_{_i}",
                    slices=[
                        ngio.RoiSlice(axis_name="x", start=float(_x), length=float(_w)),
                        ngio.RoiSlice(axis_name="y", start=float(_y), length=float(_h)),
                        ngio.RoiSlice(axis_name="z", start=0.0, length=1.0),
                    ],
                    space="pixel",
                ).to_world(pixel_size=image.pixel_size)
                for _i, (_x, _y, _w, _h) in enumerate(_rois, start=1)
            ]
        )
    else:
        iter_roi_table = fov_table

    _fig, _ax = plt.subplots(figsize=(7, max(2.0, 7.0 * iter_H / iter_W)))
    _ax.imshow(iter_raw, cmap="gray")
    _ax.axis("off")
    if _rois:
        _ax.set_title(f"ROI preview — {len(_rois)} drawn")
        for _x, _y, _w, _h in _rois:
            _ax.add_patch(
                Rectangle(
                    (_x, _y),
                    _w,
                    _h,
                    fill=False,
                    edgecolor="#3DBDB8",
                    linewidth=1.8,
                )
            )
    else:
        _ax.set_title("No ROIs drawn — falling back to FOV_ROI_table")
    _fig.tight_layout()

    mo.vstack(
        [
            mo.md(
                "### Let's build a custom ROI table \n"
                "Brush a rectangle on the image, then click **Add ROI** to "
                "store it. Repeat to build a custom ROI table; **Reset** clears "
                "the list. With no ROIs drawn, the iterator falls back to "
                "`FOV_ROI_table` so downstream cells still run."
            ),
            iter_roi_chart,
            mo.hstack([iter_add_btn, iter_reset_btn], justify="start"),
            _fig,
        ]
    )
    return (iter_roi_table,)


@app.cell
def _(iter_roi_table):
    iter_roi_table.rois()
    return


@app.cell
def _(image, iter_roi_table, ome_zarr):
    from ngio.experimental.iterators import SegmentationIterator

    nuc_label = ome_zarr.derive_label("nuclei_seg", overwrite=True)

    seg_iterator = (
        SegmentationIterator(
            input_image=image,
            output_label=nuc_label,
            channel_selection="DAPI",
            axes_order=["y", "x"],
        )
        .product(iter_roi_table)
        .by_yx()
    )
    # seg_iterator.require_no_regions_overlap()
    return SegmentationIterator, nuc_label, seg_iterator


@app.cell(hide_code=True)
def _(seg_iterator):
    seg_iterator.rois
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Naive run — let labels collide

    We hand the `basic_segmentation` function straight to
    `seg_iterator.map_as_numpy(...)`. Each patch is segmented independently
    and written back to `nuclei_seg`.

    Every patch therefore reuses the same IDs, so the
    global `nuclei_seg` would likely need a relabeling.
    """)
    return


@app.cell
def _(basic_segmentation, ome_zarr, plot_image, seg_iterator):
    seg_iterator.map_as_numpy(basic_segmentation)

    plot_image(
        ome_zarr,
        label="nuclei_seg",
        title="Naive segmentation — labels collide across patches",
        axes_order="yx",
        z=0,
    )
    return


@app.cell(hide_code=True)
def _(iter_t_run_graph, mo):
    mo.md(rf"""
    ### 3.3 Unique labels via an output transform

    `SegmentationIterator` accepts a list of `output_transforms` that run on
    every patch *before* it is written to disk. 

    {iter_t_run_graph}

    A transform is any object matching ngio's `TransformProtocol`. For a numpy `map_as_numpy` run, only
    `set_as_numpy_transform(array, slicing_ops, axes_ops)` needs to be
    implemented; the other protocol methods (`get_as_numpy_transform`,
    `*_as_dask_transform`) are only consulted on read paths or in dask runs.
    """)
    return


@app.cell
def _(
    SegmentationIterator,
    basic_segmentation,
    image,
    iter_roi_table,
    np,
    nuc_label,
    ome_zarr,
    plot_image,
):
    # `UniqueLabelOffset` keeps a running `max_label` across calls and shifts
    # each patch's labels above the previous high-water mark — turning the
    # per-patch IDs into globally unique ones.

    class UniqueLabelOffset:
        """Shift every patch's labels above the running max so IDs stay unique."""

        def __init__(self):
            self.max_label = 0

        def set_as_numpy_transform(self, array, slicing_ops, axes_ops):
            mask = array > 0
            array = np.where(mask, array + self.max_label, 0)
            if mask.any():
                self.max_label = int(array.max())
            return array

    naive_unique_count = len(np.unique(nuc_label.get_as_numpy(axes_order=["y", "x"], z=0)))

    nuc_label_unique = ome_zarr.derive_label("nuclei_seg_unique", overwrite=True)

    seg_iterator_unique = (
        SegmentationIterator(
            input_image=image,
            output_label=nuc_label_unique,
            channel_selection="DAPI",
            axes_order=["y", "x"],
            output_transforms=[UniqueLabelOffset()],
        )
        .product(iter_roi_table)
        .by_yx()
    )

    seg_iterator_unique.map_as_numpy(basic_segmentation)

    unique_label_count = len(np.unique(nuc_label_unique.get_as_numpy(axes_order=["y", "x"], z=0)))

    plot_image(
        ome_zarr,
        label="nuclei_seg_unique",
        title="Unique labels via output transform",
        axes_order="yx",
    )
    return naive_unique_count, unique_label_count


@app.cell(hide_code=True)
def _(mo, naive_unique_count, unique_label_count):
    mo.md(f"""
    **Distinct label IDs across all patches**

    | Run | Unique labels |
    |---|---:|
    | Naive `map_as_numpy` | `{naive_unique_count}` |
    | With `UniqueLabelOffset` | `{unique_label_count}` |
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3.4 Stateful iteration — `iter_as_numpy`

    `map_as_numpy` is the right call when each patch is independent. When
    you need state across patches — a running counter, a cross-patch
    statistic, an early-exit condition — switch to `iter_as_numpy`, which
    yields a `(patch, writer)` pair per ROI and lets you call the writer
    yourself.

    The example below reproduces §3.3's "globally unique labels" result
    *without* using a transform: the running `max_label` lives in the loop
    body. Two ways to solve the same problem — pick whichever fits the
    surrounding code best.
    """)
    return


@app.cell
def _(
    SegmentationIterator,
    basic_segmentation,
    image,
    iter_roi_table,
    np,
    ome_zarr,
    plot_image,
):
    nuc_label_loop = ome_zarr.derive_label("nuclei_seg_loop", overwrite=True)

    seg_iterator_loop = (
        SegmentationIterator(
            input_image=image,
            output_label=nuc_label_loop,
            channel_selection="DAPI",
            axes_order=["y", "x"],
        )
        .product(iter_roi_table)
        .by_yx()
    )

    max_label = 0
    for patch, writer in seg_iterator_loop.iter_as_numpy():
        seg = basic_segmentation(patch)
        mask = seg > 0
        seg = np.where(mask, seg + max_label, 0).astype(seg.dtype)
        if mask.any():
            max_label = int(seg.max())
        writer(patch=seg)

    plot_image(
        ome_zarr,
        label="nuclei_seg_loop",
        title="Stateful iter_as_numpy — running max_label in the loop",
        axes_order="yx",
    )
    return


if __name__ == "__main__":
    app.run()

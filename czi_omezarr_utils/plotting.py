# -*- coding: utf-8 -*-
"""
czi_omezarr_utils.plotting
===========================
Visualization utilities for well-plate heatmaps.
"""

from typing import Dict
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def create_well_plate_heatmap(
    results: Dict[str, float],
    num_rows: int = 8,
    num_cols: int = 12,
    title: str = "Well Plate Heatmap",
    parameter: str = "Objects",
    cmap: str = "viridis",
    figsize: tuple = (12, 6),
    annot: bool = True,
    fmt: str = ".0f",
) -> plt.Figure:
    """Create a heatmap visualization of well plate data.

    Args:
        results: Dictionary with well positions as keys (format: "row/col", e.g., "B/4")
            and numeric values.
        num_rows: Number of rows in the well plate (default: 8).
        num_cols: Number of columns in the well plate (default: 12).
        title: Heatmap title (default: "Well Plate Heatmap").
        parameter: Colorbar label (default: "Objects").
        cmap: Matplotlib/seaborn colormap name (default: "viridis").
        figsize: Figure size (width, height) in inches (default: (12, 6)).
        annot: Show values inside cells (default: True).
        fmt: String format for annotations (default: ".0f").

    Returns:
        Matplotlib Figure containing the heatmap.

    Examples:
        >>> results = {"A/1": 100.5, "A/2": 120.3, "B/1": 95.7}
        >>> fig = create_well_plate_heatmap(results, num_rows=8, num_cols=12)
        >>> plt.show()
    """
    rows_labels = [chr(65 + i) for i in range(num_rows)]
    cols_labels = list(range(1, num_cols + 1))

    heatmap_data = np.full((num_rows, num_cols), np.nan)

    for well_key, intensity in results.items():
        row_name, col_name = well_key.split("/")
        row_idx = rows_labels.index(row_name)
        col_idx = cols_labels.index(int(col_name))
        heatmap_data[row_idx, col_idx] = intensity

    df_heatmap = pd.DataFrame(heatmap_data, index=rows_labels, columns=cols_labels)

    fig = plt.figure(figsize=figsize)
    ax = sns.heatmap(
        df_heatmap,
        annot=annot,
        fmt=fmt,
        cmap=cmap,
        cbar_kws={"label": parameter},
        linewidths=0.5,
        linecolor="gray",
    )

    cbar = ax.collections[0].colorbar
    cbar.set_label(parameter, fontsize=12, fontweight="bold")
    plt.title(title, fontsize=14, fontweight="bold")
    plt.xlabel("Column", fontsize=12)
    plt.ylabel("Row", fontsize=12)
    plt.tight_layout()

    return fig

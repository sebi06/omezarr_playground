# -*- coding: utf-8 -*-
"""
czi_omezarr_utils.processing
=============================
Image processing utilities — ArrayProcessor class.

Moved from the standalone processing_tools.py module.
"""

from typing import Tuple, Optional, Literal
import numpy as np
import pandas as pd
import ngff_zarr as nz
from skimage.filters import threshold_triangle, threshold_otsu, median, gaussian
from skimage.measure import label, regionprops_table
from skimage.morphology import (
    remove_small_objects,
    remove_small_holes,
    disk,
    ball,
    white_tophat,
    black_tophat,
)
from skimage import segmentation
from skimage.color import label2rgb
from skimage.util import invert
import logging

logger = logging.getLogger(__name__)


class ArrayProcessor:
    """Process 2D arrays with filtering, thresholding, and object counting.

    Attributes:
        array: The 2D NumPy array being processed.
    """

    def __init__(self, array: np.ndarray) -> None:
        if isinstance(array, np.ndarray) and len(array.shape) == 2:
            self.array = array
        else:
            raise TypeError("Input should be a 2D array")

    def apply_gaussian_filter(self, sigma: int) -> np.ndarray:
        """Apply Gaussian filter to the array.

        Args:
            sigma: Sigma value for the Gaussian kernel (must be > 1).

        Returns:
            Filtered array with the same dtype as input.

        Raises:
            ValueError: If sigma is not a valid integer > 1.
        """
        if isinstance(sigma, int) and sigma > 1:
            return gaussian(self.array, sigma=sigma, preserve_range=True, mode="nearest").astype(self.array.dtype)
        raise ValueError("Sigma parameter is invalid.")

    def apply_median_filter(self, filter_size: int) -> np.ndarray:
        """Apply median filter to the array.

        Args:
            filter_size: Radius of the disk-shaped footprint.

        Returns:
            Filtered array with the same dtype as input.

        Raises:
            ValueError: If filter_size is not an integer.
        """
        if isinstance(filter_size, int):
            return median(self.array, footprint=disk(filter_size)).astype(self.array.dtype)
        raise ValueError("Filter Size parameter is invalid.")

    def apply_triangle_threshold(self) -> np.ndarray:
        """Apply triangle threshold to the array.

        Returns:
            Boolean array (array >= threshold).
        """
        thresh = threshold_triangle(self.array)
        return self.array >= thresh

    def apply_otsu_threshold(self) -> np.ndarray:
        """Apply Otsu threshold to the array.

        Returns:
            Boolean array (array >= threshold).
        """
        thresh = threshold_otsu(self.array)
        return self.array >= thresh

    def apply_threshold(self, value: int, invert_result: bool = False) -> np.ndarray:
        """Apply a fixed threshold to the array.

        Args:
            value: Threshold value (must be >= 0).
            invert_result: If True, invert the thresholded result.

        Returns:
            Thresholded (and optionally inverted) array.

        Raises:
            ValueError: If threshold parameters are invalid.
        """
        if isinstance(value, int) and value >= 0 and isinstance(invert_result, bool):
            self.array = self.array >= value
            if invert_result:
                self.array = invert(self.array)
            return self.array
        raise ValueError("Threshold parameters are invalid.")

    def label_objects(
        self,
        min_size: int = 10,
        max_size: int = 100_000_000,
        fill_holes: bool = True,
        max_holesize: int = 1,
        label_rgb: bool = True,
        orig_image: Optional[np.ndarray] = None,
        bg_label: int = 0,
        measure_params: bool = False,
        measure_properties: Optional[Tuple[str, ...]] = (
            "label",
            "area",
            "centroid",
            "bbox",
        ),
    ) -> Tuple[np.ndarray, int, Optional[pd.DataFrame]]:
        """Label objects in the thresholded array and optionally measure properties.

        Args:
            min_size: Minimum object size in pixels (default: 10).
            max_size: Maximum object size in pixels (default: 100 000 000).
            fill_holes: Fill small holes before labelling (default: True).
            max_holesize: Maximum hole size to fill (default: 1).
            label_rgb: Generate an RGB-labelled image overlay (default: True).
            orig_image: Original image for RGB overlay (default: None).
            bg_label: Background label value (default: 0).
            measure_params: Run regionprops measurement (default: False).
            measure_properties: Property names for regionprops (default: label/area/centroid/bbox).

        Returns:
            Tuple of (labelled_array, object_count, props_dataframe_or_None).

        Raises:
            ValueError: If parameters are invalid.
        """
        if not (isinstance(min_size, int) and min_size >= 1 and max_holesize >= 1 and isinstance(fill_holes, bool)):
            raise ValueError("Parameters are invalid.")

        if not np.issubdtype(self.array.dtype, bool):
            self.array = remove_small_holes(self.array.astype(bool), max_size=max_holesize, connectivity=1)
        else:
            self.array = remove_small_holes(self.array, max_size=max_holesize, connectivity=1)

        if not np.issubdtype(self.array.dtype, bool):
            self.array = remove_small_objects(self.array.astype(bool), max_size=min_size)
        else:
            self.array = remove_small_objects(self.array, max_size=min_size)

        self.array = segmentation.clear_border(self.array, bgval=bg_label)
        self.array, num_label = label(self.array, background=bg_label, return_num=True, connectivity=2)

        props: Optional[pd.DataFrame] = None
        if measure_params and measure_properties is not None:
            if orig_image is None:
                props = pd.DataFrame(
                    regionprops_table(self.array.astype(np.uint16), properties=measure_properties)
                ).set_index("label")
            else:
                props = pd.DataFrame(
                    regionprops_table(
                        self.array.astype(np.uint16),
                        intensity_image=orig_image,
                        properties=measure_properties,
                    )
                ).set_index("label")
            props = props[(props["area"] >= min_size) & (props["area"] <= max_size)]

        if label_rgb:
            if orig_image is None:
                self.array = label2rgb(self.array, image=None, bg_label=bg_label)
            else:
                self.array = label2rgb(self.array, image=orig_image, bg_label=bg_label)

        return self.array, num_label, props

    @staticmethod
    def subtract_background(
        image: np.ndarray,
        elem: Literal["disk", "ball"],
        radius: int = 50,
        light_bg: bool = False,
    ) -> np.ndarray:
        """Subtract background using morphological top-hat filtering.

        Args:
            image: 2D grayscale image.
            elem: Structuring element shape, either "disk" or "ball".
            radius: Radius of the structuring element (must be > 0).
            light_bg: If True, use black top-hat (light background); otherwise white top-hat.

        Returns:
            Background-subtracted image.

        Raises:
            ValueError: If parameters are invalid.
        """
        if not (isinstance(radius, int) and elem in ("disk", "ball") and radius > 0):
            raise ValueError("Parameters are invalid.")

        str_el = disk(radius) if elem == "disk" else ball(radius)
        return black_tophat(image, str_el) if light_bg else white_tophat(image, str_el)


def process_hcs_omezarr(
    hcs_omezarr_path: str,
    channel2analyze: int = 0,
    measure_properties: Tuple[str, ...] = ("label", "area", "centroid", "bbox"),
) -> dict:
    """Process an HCS OME-ZARR file to count objects per well.

    Iterates over every well and field in the plate, applies Otsu thresholding
    followed by connected-component labelling, and returns the total object count
    per well. Currently only 2D images (squeezed from the channel dimension) are
    supported.

    Args:
        hcs_omezarr_path: Path to the HCS OME-ZARR file or directory.
        channel2analyze: Index of the channel to analyse (default: 0).
        measure_properties: regionprops properties to measure (default: label/area/centroid/bbox).

    Returns:
        Dictionary mapping well path strings (e.g. ``"B/4"``) to total object counts.

    Raises:
        Exception: Re-raises any validation error from ``nz.from_hcs_zarr``.
    """
    try:
        logger.info("Validating HCS-ZARR file against schema...")
        hcs_plate = nz.from_hcs_zarr(hcs_omezarr_path, validate=True)
        logger.info("Validation successful.")
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise

    results_obj: dict = {}
    results_mean: dict = {}

    logger.info(f"Number of wells in metadata: {len(hcs_plate.metadata.wells)}")
    logger.info(f"Wells in metadata: {[w.path for w in hcs_plate.metadata.wells]}")

    for well_meta in hcs_plate.metadata.wells:
        row, col = well_meta.path.split("/")
        logger.info(f"\nProcessing well: {well_meta.path} (Row: {row}, Column: {col})")

        well = hcs_plate.get_well(row, col)

        if not well:
            logger.warning(f"  Well {well_meta.path} not found in plate, skipping")
            continue

        if not well.images or len(well.images) == 0:
            logger.warning(f"  Well {well_meta.path} has no images, skipping")
            continue

        field_intensities: list = []
        field_num_objects: list = []

        logger.info(f"  Found {len(well.images)} field(s) in well {well_meta.path}")

        for field_idx in range(len(well.images)):
            image = well.get_image(field_idx)

            if image:
                data = image.images[0].data.compute()
                logger.info(f"  Processing field {field_idx}: shape={data.shape}, dtype={data.dtype}")

                ap = ArrayProcessor(np.squeeze(data[:, channel2analyze, ...]))
                pro2d = ap.apply_otsu_threshold()
                ap = ArrayProcessor(pro2d)
                pro2d, num_objects, _props = ap.label_objects(
                    min_size=100,
                    label_rgb=False,
                    orig_image=None,
                    bg_label=0,
                    measure_params=True,
                    measure_properties=measure_properties,
                )

                field_num_objects.append(int(num_objects))
                field_intensities.append(float(np.mean(data)))

        results_mean[f"{row}/{col}"] = float(np.mean(field_intensities)) if field_intensities else 0.0
        results_obj[f"{row}/{col}"] = int(np.sum(field_num_objects))

    logger.info(f"Total wells processed: {len(results_mean)}")

    return results_obj

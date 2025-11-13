# -*- coding: utf-8 -*-

#################################################################
# File        : processing_tools.py
# Author      : SRh
# Institution : Carl Zeiss Microscopy GmbH
#
#
# Copyright(c) 2025 Carl Zeiss AG, Germany. All Rights Reserved.
#
# Permission is granted to use, modify and distribute this code,
# as long as this copyright notice remains part of the code.
#################################################################

from typing import Tuple, Optional, List, Literal, Union
from typing_extensions import Annotated
from pydantic import Field, validate_arguments

# from pydantic.error_wrappers import ValidationError
from skimage.filters import threshold_triangle, median, gaussian
from skimage.measure import label, regionprops_table, find_contours
from skimage.morphology import remove_small_objects, disk, ball, remove_small_holes
from skimage.morphology import white_tophat, black_tophat
from skimage import measure, segmentation
from skimage.filters import threshold_otsu
from skimage.color import label2rgb
from skimage.util import invert
import numpy as np
import pandas as pd
import os
from czitools.metadata_tools import czi_metadata as czimd
from czitools.utils import misc
from pylibCZIrw import czi as pyczi
from tqdm.contrib.itertools import product


class ArrayProcessor:
    """
    A class used to process 2D arrays with various methods including filtering, thresholding, and object counting.

    Attributes
    ----------
    array : np.ndarray
        a 2D array to be processed

    Methods
    -------
    apply_median_filter(footprint: np.ndarray) -> np.ndarray:
        Applies a median filter to the array with the given footprint.

    apply_gaussian_filter(sigma: int) -> np.ndarray:
        Applies a gaussian filter to the array with the given sigma.

    apply_triangle_threshold() -> np.ndarray:
        Applies a triangle threshold to the array.

    apply_threshold(value: int, invert_result: bool = False) -> np.ndarray:
        Applies a threshold to the array with the given value and optionally inverts the result.

    count_objects(min_size: int = 10, label_rgb: bool = True, bg_label: int = 0) -> Tuple[np.ndarray, int]:
        Counts the objects in the array that are larger than the given size and optionally labels them in RGB.
    """

    def __init__(self, array):
        """
        Parameters
        ----------
        array : np.ndarray
            a 2D array to be processed
        """
        if isinstance(array, np.ndarray) and len(array.shape) == 2:
            self.array = array
        else:
            raise TypeError("Input should be a 2D array")

    def apply_gaussian_filter(self, sigma: int) -> np.ndarray:
        """
        Applies gaussian filter to the input array with given sigma.

        Parameters:
        sigma (int): Sigma value for gaussian filter

        Returns:
        np.ndarray: Gaussian filtered numpy array

        Raises:
        ValueError: If sigma parameter is invalid.
        """
        if isinstance(sigma, int) and sigma > 1:
            return gaussian(self.array, sigma=sigma, preserve_range=True, mode="nearest").astype(self.array.dtype)
        else:
            raise ValueError("Sigma parameter is invalid.")

    def apply_median_filter(self, filter_size: int) -> np.ndarray:
        """
        Applies median filter to the input array with given footprint.

        Parameters:
        filter_size (np.ndarray): Size of the Footprint for the median filter

        Returns:
        np.ndarray: Median filtered numpy array

        Raises:
        ValueError: If Footprint parameter is invalid.
        """
        if isinstance(filter_size, int):
            return median(self.array, footprint=disk(filter_size)).astype(self.array.dtype)
        else:
            raise ValueError("Filter Size parameter is invalid.")

    def apply_triangle_threshold(self) -> np.ndarray:
        """
        Applies triangle threshold to the input array.

        Returns:
        np.ndarray: Thresholded numpy array
        """

        # apply the threshold
        thresh = threshold_triangle(self.array)

        return self.array >= thresh

    def apply_otsu_threshold(self) -> np.ndarray:
        """
        Applies Otsu threshold to the input array.

        Returns:
        np.ndarray: Thresholded numpy array
        """

        # apply the threshold
        thresh = threshold_otsu(self.array)

        return self.array >= thresh

    def apply_threshold(self, value: int, invert_result: bool = False) -> np.ndarray:
        """
        Applies threshold to the input array.

        Parameters:
        value (int): Threshold value for the input array
        invert_result (bool): Invert the thresholded result (default False)

        Returns:
        np.ndarray: Thresholded numpy array

        Raises:
        ValueError: If threshold parameters are invalid.
        """
        if isinstance(value, int) and value >= 0 and (isinstance(invert_result, bool)):

            # apply the threshold
            self.array = self.array >= value

            if invert_result:
                self.array = invert(self.array)

            return self.array
        else:
            raise ValueError("Threshold parameters are invalid.")

    def label_objects(
        self,
        min_size: int = 10,
        max_size: int = 100000000,
        fill_holes: bool = True,
        max_holesize: int = 1,
        label_rgb: bool = True,
        orig_image: Optional[np.ndarray] = None,
        bg_label: int = 0,
        measure_params: bool = False,
        measure_properties: Optional[Tuple[str]] = (
            "label",
            "area",
            "centroid",
            "bbox",
        ),
    ) -> Tuple[np.ndarray, int, pd.DataFrame]:
        """
        Counts objects in the input array and returns labeled image with the count.

        Parameters:
        min_size (int): Minimum size of the objects (default 10)
        max_size (int): Maximum size of the objects (default 100000000)
        fill_holes (bool): Option to fill holes (default True)
        max_holesize (int): Maximum size of holes to be filled (default 1)
        label_rgb (bool): Generate labeled RGB image (default True)
        orig_image (np.ndarray): original image data for overlay (default None)
        bg_label (int): Background label value (default 0)
        measure (bool): Use scikit-image to measure parameters (default False)
        measure_properties (tuple): Parameters to be measured (default ("label", "area", "centroid", "bbox"))

        Returns:
        Tuple[np.ndarray, int]: Labeled image and count of objects

        Raises:
        ValueError: If min_size parameter is invalid.
        """
        if isinstance(min_size, int) and min_size >= 1 and max_holesize >= 1 and isinstance(fill_holes, bool):

            # Remove contiguous holes smaller than the specified size
            if not np.issubdtype(self.array.dtype, bool):
                self.array = remove_small_holes(self.array.astype(bool), area_threshold=max_holesize, connectivity=1)
            else:
                self.array = remove_small_holes(self.array, area_threshold=max_holesize, connectivity=1)

            # remove small objects
            if not np.issubdtype(self.array.dtype, bool):
                self.array = remove_small_objects(self.array.astype(bool), min_size)
            else:
                self.array = remove_small_objects(self.array, min_size)

            # clear the border
            self.array = segmentation.clear_border(self.array, bgval=bg_label)

            # label the particles
            self.array, num_label = label(self.array, background=bg_label, return_num=True, connectivity=2)

            # measure the specified parameters store in dataframe
            props = None

            if measure_params:
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

                    # filter objects by size
                props = props[(props["area"] >= min_size) & (props["area"] <= max_size)]

            # apply RGB labels
            if label_rgb:
                if orig_image is None:
                    self.array = label2rgb(self.array, image=None, bg_label=bg_label)
                else:
                    self.array = label2rgb(self.array, image=orig_image, bg_label=bg_label)

            return self.array, num_label, props
        else:
            raise ValueError("Parameters are invalid.")

    def subtract_background(
        image: np.ndarray,
        elem: Literal["disk", "ball"],
        radius: int = 50,
        light_bg: bool = False,
    ) -> np.ndarray:
        """Slightly adapted from: https://forum.image.sc/t/background-subtraction-in-scikit-image/39118/4

        Subtracts the background of a given image using a morphological operation.

        Parameters
        ----------
        image : numpy.ndarray
            The image to subtract the background from. Should be a two-dimensional grayscale image.
        elem : str, optional
            The shape of the structuring element to use for the morphological operation, either 'disk' or 'ball'.
            Defaults to 'disk'.
        radius : int, optional
            The radius of the structuring element to use. Should be a positive integer. Defaults to 50.
        light_bg : bool, optional
            If True, assume that the background is lighter than the foreground,
            otherwise assume that the background is darker than the foreground.
            Defaults to False.

        Returns
        -------
        numpy.ndarray
            The resulting image with the background subtracted.

        Raises
        ------
        ValueError
            If the `radius` parameter is not a positive integer, or if the `elem` parameter
            is not 'disk' or 'ball'.

        """

        if isinstance(radius, int) and elem in ["disk", "ball"] and radius > 0:
            # use 'ball' here to get a slightly smoother result at the cost of increased computing time
            if elem == "disk":
                str_el = disk(radius)
            if elem == "ball":
                str_el = ball(radius)

            if light_bg:
                img_subtracted = black_tophat(image, str_el)
            if not light_bg:
                img_subtracted = white_tophat(image, str_el)

            return img_subtracted

        else:
            raise ValueError("Parameters is invalid.")

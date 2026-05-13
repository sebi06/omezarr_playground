# -*- coding: utf-8 -*-
"""
czi_omezarr_utils.logging_utils
================================
Logging configuration helper and the omezarr_package enum.
"""

from pathlib import Path
from typing import Optional, Union
from enum import Enum, unique
import logging


@unique
class omezarr_package(Enum):
    OME_ZARR = 1
    NGFF_ZARR = 2


def setup_logging(
    log_file_path: Optional[Union[str, Path]] = None,
    log_level: int = logging.INFO,
    force_reconfigure: bool = False,
) -> logging.Logger:
    """Set up logging configuration consistently across all functions.

    Args:
        log_file_path: Path to log file. If None, only a console handler is added.
        log_level: Logging level (default: INFO).
        force_reconfigure: If True, reconfigure even if logging is already set up.

    Returns:
        The configured root logger.
    """
    root_logger = logging.getLogger()

    has_file_handler = any(isinstance(h, logging.FileHandler) for h in root_logger.handlers)
    has_console_handler = any(
        isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in root_logger.handlers
    )

    if has_file_handler and has_console_handler and not force_reconfigure:
        return root_logger

    root_logger.setLevel(log_level)

    if force_reconfigure or not (has_file_handler and has_console_handler):
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        if log_file_path:
            file_handler = logging.FileHandler(str(log_file_path))
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

    return root_logger

"""
Dynamically loads and registers all processor modules from the sync_processors package.
Used during Lambda startup to ensure all sync_processors are available.
Includes full exception traceback for easier debugging.
"""

import importlib
import pkgutil
import traceback

import sync_processors as processors_pkg
from helpers.logger_helper import LoggerHelper

logger = LoggerHelper(__name__).get_logger()


def load_all_processors():
    logger.info("Starting to load all processor modules")
    for _, module_name, _ in pkgutil.iter_modules(processors_pkg.__path__):
        full_module_name = f"{processors_pkg.__name__}.{module_name}"
        try:
            logger.info(f"Importing processor module: {full_module_name}")
            importlib.import_module(full_module_name)
            logger.info(f"Successfully imported processor module: {full_module_name}")
        except Exception as e:
            logger.error(f"Failed to import processor module: {full_module_name} | Error: {str(e)}")
            logger.error("Traceback:\n%s", traceback.format_exc())

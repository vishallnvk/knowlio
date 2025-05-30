"""
Base class for all sync_processors.
Handles dispatching actions to appropriate processor methods using an action map.
"""

import traceback
from typing import Callable, Dict

from helpers.logger_helper import LoggerHelper

logger = LoggerHelper(__name__).get_logger()


class BaseProcessor:
    def __init__(self, action_map: Dict[str, Callable]):
        self.action_map = action_map
        logger.debug("Initialized BaseProcessor with actions: %s", list(action_map.keys()))

    def process(self, payload: Dict) -> Dict:
        logger.info("Processing payload: %s", payload)

        try:
            action = payload.get("action")
            if not action:
                logger.error("Missing 'action' in payload")
                raise ValueError("Missing 'action' in payload")

            if action not in self.action_map:
                logger.error("Unsupported action: %s", action)
                raise ValueError(f"Unsupported action: {action}")

            logger.debug("Dispatching action: %s", action)
            return self.action_map[action](payload)

        except Exception as e:
            logger.error("Error while processing action: %s", str(e))
            logger.error("Traceback:\n%s", traceback.format_exc())
            raise

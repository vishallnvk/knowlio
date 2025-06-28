"""
Base class for all sync_processors.
Handles dispatching actions to appropriate processor methods using an action map.
"""

import traceback
from typing import Callable, Dict

from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.auth_context import AuthContext

logger = LoggerHelper(__name__).get_logger()


class BaseProcessor:
    def __init__(self, action_map: Dict[str, Callable]):
        self.action_map = action_map
        logger.debug("Initialized BaseProcessor with actions: %s", list(action_map.keys()))

    def process(self, action: str, payload: Dict) -> Dict:
        logger.info("Processing action: %s, payload: %s", action, payload)

        try:
            if action not in self.action_map:
                logger.error("Unsupported action: %s", action)
                raise ValueError(f"Unsupported action: {action}")

            # Make a copy of the payload to avoid modifying the original
            payload_with_action = payload.copy() if payload else {}
            
            # Add the action name so methods can know which action was called
            payload_with_action["__action__"] = action
            
            # Extract and standardize auth context in the payload
            auth_context = AuthContext.from_payload(payload)
                
            # Add AuthContext properly to payload
            payload_with_action["auth_context"] = auth_context

            logger.debug("Dispatching action: %s with auth context for user: %s", 
                       action, auth_context.user_id or "unauthenticated")
            
            return self.action_map[action](payload_with_action)

        except Exception as e:
            logger.error("Error while processing action: %s", str(e))
            logger.error("Traceback:\n%s", traceback.format_exc())
            raise

from typing import Dict

from helpers.logger_helper import LoggerHelper
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor

logger = LoggerHelper(__name__).get_logger()


@ProcessorRegistry.register("user")
class UserProcessor(BaseProcessor):
    def __init__(self):
        rds_action_map = {"describe_db": self.describe_db}
        super().__init__(rds_action_map)

    def describe_db(self, payload: Dict) -> Dict:
        logger.info("Processing 'describe_db' action with payload: %s", payload)
        return {"message": "Successfully processed 'describe_db' action"}

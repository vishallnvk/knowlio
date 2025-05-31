from typing import Dict

from helpers.common_helper.common_helper import require_keys
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.app_logic_helpers.content_helper import ContentHelper
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor

logger = LoggerHelper(__name__).get_logger()

@ProcessorRegistry.register("content")
class ContentProcessor(BaseProcessor):
    def __init__(self):
        self.helper = ContentHelper()
        super().__init__({
            "upload_content_metadata": self._upload_content_metadata,
            "upload_content_blob": self._upload_content_blob,
            "get_content_details": self._get_content_details,
            "update_content_metadata": self._update_content_metadata,
            "list_content_by_publisher": self._list_content_by_publisher,
            "archive_content": self._archive_content,
        })

    def _upload_content_metadata(self, payload: Dict) -> Dict:
        require_keys(payload, ["publisher_id", "title", "type"])
        return self.helper.upload_content_metadata(payload)

    def _upload_content_blob(self, payload: Dict) -> Dict:
        require_keys(payload, ["content_id", "s3_uri"])
        return self.helper.upload_content_blob(payload["content_id"], payload["s3_uri"])

    def _get_content_details(self, payload: Dict) -> Dict:
        require_keys(payload, ["content_id"])
        return self.helper.get_content_details(payload["content_id"])

    def _update_content_metadata(self, payload: Dict) -> Dict:
        require_keys(payload, ["content_id", "updates"])
        return self.helper.update_content_metadata(payload["content_id"], payload["updates"])

    def _list_content_by_publisher(self, payload: Dict) -> Dict:
        require_keys(payload, ["publisher_id"])
        return {
            "contents": self.helper.list_content_by_publisher(
                publisher_id=payload["publisher_id"]
            )
        }

    def _archive_content(self, payload: Dict) -> Dict:
        require_keys(payload, ["content_id"])
        return self.helper.archive_content(payload["content_id"])

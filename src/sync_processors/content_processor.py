from typing import Dict, List

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
            "search_content": self._search_content,
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
        
        # Extract pagination parameters if provided
        limit = payload.get("limit")
        pagination_token = payload.get("pagination_token")
        
        result = self.helper.list_content_by_publisher(
            publisher_id=payload["publisher_id"],
            limit=limit,
            pagination_token=pagination_token
        )
        
        # Convert result structure to standardized format
        response = {
            "contents": result.get("items", []),
            "count": result.get("count", 0)
        }
        
        # Add pagination details if available
        if "pagination_token" in result:
            response["pagination"] = {
                "next_token": result["pagination_token"],
                "has_more": result.get("has_more", False)
            }
            
        return response

    def _archive_content(self, payload: Dict) -> Dict:
        require_keys(payload, ["content_id"])
        return self.helper.archive_content(payload["content_id"])
        
    def _search_content(self, payload: Dict) -> Dict:
        """
        Search for content based on flexible parameters with pagination support.
        All search parameters are optional filters.
        
        Args:
            payload: Dict containing search parameters which can include:
                - publisher_id: Filter by publisher
                - type: Content type (book, text, video, audio)
                - title: Full or partial title to search for
                - tags: List of tags to filter by
                - status: Content status (DRAFT, ACTIVE, ARCHIVED)
                - Any other parameter specific to content types (e.g., author for books)
                - limit: Maximum number of results to return
                - pagination_token: Token for retrieving the next page of results
                
        Returns:
            Dict containing search results and pagination details
        """
        # Extract pagination parameters
        limit = payload.pop("limit", None)
        pagination_token = payload.pop("pagination_token", None)
        
        # Execute search with remaining parameters as filters
        search_result = self.helper.search_content(
            search_params=payload,
            limit=limit,
            pagination_token=pagination_token
        )
        
        # Handle error case
        if "error" in search_result:
            return {"error": search_result["error"]}
        
        # Convert result structure to standardized format
        response = {
            "contents": search_result.get("items", []),
            "count": search_result.get("count", 0),
            "total_scanned": search_result.get("total_scanned", 0)
        }
        
        # Add pagination details if available
        if "pagination_token" in search_result:
            response["pagination"] = {
                "next_token": search_result["pagination_token"],
                "has_more": search_result.get("has_more", False)
            }
            
        return response

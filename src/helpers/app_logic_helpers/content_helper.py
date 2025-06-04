import uuid
from typing import Dict, List, Optional, Any, Union

from helpers.aws_service_helpers.dynamodb_helper import DynamoDBHelper
from helpers.common_helper.logger_helper import LoggerHelper
from models.content_model import ContentModel

logger = LoggerHelper(__name__).get_logger()

CONTENT_TABLE = "content"

class ContentHelper:
    def __init__(self):
        self.db = DynamoDBHelper(table_name=CONTENT_TABLE)

    def upload_content_metadata(self, content_data: Dict) -> Dict:
        content_id = str(uuid.uuid4())
        content_item = ContentModel(content_data).__dict__

        logger.info("Uploading content metadata: %s", content_item)
        self.db.put_item(content_item)
        return {"message": "Content metadata uploaded", "content_id": content_id}

    def upload_content_blob(self, content_id: str, file_key: str) -> Dict:
        logger.info("Attaching file key '%s' to content_id: %s", file_key, content_id)
        return self.db.update_item("content_id", content_id, {"file_key": file_key, "status": "ACTIVE"})

    def get_content_details(self, content_id: str) -> Optional[Dict]:
        logger.info("Fetching content details for content_id: %s", content_id)
        return self.db.get_item({"content_id": content_id})

    def update_content_metadata(self, content_id: str, updates: Dict) -> Dict:
        logger.info("Updating content metadata for content_id: %s with: %s", content_id, updates)
        return self.db.update_item("content_id", content_id, updates)

    def list_content_by_publisher(self, publisher_id: str, limit: int = None, 
                                 pagination_token: str = None) -> Dict:
        """
        List content by publisher with pagination support
        
        Args:
            publisher_id: The publisher ID to filter by
            limit: Optional maximum number of items to return
            pagination_token: Optional pagination token from previous query
            
        Returns:
            Dict containing items and pagination details
        """
        logger.info("Listing content for publisher_id: %s (limit: %s)", publisher_id, limit)
        
        # Convert pagination token from string to dict if provided
        last_evaluated_key = None
        if pagination_token:
            try:
                import json
                import base64
                decoded_token = base64.b64decode(pagination_token)
                last_evaluated_key = json.loads(decoded_token)
                logger.debug("Decoded pagination token: %s", last_evaluated_key)
            except Exception as e:
                logger.error("Failed to decode pagination token: %s", e)
                return {"error": "Invalid pagination token"}
        
        # Query with pagination
        result = self.db.query_items(
            key_name="publisher_id", 
            key_value=publisher_id,
            limit=limit,
            last_evaluated_key=last_evaluated_key
        )
        
        # Encode last_evaluated_key as pagination token if present
        if result.get("last_evaluated_key"):
            import json
            import base64
            token_bytes = json.dumps(result["last_evaluated_key"]).encode("utf-8")
            result["pagination_token"] = base64.b64encode(token_bytes).decode("utf-8")
            del result["last_evaluated_key"]  # Remove raw key from response
            
        return result

    def archive_content(self, content_id: str) -> Dict:
        logger.info("Archiving content_id: %s", content_id)
        return self.db.update_item("content_id", content_id, {"status": "ARCHIVED"})
        
    def search_content(self, search_params: Dict, limit: int = None, 
                      pagination_token: str = None) -> Dict:
        """
        Search content based on provided parameters with pagination support.
        Supports generic content fields and specific fields for different content types.
        
        Args:
            search_params: Dictionary of search parameters, which can include:
                - publisher_id: Filter by publisher 
                - type: Content type (book, text, video, audio)
                - title: Full or partial title match
                - tags: List of tags to filter by
                - status: Content status
                - Any other metadata field for specific content types
            limit: Optional maximum number of items to return
            pagination_token: Optional pagination token from previous query
                
        Returns:
            Dict containing matching content items and pagination details
        """
        logger.info("Searching content with parameters: %s (limit: %s)", search_params, limit)
        
        # Convert pagination token from string to dict if provided
        last_evaluated_key = None
        if pagination_token:
            try:
                import json
                import base64
                decoded_token = base64.b64decode(pagination_token)
                last_evaluated_key = json.loads(decoded_token)
                logger.debug("Decoded pagination token: %s", last_evaluated_key)
            except Exception as e:
                logger.error("Failed to decode pagination token: %s", e)
                return {"error": "Invalid pagination token"}
        
        # Start with all content or filter by publisher if provided
        if "publisher_id" in search_params:
            # If publisher_id is provided, use query which is more efficient
            publisher_id = search_params["publisher_id"]
            base_result = self.db.query_items(
                key_name="publisher_id", 
                key_value=publisher_id,
                limit=limit,
                last_evaluated_key=last_evaluated_key
            )
            base_items = base_result.get("items", [])
            logger.debug("Found %d items for publisher_id %s", len(base_items), publisher_id)
        else:
            # Otherwise scan all items (less efficient, but necessary for global search)
            base_result = self.db.scan_items(
                limit=limit,
                last_evaluated_key=last_evaluated_key
            )
            base_items = base_result.get("items", [])
            logger.debug("Scanned content, found %d items", len(base_items))
        
        # Apply filters based on provided search parameters
        filtered_results = []
        for item in base_items:
            if self._matches_search_criteria(item, search_params):
                filtered_results.append(item)
        
        # Prepare result with pagination
        result = {
            "items": filtered_results,
            "count": len(filtered_results),
            "total_scanned": base_result.get("count", 0),
            "has_more": base_result.get("has_more", False)
        }
        
        # Encode last_evaluated_key as pagination token if present
        if base_result.get("last_evaluated_key"):
            import json
            import base64
            token_bytes = json.dumps(base_result["last_evaluated_key"]).encode("utf-8")
            result["pagination_token"] = base64.b64encode(token_bytes).decode("utf-8")
        
        logger.info("Search returned %d results", len(filtered_results))
        return result
    
    def _matches_search_criteria(self, item: Dict, search_params: Dict) -> bool:
        """
        Check if an item matches all search criteria.
        
        Args:
            item: Content item to check
            search_params: Search parameters to match against
            
        Returns:
            True if the item matches all criteria, False otherwise
        """
        # Type filter
        if "type" in search_params and item.get("type") != search_params["type"]:
            return False
            
        # Status filter
        if "status" in search_params and item.get("status") != search_params["status"]:
            return False
            
        # Title search (partial match)
        if "title" in search_params:
            search_title = search_params["title"].lower()
            item_title = item.get("title", "").lower()
            if search_title not in item_title:
                return False
                
        # Tags filter (any match)
        if "tags" in search_params:
            search_tags = [tag.lower() for tag in search_params["tags"]]
            item_tags = [tag.lower() for tag in item.get("tags", [])]
            if not any(tag in item_tags for tag in search_tags):
                return False
        
        # Handle metadata searches
        item_metadata = item.get("metadata", {})
        
        # Book-specific search parameters (when type is book)
        if item.get("type") == "book":
            # For books, check metadata fields
            for key, value in search_params.items():
                # Skip already processed standard fields
                if key in ["publisher_id", "type", "status", "title", "tags"]:
                    continue
                    
                # If the parameter matches a field in metadata, check it
                if key in item_metadata:
                    # Case-insensitive partial match for string values
                    if isinstance(item_metadata[key], str) and isinstance(value, str):
                        if value.lower() not in item_metadata[key].lower():
                            return False
                    # Exact match for other types
                    elif item_metadata[key] != value:
                        return False
        
        # For other content types, similar logic can be added when needed
        
        # If all filters passed, the item matches
        return True

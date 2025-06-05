import uuid
import json
import base64
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

import botocore.exceptions
from helpers.aws_service_helpers.dynamodb_helper import DynamoDBHelper
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.common_helper import Retry
from models.content_model import ContentModel

logger = LoggerHelper(__name__).get_logger()

CONTENT_TABLE = "content"

class ContentValidationError(Exception):
    """Exception raised for content data validation failures."""
    pass

class ContentHelper:
    def __init__(self):
        self.db = DynamoDBHelper(table_name=CONTENT_TABLE)

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def upload_content_metadata(self, content_data: Dict) -> Dict:
        """
        Upload content metadata with validation.
        
        Args:
            content_data: Content information including required fields
            
        Returns:
            Dict with success message and content_id
            
        Raises:
            ContentValidationError: If validation fails
        """
        try:
            # Create content model (validates type and other fields)
            content_model = ContentModel(content_data)
            content_item = content_model.__dict__
            content_id = content_item["content_id"]

            logger.info("Uploading content metadata: %s", content_item)
            self.db.put_item(content_item)
            return {"message": "Content metadata uploaded", "content_id": content_id}
        except ValueError as e:
            logger.error("Content validation error: %s", str(e))
            raise ContentValidationError(str(e))

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def upload_content_blob(self, content_id: str, file_key: str) -> Dict:
        """
        Attach a file key to content and activate it.
        
        Args:
            content_id: ID of the content to update
            file_key: S3 key for the uploaded file
            
        Returns:
            Updated content item
        """
        logger.info("Attaching file key '%s' to content_id: %s", file_key, content_id)
        
        # Set updated_at timestamp
        updates = {
            "file_key": file_key, 
            "status": "ACTIVE",
            "updated_at": datetime.utcnow().isoformat()
        }
        
        return self.db.update_item("content_id", content_id, updates)

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def get_content_details(self, content_id: str) -> Optional[Dict]:
        """
        Get content details by ID.
        
        Args:
            content_id: ID of the content to fetch
            
        Returns:
            Content details or None if not found
        """
        logger.info("Fetching content details for content_id: %s", content_id)
        return self.db.get_item({"content_id": content_id})

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def update_content_metadata(self, content_id: str, updates: Dict) -> Dict:
        """
        Update content metadata with validation.
        
        This is a generic update method that can update any field including nested metadata.
        
        Args:
            content_id: ID of the content to update
            updates: Dict of fields to update
            
        Returns:
            Updated content item
            
        Raises:
            ContentValidationError: If validation fails
        """
        logger.info("Updating content metadata for content_id: %s with: %s", content_id, updates)
        
        # Get current content to validate changes
        content = self.get_content_details(content_id)
        if not content:
            raise ContentValidationError(f"Content not found with ID: {content_id}")
        
        # Validate type if changing
        if "type" in updates:
            try:
                updates["type"] = ContentModel._validate_type(None, updates["type"])
            except ValueError as e:
                raise ContentValidationError(str(e))
        
        # Validate status if changing
        if "status" in updates and not ContentModel.validate_status(updates["status"]):
            valid_statuses = ", ".join(ContentModel.VALID_STATUSES)
            raise ContentValidationError(f"Invalid status: {updates['status']}. Valid statuses: {valid_statuses}")
            
        # Validate workflow statuses if changing
        for status_field in ["rag_status", "training_status", "licensing_status"]:
            if status_field in updates and not ContentModel.validate_workflow_status(updates[status_field]):
                valid_statuses = ", ".join(ContentModel.VALID_WORKFLOW_STATUSES)
                raise ContentValidationError(f"Invalid {status_field}: {updates[status_field]}. Valid values: {valid_statuses}")
        
        # Add updated_at timestamp
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        return self.db.update_item("content_id", content_id, updates)

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def update_content_attribute(self, content_id: str, attribute: str, value: Any) -> Dict:
        """
        Update a single attribute of content with validation.
        
        This is a generic method that can update any attribute including nested ones.
        
        Args:
            content_id: ID of the content to update
            attribute: Attribute name to update (can use dot notation for nested fields)
            value: New value for the attribute
            
        Returns:
            Updated content item
            
        Raises:
            ContentValidationError: If validation fails
        """
        logger.info("Updating attribute '%s' for content_id: %s", attribute, content_id)
        
        # For top-level attributes, use update_content_metadata
        if "." not in attribute:
            return self.update_content_metadata(content_id, {attribute: value})
            
        # For nested attributes, we need to get the current content first
        content = self.get_content_details(content_id)
        if not content:
            raise ContentValidationError(f"Content not found with ID: {content_id}")
            
        # Parse the attribute path
        parts = attribute.split(".")
        top_level = parts[0]
        
        # Currently only supports metadata.field notation
        if top_level != "metadata" or len(parts) != 2:
            raise ContentValidationError(f"Invalid attribute path: {attribute}. Only metadata.field notation is supported.")
            
        # Get the current metadata
        metadata = dict(content.get("metadata", {}))
        
        # Update the specific field
        metadata[parts[1]] = value
        
        # Update the entire metadata
        return self.update_content_metadata(content_id, {"metadata": metadata})

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
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
        last_evaluated_key = self._decode_pagination_token(pagination_token)
        
        # Query with pagination
        result = self.db.query_items(
            key_name="publisher_id", 
            key_value=publisher_id,
            limit=limit,
            last_evaluated_key=last_evaluated_key
        )
        
        # Apply standard pagination encoding
        return self._encode_pagination_result(result)

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def archive_content(self, content_id: str) -> Dict:
        """
        Archive content by setting its status to ARCHIVED.
        
        Args:
            content_id: ID of the content to archive
            
        Returns:
            Updated content item
        """
        logger.info("Archiving content_id: %s", content_id)
        return self.update_content_metadata(content_id, {"status": "ARCHIVED"})
        
    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def search_content(self, search_params: Dict, limit: int = None, 
                      pagination_token: str = None) -> Dict:
        """
        Search content based on provided parameters with pagination support.
        Supports generic content fields and specific fields for different content types.
        
        Args:
            search_params: Dictionary of search parameters, which can include:
                - publisher_id: Filter by publisher 
                - type: Content type (BOOK, VIDEO, AUDIO, DATASET, TEXT)
                - title: Full or partial title match
                - tags: List of tags to filter by
                - status: Content status (DRAFT, ACTIVE, ARCHIVED)
                - rag_status, training_status, licensing_status: Workflow statuses
                - Any metadata fields for type-specific attributes
            limit: Optional maximum number of items to return
            pagination_token: Optional pagination token from previous query
                
        Returns:
            Dict containing matching content items and pagination details
        """
        logger.info("Searching content with parameters: %s (limit: %s)", search_params, limit)
        
        # Make a copy of search params to avoid modifying the original
        search_params = search_params.copy()
        
        # Convert pagination token from string to dict if provided
        last_evaluated_key = self._decode_pagination_token(pagination_token)
        
        # Use the most efficient query method based on parameters
        base_result = self._get_base_query_result(search_params, limit, last_evaluated_key)
        
        # Apply filters based on provided search parameters
        filtered_items = []
        for item in base_result.get("items", []):
            if self._matches_search_criteria(item, search_params):
                filtered_items.append(item)
        
        # Prepare result with pagination
        result = {
            "items": filtered_items,
            "count": len(filtered_items),
            "total_scanned": base_result.get("count", 0),
            "has_more": base_result.get("has_more", False)
        }
        
        # Encode pagination token if present
        if base_result.get("last_evaluated_key"):
            result["last_evaluated_key"] = base_result["last_evaluated_key"]
        
        # Apply standard pagination encoding
        final_result = self._encode_pagination_result(result)
        
        logger.info("Search returned %d results", len(filtered_items))
        return final_result
        
    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def query_by_attribute(self, attribute: str, value: Any, limit: int = None,
                         pagination_token: str = None) -> Dict:
        """
        Query content by any attribute with pagination support.
        
        This is a generic method that can query by any top-level attribute
        that has a GSI, or fall back to scanning and filtering.
        
        Args:
            attribute: Attribute name to query by
            value: Value to match
            limit: Optional maximum number of items to return
            pagination_token: Optional pagination token from previous query
            
        Returns:
            Dict containing matching content items and pagination details
        """
        logger.info("Querying content by %s = %s (limit: %s)", attribute, value, limit)
        
        search_params = {attribute: value}
        return self.search_content(search_params, limit, pagination_token)

    def _get_base_query_result(self, search_params: Dict, limit: int = None, 
                              last_evaluated_key: Dict = None) -> Dict:
        """
        Get the base query result using the most efficient method based on parameters.
        
        Args:
            search_params: Search parameters to use
            limit: Optional maximum number of items to return
            last_evaluated_key: Optional key to start from for pagination
            
        Returns:
            Query result with items and pagination info
        """
        # Try to use GSIs for efficiency when possible
        indexable_fields = ["publisher_id", "type", "status"]
        
        for field in indexable_fields:
            if field in search_params:
                try:
                    # Try to use the field's GSI
                    result = self.db.query_items(
                        key_name=field,
                        key_value=search_params[field],
                        limit=limit,
                        last_evaluated_key=last_evaluated_key
                    )
                    # Remove the field from search_params to avoid double filtering
                    del search_params[field]
                    return result
                except Exception as e:
                    logger.warning("Failed to use index for %s: %s", field, e)
                    # Continue to the next field or fall back to scan
        
        # If no indexed field is available, fall back to scan
        return self.db.scan_items(
            limit=limit,
            last_evaluated_key=last_evaluated_key
        )
    
    def _matches_search_criteria(self, item: Dict, search_params: Dict) -> bool:
        """
        Check if an item matches all search criteria.
        
        Args:
            item: Content item to check
            search_params: Search parameters to match against
            
        Returns:
            True if the item matches all criteria, False otherwise
        """
        for key, value in search_params.items():
            # Handle nested attribute paths (e.g., metadata.field)
            if "." in key:
                parts = key.split(".")
                if len(parts) != 2 or parts[0] != "metadata":
                    # Currently only support metadata.field notation
                    continue
                    
                metadata = item.get("metadata", {})
                metadata_key = parts[1]
                
                # Skip if the metadata key doesn't exist
                if metadata_key not in metadata:
                    return False
                    
                # Compare the metadata value
                metadata_value = metadata[metadata_key]
                if not self._values_match(metadata_value, value):
                    return False
                    
            # Handle standard fields
            elif key in item:
                if not self._values_match(item[key], value):
                    return False
                    
            # Handle workflow status fields
            elif key in ["rag_status", "training_status", "licensing_status"] and key in item:
                if item[key] != value:
                    return False
                    
            # If the field isn't found, it's not a match
            else:
                return False
                
        # All criteria matched
        return True
    
    def _values_match(self, item_value: Any, search_value: Any) -> bool:
        """
        Check if a value matches the search criteria.
        
        Args:
            item_value: Value from the item
            search_value: Value from the search criteria
            
        Returns:
            True if values match, False otherwise
        """
        # Handle strings with case-insensitive partial matching
        if isinstance(item_value, str) and isinstance(search_value, str):
            return search_value.lower() in item_value.lower()
            
        # Handle lists (e.g., tags) with any-match semantics
        elif isinstance(item_value, list):
            if isinstance(search_value, list):
                # If search value is also a list, check if any value matches
                return any(self._values_match(item_value, sv) for sv in search_value)
            else:
                # If search value is a scalar, check if it matches any item in the list
                if isinstance(search_value, str):
                    return any(search_value.lower() in str(v).lower() for v in item_value)
                else:
                    return search_value in item_value
                
        # Exact match for other types
        else:
            return item_value == search_value
    
    def _decode_pagination_token(self, pagination_token: Optional[str]) -> Optional[Dict]:
        """
        Decode a pagination token to a DynamoDB last_evaluated_key.
        
        Args:
            pagination_token: Base64 encoded token
            
        Returns:
            Decoded last_evaluated_key or None if no token
            
        Raises:
            ValueError: If token format is invalid
        """
        if not pagination_token:
            return None
            
        try:
            decoded_token = base64.b64decode(pagination_token)
            return json.loads(decoded_token)
        except Exception as e:
            logger.error("Failed to decode pagination token: %s", e)
            raise ValueError(f"Invalid pagination token format: {pagination_token}")
    
    def _encode_pagination_result(self, result: Dict) -> Dict:
        """
        Encode pagination information in a result dictionary.
        
        Args:
            result: Dictionary containing query/scan result with last_evaluated_key
            
        Returns:
            Result with encoded pagination_token
        """
        # Create a copy of the result to avoid modifying the original
        result_copy = result.copy()
        
        # Encode last_evaluated_key as pagination token if present
        if "last_evaluated_key" in result_copy:
            token_bytes = json.dumps(result_copy["last_evaluated_key"]).encode("utf-8")
            result_copy["pagination_token"] = base64.b64encode(token_bytes).decode("utf-8")
            del result_copy["last_evaluated_key"]  # Remove raw key from response
            
        return result_copy

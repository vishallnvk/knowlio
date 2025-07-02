import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

import botocore.exceptions
from helpers.aws_service_helpers.dynamodb_helper import DynamoDBHelper
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.common_helper import Retry
from helpers.common_helper.pagination_helper import PaginationHelper
from enums.content_status import ContentStatus, WorkflowStatus
from config.content_config import CONTENT_TABLE_NAME, DEFAULT_RETRY_MAX_ATTEMPTS, DEFAULT_RETRY_INITIAL_WAIT, WORKFLOW_STATUS_FIELDS

logger = LoggerHelper(__name__).get_logger()

class ContentValidationError(Exception):
    """Exception raised for content data validation failures."""
    pass

class ContentHelper:
    def __init__(self):
        self.db = DynamoDBHelper(table_name=CONTENT_TABLE_NAME)

    @Retry(max_attempts=DEFAULT_RETRY_MAX_ATTEMPTS, initial_wait=DEFAULT_RETRY_INITIAL_WAIT, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def upload_content_metadata(self, content_data: Dict) -> Dict:
        """
        Upload content metadata directly to DynamoDB.
        
        Note: Validation is now handled by the ContentFactory and type-specific models
        in the ContentProcessor before calling this method.
        
        Args:
            content_data: Pre-validated content information dictionary
            
        Returns:
            Dict with success message and content_id
        """
        try:
            content_id = content_data.get("content_id")
            
            # Add timestamps if not present
            if "created_at" not in content_data:
                content_data["created_at"] = datetime.utcnow().isoformat()
            
            logger.info("Uploading content metadata: %s", content_data)
            self.db.put_item(content_data)
            
            return {"message": "Content metadata uploaded", "content_id": content_id}
        except Exception as e:
            logger.error("Error uploading content metadata: %s", str(e))
            raise ContentValidationError(f"Failed to upload content metadata: {str(e)}")

    @Retry(max_attempts=DEFAULT_RETRY_MAX_ATTEMPTS, initial_wait=DEFAULT_RETRY_INITIAL_WAIT, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
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
            "status": ContentStatus.ACTIVE.value,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        return self.db.update_item("content_id", content_id, updates)

    @Retry(max_attempts=DEFAULT_RETRY_MAX_ATTEMPTS, initial_wait=DEFAULT_RETRY_INITIAL_WAIT, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
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

    @Retry(max_attempts=DEFAULT_RETRY_MAX_ATTEMPTS, initial_wait=DEFAULT_RETRY_INITIAL_WAIT, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
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
        
        # Validate status if changing
        if "status" in updates and not ContentStatus.is_valid(updates["status"]):
            valid_statuses = ", ".join(ContentStatus.get_valid_statuses())
            raise ContentValidationError(f"Invalid status: {updates['status']}. Valid statuses: {valid_statuses}")
            
        # Validate workflow statuses if changing
        for status_field in ["rag_status", "training_status", "licensing_status"]:
            if status_field in updates and not WorkflowStatus.is_valid(updates[status_field]):
                valid_statuses = ", ".join(WorkflowStatus.get_valid_statuses())
                raise ContentValidationError(f"Invalid {status_field}: {updates[status_field]}. Valid values: {valid_statuses}")
        
        # Add updated_at timestamp
        updates["updated_at"] = datetime.utcnow().isoformat()
        
        return self.db.update_item("content_id", content_id, updates)

    @Retry(max_attempts=DEFAULT_RETRY_MAX_ATTEMPTS, initial_wait=DEFAULT_RETRY_INITIAL_WAIT, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
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
            
        # For now, nested attribute updates are not supported
        raise ContentValidationError(f"Nested attribute updates are not currently supported: {attribute}")

    @Retry(max_attempts=DEFAULT_RETRY_MAX_ATTEMPTS, initial_wait=DEFAULT_RETRY_INITIAL_WAIT, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def archive_content(self, content_id: str) -> Dict:
        """
        Archive content by setting its status to ARCHIVED.
        
        Args:
            content_id: ID of the content to archive
            
        Returns:
            Updated content item
        """
        logger.info("Archiving content_id: %s", content_id)
        return self.update_content_metadata(content_id, {"status": ContentStatus.ARCHIVED.value})
        
    @Retry(max_attempts=DEFAULT_RETRY_MAX_ATTEMPTS, initial_wait=DEFAULT_RETRY_INITIAL_WAIT, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def search_content(self, search_params: Dict, limit: int = None, 
                      pagination_token: str = None) -> Dict:
        """
        Search content based on provided parameters with pagination support.
        Supports generic content fields and specific fields for different content types.
        
        Args:
            search_params: Dictionary of search parameters, which can include:
                - type: Content type (BOOK, AUDIO, etc.)
                - Any type-specific fields (e.g., authors, publisher for BOOK type)
                - Status fields (rag_status, training_status, licensing_status)
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
        
        # Use the common pagination helper to apply search filters and format results
        result = PaginationHelper.apply_search_filters(base_result, filtered_items, search_params)
        
        # Apply standard pagination encoding
        final_result = PaginationHelper.encode_pagination_result(result)
        
        logger.info("Search returned %d results", len(filtered_items))
        return final_result

    def _get_base_query_result(self, search_params: Dict, limit: int = None, 
                              last_evaluated_key: Dict = None) -> Dict:
        """
        Get the base query result using the most efficient method based on parameters.
        
        Args:
            search_params: Search parameters to use
            limit: Optional maximum number of items to return
            last_evaluated_key: Optional key to start from for pagination
            
        Returns:
            Query result with items and pagination info, including the limit
        """
        # Try to use GSIs for efficiency when possible
        # For the new model, we might have different indexable fields
        indexable_fields = ["type", "status"]
        
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
                    
                    # Include the limit in the result for pagination calculation
                    if limit is not None:
                        result["limit"] = limit
                        
                    return result
                except Exception as e:
                    logger.warning("Failed to use index for %s: %s", field, e)
                    # Continue to the next field or fall back to scan
        
        # If no indexed field is available, fall back to scan
        result = self.db.scan_items(
            limit=limit,
            last_evaluated_key=last_evaluated_key
        )
        
        # Include the limit in the result for pagination calculation
        if limit is not None:
            result["limit"] = limit
            
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
        for key, value in search_params.items():
            # Handle standard fields
            if key in item:
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
            
        # Handle lists (e.g., tags, authors, keywords) with any-match semantics
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
        return PaginationHelper.decode_pagination_token(pagination_token)
    
    def _encode_pagination_result(self, result: Dict) -> Dict:
        """
        Encode pagination information in a result dictionary.
        
        Args:
            result: Dictionary containing query/scan result with last_evaluated_key
            
        Returns:
            Result with encoded pagination_token and proper pagination structure
        """
        return PaginationHelper.encode_pagination_result(result)

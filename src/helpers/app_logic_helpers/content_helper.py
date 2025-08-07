import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

import botocore.exceptions
from helpers.aws_service_helpers.dynamodb_helper import DynamoDBHelper
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.common_helper import Retry
from helpers.common_helper.pagination_helper import PaginationHelper
from helpers.common_helper.data_type_utils import DataTypeUtils, ContentDataValidator
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
            
            # Use safe logging format to prevent type errors
            safe_content_data = DataTypeUtils.safe_logging_format(content_data)
            logger.info("Uploading content metadata: %s", safe_content_data)
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
        try:
            # Safely format the attribute and value for logging
            safe_attribute = DataTypeUtils.safe_string_conversion(attribute)
            safe_value = DataTypeUtils.safe_logging_format(value)
            
            logger.info("Updating attribute '%s' for content_id: %s with value: %s", 
                       safe_attribute, content_id, safe_value)
            
            # Validate and normalize the attribute value
            try:
                normalized_value = ContentDataValidator.validate_content_attribute_value(safe_attribute, value)
            except ValueError as e:
                raise ContentValidationError(f"Invalid value for attribute '{safe_attribute}': {str(e)}")
            
            # For top-level attributes, use update_content_metadata
            if "." not in safe_attribute:
                return self.update_content_metadata(content_id, {safe_attribute: normalized_value})
                
            # For nested attributes, we need to get the current content first
            content = self.get_content_details(content_id)
            if not content:
                raise ContentValidationError(f"Content not found with ID: {content_id}")
                
            # For now, nested attribute updates are not supported
            raise ContentValidationError(f"Nested attribute updates are not currently supported: {safe_attribute}")
            
        except ContentValidationError:
            raise
        except Exception as e:
            logger.error("Error updating content attribute: %s", str(e))
            raise ContentValidationError(f"Failed to update content attribute: {str(e)}")

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
                      pagination_token: str = None, count_only: bool = False, 
                      user_id: str = None) -> Dict:
        """
        Search content based on provided parameters with pagination support.
        Supports generic content fields and specific fields for different content types.
        
        IMPORTANT: This method enforces user isolation - content is always filtered by user_id.
        
        Args:
            search_params: Dictionary of search parameters, which can include:
                - type: Content type (BOOK, AUDIO, etc.)
                - Any type-specific fields (e.g., authors, publisher for BOOK type)
                - Status fields (rag_status, training_status, licensing_status)
            limit: Optional maximum number of items to return
            pagination_token: Optional pagination token from previous query
            count_only: If True, return only count information without full items
            user_id: User ID to filter content by (required for user isolation)
                
        Returns:
            Dict containing matching content items and pagination details, or just count if count_only=True
        """
        try:
            # CRITICAL: Enforce user isolation - user_id must be provided
            if not user_id:
                raise ContentValidationError("User ID is required for content search - user isolation enforced")
            
            # Safely format search parameters for logging
            safe_search_params = DataTypeUtils.safe_logging_format(search_params)
            logger.info("Searching content with parameters: %s (limit: %s) for user: %s", safe_search_params, limit, user_id)
            
            # Validate and normalize search parameters to prevent type errors
            validated_search_params = ContentDataValidator.validate_search_parameters(search_params)
            
            # CRITICAL: Always add user_id filter for user isolation
            # (Content items store user information in user_id field)
            validated_search_params["user_id"] = user_id
            
            # Convert pagination token from string to dict if provided
            last_evaluated_key = self._decode_pagination_token(pagination_token)
            
            # DEBUGGING: Log the decoded pagination token
            if last_evaluated_key:
                logger.info("PAGINATION DEBUG: Decoded pagination token: %s", last_evaluated_key)
            else:
                logger.info("PAGINATION DEBUG: No pagination token provided (first page)")
            
            # Use the most efficient query method based on parameters
            base_result = self._get_base_query_result(validated_search_params, limit, last_evaluated_key)
            
            # Apply filters based on provided search parameters
            filtered_items = []
            gsi_filtered_field = base_result.get("gsi_filtered_field")
            used_composite_gsi = base_result.get("used_composite_gsi", False)
            
            # DEBUGGING: Log the items returned from the query
            query_items = base_result.get("items", [])
            logger.info("FILTER DEBUG: Query returned %d items to filter", len(query_items))
            logger.info("FILTER DEBUG: GSI filtered field: %s, Used composite GSI: %s", gsi_filtered_field, used_composite_gsi)
            logger.info("FILTER DEBUG: Validated search params: %s", DataTypeUtils.safe_logging_format(validated_search_params))
            
            for i, item in enumerate(query_items):
                item_content_id = item.get("content_id", f"unknown_{i}")
                logger.info("FILTER DEBUG: Processing item %d: content_id=%s", i+1, item_content_id)
                
                # CRITICAL: Skip redundant user isolation filtering when using composite GSI
                # The composite key (user_id#type) already ensures user isolation
                if not used_composite_gsi and not self._user_owns_content(item, user_id):
                    logger.warning("FILTER DEBUG: Skipping content item not owned by user %s: %s", user_id, item_content_id)
                    continue
                
                # DEBUGGING: Log the criteria matching process
                matches_criteria = self._matches_search_criteria(item, validated_search_params, gsi_filtered_field, user_id, used_composite_gsi)
                logger.info("FILTER DEBUG: Item %s matches criteria: %s", item_content_id, matches_criteria)
                    
                if matches_criteria:
                    filtered_items.append(item)
                    logger.info("FILTER DEBUG: Item %s INCLUDED in results", item_content_id)
                else:
                    logger.info("FILTER DEBUG: Item %s EXCLUDED from results", item_content_id)
            
            logger.info("FILTER DEBUG: Final filtered items count: %d (from %d original items)", len(filtered_items), len(query_items))
            
            # If count_only is True, return just the count information
            if count_only:
                logger.info("Count-only search returned %d results for user %s", len(filtered_items), user_id)
                return {
                    "count": len(filtered_items),
                    "total_scanned": base_result.get("total_scanned", len(base_result.get("items", [])))
                }
            
            # Use the common pagination helper to apply search filters and format results
            result = PaginationHelper.apply_search_filters(base_result, filtered_items, validated_search_params)
            
            # Apply standard pagination encoding
            final_result = PaginationHelper.encode_pagination_result(result)
            
            logger.info("Search returned %d results for user %s", len(filtered_items), user_id)
            return final_result
            
        except Exception as e:
            logger.error("Error in search_content for user %s: %s", user_id, str(e))
            raise ContentValidationError(f"Search failed: {str(e)}")

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
        
        # DEBUGGING: Log the search parameters to understand the query path
        logger.info("QUERY DEBUG: search_params=%s, indexable_fields=%s", search_params, indexable_fields)
        
        for field in indexable_fields:
            if field in search_params:
                logger.info("QUERY DEBUG: Found indexable field '%s' with value '%s'", field, search_params[field])
                
                try:
                    # For content type queries, use user-aware composite key query to fix pagination
                    is_type_field = (field == "type")
                    has_user_id = ("user_id" in search_params)
                    user_id_value = search_params.get("user_id", "N/A")
                    
                    logger.info("QUERY DEBUG: Condition check - field=%s, is_type_field=%s, has_user_id=%s, user_id_value=%s", 
                               field, is_type_field, has_user_id, user_id_value)
                    
                    # CRITICAL FIX: Always use user-aware composite key query for type queries when user_id is present
                    # This ensures proper user isolation and fixes pagination issues
                    if is_type_field and has_user_id and user_id_value != "N/A":
                        logger.info("QUERY DEBUG: Using user-aware composite key query for type=%s, user=%s", 
                                   search_params[field], user_id_value)
                        result = self.db.query_user_aware_items(
                            user_id=user_id_value,
                            content_type=search_params[field],
                            limit=limit,
                            last_evaluated_key=last_evaluated_key
                        )
                        # Mark that we used composite GSI to skip redundant user isolation filtering
                        result["used_composite_gsi"] = True
                        logger.info("QUERY DEBUG: User-aware composite key query completed, returned %d items", 
                                   len(result.get("items", [])))
                    else:
                        # Use regular GSI query for other fields
                        logger.info("QUERY DEBUG: Using regular GSI query for field='%s' (reason: is_type=%s, has_user_id=%s, user_id=%s)", 
                                   field, is_type_field, has_user_id, user_id_value)
                        result = self.db.query_items(
                            key_name=field,
                            key_value=search_params[field],
                            limit=limit,
                            last_evaluated_key=last_evaluated_key
                        )
                        logger.info("QUERY DEBUG: Regular GSI query completed, returned %d items", 
                                   len(result.get("items", [])))
                    
                    # Mark this field as already filtered by the GSI query
                    result["gsi_filtered_field"] = field
                    
                    # Include the limit in the result for pagination calculation
                    if limit is not None:
                        result["limit"] = limit
                        
                    return result
                except Exception as e:
                    logger.warning("Failed to use index for %s: %s", field, e)
                    # Continue to the next field or fall back to scan
        
        # If no indexed field is available, fall back to scan
        logger.info("QUERY DEBUG: No indexable fields found, falling back to scan")
        result = self.db.scan_items(
            limit=limit,
            last_evaluated_key=last_evaluated_key
        )
        
        # Include the limit in the result for pagination calculation
        if limit is not None:
            result["limit"] = limit
            
        return result
    
    def _matches_search_criteria(self, item: Dict, search_params: Dict, gsi_filtered_field: str = None, 
                                 user_id: str = None, used_composite_gsi: bool = False) -> bool:
        """
        Check if an item matches all search criteria.
        
        Args:
            item: Content item to check
            search_params: Search parameters to match against
            gsi_filtered_field: Field that was already filtered by GSI query (should be skipped)
            user_id: User ID for debugging purposes
            used_composite_gsi: Whether a composite GSI was used (affects user_id filtering)
            
        Returns:
            True if the item matches all criteria, False otherwise
        """
        # CRITICAL FIX: Define system/pagination parameters that should NOT be treated as search criteria
        system_parameters = {
            "next_token",           # Pagination token
            "pagination_token",     # Alternative pagination token name
            "limit",               # Result limit
            "count_only",          # Count-only flag
            "user_id",             # User ID (when using composite GSI, already filtered)
            "offset",              # Potential offset parameter
            "cursor"               # Potential cursor parameter
        }
        
        item_content_id = item.get("content_id", "unknown")
        logger.info("CRITERIA DEBUG: Checking criteria for item %s", item_content_id)
        logger.info("CRITERIA DEBUG: System parameters to exclude: %s", system_parameters)
        logger.info("CRITERIA DEBUG: GSI filtered field to skip: %s", gsi_filtered_field)
        logger.info("CRITERIA DEBUG: Used composite GSI: %s", used_composite_gsi)
        
        for key, value in search_params.items():
            logger.info("CRITERIA DEBUG: Evaluating parameter %s = %s", key, value)
            
            # Skip the field that was already filtered by GSI query
            if key == gsi_filtered_field:
                logger.info("CRITERIA DEBUG: Skipping %s (GSI filtered field)", key)
                continue
            
            # CRITICAL FIX: Skip system/pagination parameters that are not search criteria
            if key in system_parameters:
                logger.info("CRITERIA DEBUG: Skipping %s (system parameter)", key)
                # Special handling for user_id when using composite GSI
                if key == "user_id" and used_composite_gsi:
                    logger.info("CRITERIA DEBUG: user_id already handled by composite GSI, skipping criteria check")
                continue
                
            # Handle standard fields
            if key in item:
                matches = self._values_match(item[key], value)
                logger.info("CRITERIA DEBUG: Field %s in item, matches: %s (item_value=%s, search_value=%s)", 
                           key, matches, item[key], value)
                if not matches:
                    logger.info("CRITERIA DEBUG: Item %s FAILED criteria check for field %s", item_content_id, key)
                    return False
                    
            # Handle workflow status fields
            elif key in ["rag_status", "training_status", "licensing_status"] and key in item:
                matches = (item[key] == value)
                logger.info("CRITERIA DEBUG: Workflow status field %s, matches: %s (item_value=%s, search_value=%s)", 
                           key, matches, item[key], value)
                if not matches:
                    logger.info("CRITERIA DEBUG: Item %s FAILED workflow status check for field %s", item_content_id, key)
                    return False
                    
            # If the field isn't found and it's not a system parameter, it's not a match
            else:
                logger.info("CRITERIA DEBUG: Field %s not found in item %s, this is a FAILURE", key, item_content_id)
                return False
                
        # All criteria matched
        logger.info("CRITERIA DEBUG: Item %s PASSED all criteria checks", item_content_id)
        return True
    
    def _values_match(self, item_value: Any, search_value: Any) -> bool:
        """
        Check if a value matches the search criteria using safe type handling.
        
        Args:
            item_value: Value from the item
            search_value: Value from the search criteria
            
        Returns:
            True if values match, False otherwise
        """
        try:
            # Use safe comparison utilities to handle type mismatches
            if item_value is None or search_value is None:
                return item_value == search_value
            
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
                    search_str = DataTypeUtils.safe_string_conversion(search_value).lower()
                    return any(search_str in DataTypeUtils.safe_string_conversion(v).lower() for v in item_value)
                    
            # Use safe equality check for other types
            else:
                return DataTypeUtils.safe_equality_check(item_value, search_value)
                
        except Exception as e:
            logger.warning("Error in _values_match: %s", str(e))
            # Fall back to safe equality check
            return DataTypeUtils.safe_equality_check(item_value, search_value)
    
    def _user_owns_content(self, item: Dict, user_id: str) -> bool:
        """
        Check if a user owns a content item - critical for user isolation.
        
        Args:
            item: Content item to check
            user_id: User ID to check ownership for
            
        Returns:
            True if user owns the content, False otherwise
        """
        try:
            # Get the user_id from the item (content items store user info in user_id field)
            item_user_id = item.get("user_id")
            
            # If no user_id in item, it's not owned by any user (should not happen)
            if not item_user_id:
                logger.warning("Content item missing user_id: %s", item.get("content_id", "unknown"))
                return False
            
            # Check if the user_id matches the requesting user_id
            return DataTypeUtils.safe_equality_check(item_user_id, user_id)
            
        except Exception as e:
            logger.error("Error checking content ownership: %s", str(e))
            # Default to False for security - deny access if there's an error
            return False
    
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

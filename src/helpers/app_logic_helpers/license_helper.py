import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any

import botocore.exceptions
from helpers.aws_service_helpers.dynamodb_helper import DynamoDBHelper
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.common_helper import Retry
from helpers.common_helper.pagination_helper import PaginationHelper
from models.license_model import LicenseModel
from config.license_config import (
    LICENSES_TABLE_NAME,
    DEFAULT_RETRY_MAX_ATTEMPTS,
    DEFAULT_RETRY_INITIAL_WAIT,
    INDEXED_FIELDS
)

logger = LoggerHelper(__name__).get_logger()

class LicenseHelper:
    def __init__(self):
        self.db = DynamoDBHelper(table_name=LICENSES_TABLE_NAME)

    @Retry(max_attempts=DEFAULT_RETRY_MAX_ATTEMPTS, initial_wait=DEFAULT_RETRY_INITIAL_WAIT, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def create_license(self, license_data: Dict) -> Dict:
        """
        Create a new license.
        
        Args:
            license_data: License information
            
        Returns:
            Dict with success message and license_id
        """
        license_item = LicenseModel(license_data).__dict__

        logger.info("Creating license: %s", license_item)
        self.db.put_item(license_item)
        return {"message": "License created successfully", "license_id": license_item["license_id"]}

    @Retry(max_attempts=DEFAULT_RETRY_MAX_ATTEMPTS, initial_wait=DEFAULT_RETRY_INITIAL_WAIT, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def get_license(self, license_id: str) -> Optional[Dict]:
        """
        Get license details by ID.
        
        Args:
            license_id: ID of the license to fetch
            
        Returns:
            License details or None if not found
        """
        logger.info("Fetching license for license_id: %s", license_id)
        return self.db.get_item({"license_id": license_id})

    @Retry(max_attempts=DEFAULT_RETRY_MAX_ATTEMPTS, initial_wait=DEFAULT_RETRY_INITIAL_WAIT, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def search_licenses(self, search_params: Dict, limit: int = None, pagination_token: str = None) -> Dict:
        """
        Search licenses based on provided parameters with pagination support.
        Unified replacement for list_licenses_by_consumer and list_licenses_by_content.
        
        Args:
            search_params: Dictionary of search parameters, which can include:
                - consumer_id: Filter by consumer
                - content_id: Filter by content
                - publisher_id: Filter by publisher
                - status: License status (ACTIVE, REVOKED)
                - Any license fields to match
            limit: Optional maximum number of items to return
            pagination_token: Optional pagination token from previous query
                
        Returns:
            Dict containing matching license items and pagination details
        """
        logger.info("Searching licenses with parameters: %s (limit: %s)", search_params, limit)
        
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
        for field in INDEXED_FIELDS:
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
            item: License item to check
            search_params: Search parameters to match against
            
        Returns:
            True if the item matches all criteria, False otherwise
        """
        for key, value in search_params.items():
            # Skip internal fields and headers
            if key.startswith('_'):
                continue
                
            # Handle standard fields
            if key in item:
                if not self._values_match(item[key], value):
                    return False
            # If the field isn't found, it's not a match
            else:
                # Log that the field is missing for debugging
                logger.debug("Field '%s' not found in item: %s", key, item)
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
            
        # Handle lists with any-match semantics
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

    @Retry(max_attempts=DEFAULT_RETRY_MAX_ATTEMPTS, initial_wait=DEFAULT_RETRY_INITIAL_WAIT, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def revoke_license(self, license_id: str, revocation_data: Dict = None) -> Dict:
        """
        Revoke a license.
        
        Args:
            license_id: ID of the license to revoke
            revocation_data: Optional additional data to include in the revocation (e.g., who revoked it)
            
        Returns:
            Updated license item
        """
        logger.info("Revoking license for license_id: %s", license_id)
        updates = {
            "status": "REVOKED",
            "revoked_at": datetime.utcnow().isoformat()
        }
        
        # Add any additional revocation data
        if revocation_data:
            updates.update(revocation_data)
            
        return self.db.update_item("license_id", license_id, updates)
        
    def _decode_pagination_token(self, pagination_token: Optional[str]) -> Optional[Dict]:
        """
        Decode a pagination token to a DynamoDB last_evaluated_key.
        
        Args:
            pagination_token: Base64 encoded token
            
        Returns:
            Decoded last_evaluated_key or None if no token
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

import uuid
import json
import base64
from datetime import datetime
from typing import Optional, Dict, List, Any

import botocore.exceptions
from helpers.aws_service_helpers.dynamodb_helper import DynamoDBHelper
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.common_helper import Retry
from models.license_model import LicenseModel

logger = LoggerHelper(__name__).get_logger()

LICENSES_TABLE = "licenses"

class LicenseHelper:
    def __init__(self):
        self.db = DynamoDBHelper(table_name=LICENSES_TABLE)

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
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

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
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

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
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
        
        # Prepare result with pagination
        result = {
            "items": filtered_items,
            "count": len(filtered_items),
            "total_scanned": base_result.get("count", 0)
        }
        
        # If no items were found after filtering, explicitly set has_more=False
        # even if DynamoDB returned a LastEvaluatedKey
        if len(filtered_items) == 0:
            result["has_more"] = False
        else:
            # Otherwise, use the has_more flag from the base query
            result["has_more"] = base_result.get("has_more", False)
        
        # Only include pagination token if there are filtered items
        # and the base query has a LastEvaluatedKey
        if len(filtered_items) > 0 and base_result.get("last_evaluated_key"):
            result["last_evaluated_key"] = base_result["last_evaluated_key"]
        elif len(filtered_items) == 0:
            # If no items were found, don't include a pagination token
            # regardless of whether the base query had a LastEvaluatedKey
            logger.info("No items found after filtering, setting has_more=False and removing pagination token")
        
        # Apply standard pagination encoding
        final_result = self._encode_pagination_result(result)
        
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
        indexable_fields = ["consumer_id", "content_id", "publisher_id", "status"]
        
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

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def revoke_license(self, license_id: str) -> Dict:
        """
        Revoke a license.
        
        Args:
            license_id: ID of the license to revoke
            
        Returns:
            Updated license item
        """
        logger.info("Revoking license for license_id: %s", license_id)
        updates = {
            "status": "REVOKED",
            "revoked_at": datetime.utcnow().isoformat()
        }
        return self.db.update_item("license_id", license_id, updates)
        
    def _decode_pagination_token(self, pagination_token: Optional[str]) -> Optional[Dict]:
        """
        Decode a pagination token to a DynamoDB last_evaluated_key.
        
        Args:
            pagination_token: Base64 encoded token
            
        Returns:
            Decoded last_evaluated_key or None if no token
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
            Result with encoded pagination_token and proper pagination structure
        """
        # Create a copy of the result to avoid modifying the original
        result_copy = result.copy()
        
        # Only add pagination if there are actual results
        items = result_copy.get("items", [])
        
        # If no items present, never add pagination regardless of has_more
        if len(items) == 0:
            # Add empty pagination structure with has_more=false
            result_copy["pagination"] = {
                "has_more": False
            }
            logger.debug("No items in result, setting has_more=False")
        else:
            # Get has_more flag from the result
            has_more = result_copy.get("has_more", False)
            
            # If has_more is True, ensure we have a last_evaluated_key to use
            if has_more and "last_evaluated_key" in result_copy:
                token_bytes = json.dumps(result_copy["last_evaluated_key"]).encode("utf-8")
                pagination_token = base64.b64encode(token_bytes).decode("utf-8")
                
                # Create pagination structure with next token
                result_copy["pagination"] = {
                    "next_token": pagination_token,
                    "has_more": True
                }
            else:
                # Add pagination structure with has_more=false if no token available
                result_copy["pagination"] = {
                    "has_more": False
                }
                if has_more:
                    logger.warning("has_more=True but no last_evaluated_key available, correcting to has_more=False")
        
        # Remove raw key from response
        if "last_evaluated_key" in result_copy:
            del result_copy["last_evaluated_key"]
            
        return result_copy

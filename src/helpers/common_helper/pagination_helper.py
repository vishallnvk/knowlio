import json
import base64
from typing import Dict, Optional

from helpers.common_helper.logger_helper import LoggerHelper

logger = LoggerHelper(__name__).get_logger()

class PaginationHelper:
    """
    Standardized pagination helper for all API endpoints.
    Ensures consistent pagination behavior across content, license and user endpoints.
    """
    
    @staticmethod
    def decode_pagination_token(pagination_token: Optional[str]) -> Optional[Dict]:
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
            
    @staticmethod
    def encode_pagination_result(result: Dict) -> Dict:
        """
        Encode pagination information in a result dictionary.
        This method handles edge cases such as:
        - Empty result sets never have has_more=true
        - A pagination token is only provided when there are items and more to fetch
        
        Args:
            result: Dictionary containing query/scan result with last_evaluated_key
            
        Returns:
            Result with encoded pagination_token and proper pagination structure
        """
        # Create a copy of the result to avoid modifying the original
        result_copy = result.copy()
        
        # Only add pagination if there are actual results
        items = result_copy.get("items", [])
        
        # If no items present, never add pagination with has_more=true
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
        
    @staticmethod
    def apply_search_filters(base_result: Dict, filtered_items: list, search_params: Dict = None) -> Dict:
        """
        Create a correctly formatted result object with proper pagination handling for empty result sets.
        
        Args:
            base_result: Original query/scan result from DynamoDB
            filtered_items: List of items after applying filters
            search_params: Original search parameters (optional, for logging)
            
        Returns:
            Result with proper structure and pagination flags
        """
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
            logger.debug("No items found after filtering, setting has_more=False and removing pagination token")
        else:
            # Otherwise, use the has_more flag from the base query
            result["has_more"] = base_result.get("has_more", False)
        
        # Only include pagination token if there are filtered items
        # and the base query has a LastEvaluatedKey
        if len(filtered_items) > 0 and base_result.get("last_evaluated_key"):
            result["last_evaluated_key"] = base_result["last_evaluated_key"]
            
        return result

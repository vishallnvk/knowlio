import uuid
import json
import base64
from datetime import datetime
from typing import Optional, Dict, List

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
    def list_licenses_by_consumer(self, consumer_id: str, limit: int = None, pagination_token: str = None) -> Dict:
        """
        List licenses by consumer with pagination.
        
        Args:
            consumer_id: ID of the consumer to list licenses for
            limit: Maximum number of items to return
            pagination_token: Token for pagination
            
        Returns:
            Dict with licenses and pagination info
        """
        logger.info("Listing licenses for consumer_id: %s (limit: %s)", consumer_id, limit)
        
        result = self.db.query_items(
            key_name="consumer_id", 
            key_value=consumer_id,
            limit=limit,
            last_evaluated_key=self._decode_pagination_token(pagination_token)
        )
        
        # Include the limit in the result for pagination calculation
        if limit is not None:
            result["limit"] = limit
        
        # Apply proper pagination encoding
        return self._encode_pagination_result(result)

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def list_licenses_by_content(self, content_id: str, limit: int = None, pagination_token: str = None) -> Dict:
        """
        List licenses by content with pagination.
        
        Args:
            content_id: ID of the content to list licenses for
            limit: Maximum number of items to return
            pagination_token: Token for pagination
            
        Returns:
            Dict with licenses and pagination info
        """
        logger.info("Listing licenses for content_id: %s (limit: %s)", content_id, limit)
        
        result = self.db.query_items(
            key_name="content_id", 
            key_value=content_id,
            limit=limit,
            last_evaluated_key=self._decode_pagination_token(pagination_token)
        )
        
        # Include the limit in the result for pagination calculation
        if limit is not None:
            result["limit"] = limit
        
        # Apply proper pagination encoding
        return self._encode_pagination_result(result)

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
        
        # Determine if there are more items to fetch
        # Consider both: if we have a last_evaluated_key AND if the current query returned full limit
        has_more = False
        if "last_evaluated_key" in result_copy:
            # Check if we're at the last page
            # If this page has fewer items than the limit, it's the last page regardless of last_evaluated_key
            limit = result_copy.get("limit")
            if limit is not None and len(items) >= limit:
                has_more = True
            elif limit is None and len(items) > 0:
                # If no limit was specified but we have items and a token, assume more pages
                has_more = True
            # Otherwise, even with last_evaluated_key, if we have < limit items, we're done
        
        # Add pagination information to the response if there are items
        if len(items) > 0:
            if has_more and "last_evaluated_key" in result_copy:
                token_bytes = json.dumps(result_copy["last_evaluated_key"]).encode("utf-8")
                pagination_token = base64.b64encode(token_bytes).decode("utf-8")
                
                # Create pagination structure with next token
                result_copy["pagination"] = {
                    "next_token": pagination_token,
                    "has_more": True
                }
            else:
                # Add pagination structure with has_more=false
                result_copy["pagination"] = {
                    "has_more": False
                }
        
        # Remove raw key from response
        if "last_evaluated_key" in result_copy:
            del result_copy["last_evaluated_key"]
            
        return result_copy

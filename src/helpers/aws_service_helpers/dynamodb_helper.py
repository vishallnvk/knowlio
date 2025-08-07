import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import Dict, List, Any, Optional, Union
import botocore.exceptions

from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.common_helper import Retry
from helpers.common_helper.database_operation_wrapper import DatabaseOperationWrapper

logger = LoggerHelper(__name__).get_logger()


class DynamoDBHelper:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def put_item(self, item: Any) -> None:
        """
        Put an item into DynamoDB with comprehensive type safety.
        
        Args:
            item: Item to put (any type, will be sanitized)
        """
        # Validate operation
        if not DatabaseOperationWrapper.validate_database_operation("put_item", item=item):
            raise ValueError("Invalid put_item operation parameters")
        
        # Convert item to safe format
        safe_item = DatabaseOperationWrapper.safe_item_conversion(item)
        
        # Log operation safely
        DatabaseOperationWrapper.log_operation_safely("put_item", item=safe_item)
        
        # Execute the operation
        self.table.put_item(Item=safe_item)

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def get_item(self, key: Union[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Get an item from DynamoDB with comprehensive type safety.
        
        Args:
            key: Key to get (string or dict, will be sanitized)
            
        Returns:
            Item if found, None otherwise
        """
        # Validate operation
        if not DatabaseOperationWrapper.validate_database_operation("get_item", key=key):
            raise ValueError("Invalid get_item operation parameters")
        
        # Convert key to safe format
        safe_key = DatabaseOperationWrapper.safe_key_conversion(key)
        
        # Log operation safely
        DatabaseOperationWrapper.log_operation_safely("get_item", key=safe_key)
        
        # Execute the operation
        response = self.table.get_item(Key=safe_key)
        item = response.get("Item")
        
        # Sanitize the response
        if item:
            return DatabaseOperationWrapper.sanitize_for_database(item)
        return None

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def update_item(self, key: Union[str, Dict[str, Any]], updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an item in DynamoDB with comprehensive type safety.
        
        Args:
            key: Key to update (string or dict, will be sanitized)
            updates: Updates to apply (dict, will be sanitized)
            
        Returns:
            Updated item attributes if successful, None otherwise
        """
        # Validate operation
        if not DatabaseOperationWrapper.validate_database_operation("update_item", key=key, updates=updates):
            raise ValueError("Invalid update_item operation parameters")
        
        # Convert key to safe format
        safe_key = DatabaseOperationWrapper.safe_key_conversion(key)
        
        # Prepare safe update expression
        update_expression, expression_attr_names, expression_attr_values = \
            DatabaseOperationWrapper.prepare_update_expression(updates)
        
        if not update_expression:
            logger.warning("No valid updates provided")
            return None
        
        # Log operation safely
        DatabaseOperationWrapper.log_operation_safely("update_item", 
                                                      key=safe_key, 
                                                      updates=updates)
        
        # Execute the operation
        response = self.table.update_item(
            Key=safe_key,
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues="ALL_NEW"
        )
        
        # Sanitize the response
        attributes = response.get("Attributes")
        if attributes:
            return DatabaseOperationWrapper.sanitize_for_database(attributes)
        return None

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def query_items(self, key_name: str, key_value: str, limit: int = None, 
                   last_evaluated_key: Dict = None) -> Dict:
        """
        Query items with pagination support
        
        Args:
            key_name: The name of the key to query on
            key_value: The value of the key to match
            limit: Optional maximum number of items to return
            last_evaluated_key: Optional key to start from for pagination
            
        Returns:
            Dict containing items and optional last_evaluated_key for pagination
        """
        if last_evaluated_key:
            logger.info("Querying items where %s = %s (limit: %s, pagination_token: %s)", 
                       key_name, key_value, limit, last_evaluated_key)
        else:
            logger.info("Querying items where %s = %s (limit: %s)", key_name, key_value, limit)
        query_kwargs = {
            "IndexName": f"{key_name}-index",  # assumes GSI is defined as `${key_name}-index`
            "KeyConditionExpression": Key(key_name).eq(key_value)
        }
        
        if limit is not None:
            query_kwargs["Limit"] = limit
            
        if last_evaluated_key:
            query_kwargs["ExclusiveStartKey"] = last_evaluated_key
            
        try:
            response = self.table.query(**query_kwargs)
            logger.info("Query succeeded using GSI")
            result = {
                "items": response.get("Items", []),
                "count": response.get("Count", 0),
                "scanned_count": response.get("ScannedCount", 0),
            }
            
            # Add pagination token if there are more results
            if "LastEvaluatedKey" in response:
                result["last_evaluated_key"] = response["LastEvaluatedKey"]
                if len(result["items"]) > 0:
                    # Only set has_more=true if we actually got items AND there's a LastEvaluatedKey
                    result["has_more"] = True
                else:
                    # Even with LastEvaluatedKey, if no items were returned, we're done
                    result["has_more"] = False
                    logger.info("Setting has_more=false because no items were returned despite having LastEvaluatedKey")
            else:
                result["has_more"] = False
                
            # Add limit to result for proper pagination handling
            if limit is not None:
                result["limit"] = limit
                
            logger.info("Query returned %d items, has_more=%s", len(result["items"]), result["has_more"])
            return result
            
        except Exception as e:
            logger.warning("GSI not found for %s. Falling back to scan. Error: %s", key_name, e)
            # fallback: full table scan with pagination
            return self.scan_items(
                filter_expression=Attr(key_name).eq(key_value),
                limit=limit,
                last_evaluated_key=last_evaluated_key
            )

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def query_user_aware_items(self, user_id: str, content_type: str, limit: int = None, 
                              last_evaluated_key: Dict = None) -> Dict:
        """
        Query items using user-aware composite key for efficient user isolation with pagination.
        This method eliminates the pagination bug by ensuring queries respect user boundaries.
        
        Args:
            user_id: The user ID for user isolation
            content_type: The content type to query (BOOK, AUDIO, etc.)
            limit: Optional maximum number of items to return
            last_evaluated_key: Optional key to start from for pagination
            
        Returns:
            Dict containing items and optional last_evaluated_key for pagination
        """
        # Create composite key value in format: user_id#type
        composite_key_value = f"{user_id}#{content_type}"
        
        if last_evaluated_key:
            logger.info("User-aware query: user_type_key = %s (limit: %s, pagination_token: %s)", 
                       composite_key_value, limit, last_evaluated_key)
        else:
            logger.info("User-aware query: user_type_key = %s (limit: %s)", composite_key_value, limit)
        
        query_kwargs = {
            "IndexName": "user_type-index",
            "KeyConditionExpression": Key("user_type_key").eq(composite_key_value)
        }
        
        if limit is not None:
            query_kwargs["Limit"] = limit
            
        if last_evaluated_key:
            # CRITICAL FIX: Validate that the pagination token has the correct composite GSI structure
            if "user_type_key" not in last_evaluated_key:
                logger.warning("Pagination token missing user_type_key, reconstructing for composite GSI")
                # Reconstruct the correct key structure
                fixed_key = {
                    "user_type_key": composite_key_value
                }
                # Copy over any other keys from the token
                for k, v in last_evaluated_key.items():
                    if k != "type":  # Skip the old "type" field
                        fixed_key[k] = v
                query_kwargs["ExclusiveStartKey"] = fixed_key
                logger.info("PAGINATION DEBUG: Reconstructed ExclusiveStartKey: %s", fixed_key)
            else:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key
                logger.info("PAGINATION DEBUG: Using original ExclusiveStartKey: %s", last_evaluated_key)
            
        try:
            response = self.table.query(**query_kwargs)
            logger.info("User-aware query succeeded using composite GSI")
            
            result = {
                "items": response.get("Items", []),
                "count": response.get("Count", 0),
                "scanned_count": response.get("ScannedCount", 0),
            }
            
            # Add pagination token if there are more results
            if "LastEvaluatedKey" in response:
                # CRITICAL FIX: Ensure the returned LastEvaluatedKey has the correct format
                # for the next pagination request
                raw_key = response["LastEvaluatedKey"]
                result["last_evaluated_key"] = raw_key
                
                # Debug log to verify the key structure
                logger.info("Raw LastEvaluatedKey structure: %s", raw_key)
                
                if len(result["items"]) > 0:
                    result["has_more"] = True
                else:
                    result["has_more"] = False
                    logger.info("Setting has_more=false because no items were returned despite having LastEvaluatedKey")
            else:
                result["has_more"] = False
                
            # Add limit to result for proper pagination handling
            if limit is not None:
                result["limit"] = limit
                
            logger.info("User-aware query returned %d items for user %s, has_more=%s", 
                       len(result["items"]), user_id, result["has_more"])
            return result
            
        except Exception as e:
            logger.error("User-aware query failed for user %s, type %s. Error: %s", user_id, content_type, e)
            # Fallback to regular user_id query if composite index is not available
            logger.info("Falling back to user_id-index query")
            return self.query_items("user_id", user_id, limit, last_evaluated_key)

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def scan_items(self, filter_expression=None, limit: int = None, 
                  last_evaluated_key: Dict = None) -> Dict:
        """
        Scan items with pagination support
        
        Args:
            filter_expression: Optional filter expression
            limit: Optional maximum number of items to return
            last_evaluated_key: Optional key to start from for pagination
            
        Returns:
            Dict containing items and optional last_evaluated_key for pagination
        """
        if last_evaluated_key:
            logger.info("Scanning table: %s (limit: %s, pagination_token: %s)", self.table_name, limit, last_evaluated_key)
        else:
            logger.info("Scanning table: %s (limit: %s)", self.table_name, limit)
        scan_kwargs = {}
        
        if filter_expression:
            scan_kwargs["FilterExpression"] = filter_expression
            
        if limit is not None:
            scan_kwargs["Limit"] = limit
            
        if last_evaluated_key:
            scan_kwargs["ExclusiveStartKey"] = last_evaluated_key
            
        response = self.table.scan(**scan_kwargs)
        
        result = {
            "items": response.get("Items", []),
            "count": response.get("Count", 0),
            "scanned_count": response.get("ScannedCount", 0),
        }
        
        # Add pagination token if there are more results
        if "LastEvaluatedKey" in response:
            result["last_evaluated_key"] = response["LastEvaluatedKey"]
            if len(result["items"]) > 0:
                # Only set has_more=true if we actually got items AND there's a LastEvaluatedKey
                result["has_more"] = True
            else:
                # Even with LastEvaluatedKey, if no items were returned, we're done
                result["has_more"] = False
                logger.info("Setting has_more=false because no items were returned despite having LastEvaluatedKey")
        else:
            result["has_more"] = False
            
        # Add limit to result for proper pagination handling
        if limit is not None:
            result["limit"] = limit
            
        logger.info("Scan returned %d items, has_more=%s", len(result["items"]), result["has_more"])
        return result
        
    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def scan_table(self) -> List[Dict]:
        """Scan the entire table and return all items (no pagination)"""
        logger.info("Scanning entire table: %s", self.table_name)
        response = self.table.scan()
        items = response.get("Items", [])
        
        # Handle pagination for large tables
        while "LastEvaluatedKey" in response:
            response = self.table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))
        
        logger.info("Scan returned %d items total", len(items))
        return items

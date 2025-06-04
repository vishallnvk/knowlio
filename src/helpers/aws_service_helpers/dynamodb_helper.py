import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import Dict, List
import botocore.exceptions

from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.common_helper import Retry

logger = LoggerHelper(__name__).get_logger()


class DynamoDBHelper:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def put_item(self, item: Dict) -> None:
        logger.info("Putting item into DynamoDB: %s", item)
        self.table.put_item(Item=item)

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def get_item(self, key: Dict) -> Dict:
        logger.info("Getting item with key: %s", key)
        response = self.table.get_item(Key=key)
        return response.get("Item")

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def update_item(self, key_name: str, key_value: str, updates: Dict) -> Dict:
        update_expression = "SET " + ", ".join(f"#{k}=:{k}" for k in updates)
        expression_attr_names = {f"#{k}": k for k in updates}
        expression_attr_values = {f":{k}": v for k, v in updates.items()}

        logger.info("Updating item in DynamoDB")
        response = self.table.update_item(
            Key={key_name: key_value},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attr_names,
            ExpressionAttributeValues=expression_attr_values,
            ReturnValues="ALL_NEW"
        )
        return response.get("Attributes")

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
                result["has_more"] = True
            else:
                result["has_more"] = False
                
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
            result["has_more"] = True
        else:
            result["has_more"] = False
            
        logger.info("Scan returned %d items", len(result["items"]))
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

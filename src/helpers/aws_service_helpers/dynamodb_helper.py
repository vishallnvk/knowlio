import boto3
from boto3.dynamodb.conditions import Key, Attr
from typing import Dict, List

from helpers.common_helper.logger_helper import LoggerHelper

logger = LoggerHelper(__name__).get_logger()


class DynamoDBHelper:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def put_item(self, item: Dict) -> None:
        logger.info("Putting item into DynamoDB: %s", item)
        self.table.put_item(Item=item)

    def get_item(self, key: Dict) -> Dict:
        logger.info("Getting item with key: %s", key)
        response = self.table.get_item(Key=key)
        return response.get("Item")

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

    def query_items(self, key_name: str, key_value: str) -> List[Dict]:
        logger.info("Querying items where %s = %s", key_name, key_value)
        try:
            response = self.table.query(
                IndexName=f"{key_name}-index",  # assumes GSI is defined as `${key_name}-index`
                KeyConditionExpression=Key(key_name).eq(key_value)
            )
            logger.info("Query succeeded using GSI")
            return response.get("Items", [])
        except Exception as e:
            logger.warning("GSI not found for %s. Falling back to scan. Error: %s", key_name, e)
            # fallback: full table scan
            response = self.table.scan(
                FilterExpression=Attr(key_name).eq(key_value)
            )
            logger.info("Scan returned %d items", len(response.get("Items", [])))
            return response.get("Items", [])

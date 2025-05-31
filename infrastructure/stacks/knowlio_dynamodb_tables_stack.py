from aws_cdk import Stack
from constructs import Construct
from aws_cdk import aws_dynamodb as dynamodb

from infrastructure.app_constructs.dynamodb_construct import DynamoDBTableConstruct, DynamoDBTableProps


class DynamoDBStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Users Table
        user_table = DynamoDBTableConstruct(
            self, "UserTable",
            DynamoDBTableProps(
                table_name="users",
                partition_key_name="user_id",
                partition_key_type=dynamodb.AttributeType.STRING
            )
        )

        # Content Table
        content_table = DynamoDBTableConstruct(
            self, "ContentTable",
            DynamoDBTableProps(
                table_name="content",
                partition_key_name="content_id",
                partition_key_type=dynamodb.AttributeType.STRING
            )
        )

        self.user_table = user_table.table
        self.content_table = content_table.table

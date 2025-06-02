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

        # License Table
        license_table = DynamoDBTableConstruct(
            self, "LicenseTable",
            DynamoDBTableProps(
                table_name="licenses",
                partition_key_name="license_id",
                partition_key_type=dynamodb.AttributeType.STRING
            )
        )

        # Usage Logs Table
        usage_logs_table = DynamoDBTableConstruct(
            self, "UsageLogsTable",
            DynamoDBTableProps(
                table_name="usage_logs",
                partition_key_name="log_id",
                partition_key_type=dynamodb.AttributeType.STRING
            )
        )

        self.user_table = user_table.table
        self.content_table = content_table.table
        self.license_table = license_table.table
        self.usage_logs_table = usage_logs_table.table

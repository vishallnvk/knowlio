from aws_cdk import Stack
from constructs import Construct
from aws_cdk import aws_dynamodb as dynamodb

from infrastructure.app_constructs.dynamodb_construct import DynamoDBTableConstruct, DynamoDBTableProps


class DynamoDBStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # Users Table with GSIs for role-based and email-based queries
        user_table_props = DynamoDBTableProps(
            table_name="users",
            partition_key_name="user_id",
            partition_key_type=dynamodb.AttributeType.STRING
        )
        
        user_table = DynamoDBTableConstruct(
            self, "UserTable",
            user_table_props
        )
        
        # Add GSI for querying users by role
        user_table.table.add_global_secondary_index(
            index_name="role-index",
            partition_key=dynamodb.Attribute(name="role", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        # Add GSI for querying users by email
        user_table.table.add_global_secondary_index(
            index_name="email-index",
            partition_key=dynamodb.Attribute(name="email", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # Content Table with GSIs for efficient queries
        content_table_props = DynamoDBTableProps(
            table_name="content",
            partition_key_name="content_id",
            partition_key_type=dynamodb.AttributeType.STRING
        )
        
        content_table = DynamoDBTableConstruct(
            self, "ContentTable",
            content_table_props
        )
        
        # Add GSI for querying content by publisher_id
        content_table.table.add_global_secondary_index(
            index_name="publisher_id-index",
            partition_key=dynamodb.Attribute(name="publisher_id", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        # Add GSI for querying content by type
        content_table.table.add_global_secondary_index(
            index_name="type-index",
            partition_key=dynamodb.Attribute(name="type", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        # Add GSI for querying content by status
        content_table.table.add_global_secondary_index(
            index_name="status-index",
            partition_key=dynamodb.Attribute(name="status", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
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

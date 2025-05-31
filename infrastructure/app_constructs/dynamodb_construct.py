
from aws_cdk import (
    aws_dynamodb as dynamodb,
    RemovalPolicy,
)

from typing import Optional

from constructs import Construct


class DynamoDBTableProps:
    def __init__(
        self,
        table_name: str,
        partition_key_name: str,
        partition_key_type: dynamodb.AttributeType,
        sort_key_name: Optional[str] = None,
        sort_key_type: Optional[dynamodb.AttributeType] = None,
        billing_mode: dynamodb.BillingMode = dynamodb.BillingMode.PAY_PER_REQUEST,
        removal_policy: RemovalPolicy = RemovalPolicy.RETAIN,  # Use RETAIN for prod
    ):
        self.table_name = table_name
        self.partition_key_name = partition_key_name
        self.partition_key_type = partition_key_type
        self.sort_key_name = sort_key_name
        self.sort_key_type = sort_key_type
        self.billing_mode = billing_mode
        self.removal_policy = removal_policy


class DynamoDBTableConstruct(Construct):
    def __init__(self, scope: Construct, id: str, props: DynamoDBTableProps) -> None:
        super().__init__(scope, id)

        table_args = {
            "partition_key": dynamodb.Attribute(
                name=props.partition_key_name,
                type=props.partition_key_type,
            ),
            "table_name": props.table_name,
            "billing_mode": props.billing_mode,
            "removal_policy": props.removal_policy,
        }

        if props.sort_key_name and props.sort_key_type:
            table_args["sort_key"] = dynamodb.Attribute(
                name=props.sort_key_name,
                type=props.sort_key_type,
            )

        self.table = dynamodb.Table(self, "DynamoDBTable", **table_args)
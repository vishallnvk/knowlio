from aws_cdk import Stack, aws_iam as iam
from constructs import Construct

from infrastructure.app_constructs.iam_role_construct import IamRole
from infrastructure.app_constructs.lambda_construct import LambdaFunctionConstructProps, LambdaConstruct


class KnowlioStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Create IAM Role for Lambda
        lambda_role = IamRole(
            self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBFullAccess"),  # Or restrict more later
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchFullAccess"),
            ],
            description="Role for Lambda to access DynamoDB, CloudWatch and Lambda invoke"
        ).role

        # Create Lambda using LambdaConstruct
        lambda_props = LambdaFunctionConstructProps(
            id="SyncHandler",
            handler="handlers.synchronous_lambda_handler.lambda_handler",
            code_path="src",
            timeout_seconds=900,  # 15 minutes
            lambda_role=lambda_role,
        )

        lambda_fn = LambdaConstruct(self, "SyncHandlerConstruct", lambda_props)

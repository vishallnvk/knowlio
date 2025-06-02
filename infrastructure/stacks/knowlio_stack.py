from aws_cdk import Stack, aws_iam as iam, CfnOutput
from constructs import Construct

from infrastructure.app_constructs.iam_role_construct import IamRole
from infrastructure.app_constructs.lambda_construct import LambdaFunctionConstructProps, LambdaConstruct
from infrastructure.app_constructs.api_gateway_construct import ApiGatewayConstruct
from infrastructure.config.knowlio_api_config import KnowlioApiConfig


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
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),  # For analytics exports
            ],
            description="Role for Lambda to access DynamoDB, CloudWatch, S3 and Lambda invoke"
        ).role

        # Create Lambda using LambdaConstruct
        lambda_props = LambdaFunctionConstructProps(
            id="SyncHandler",
            handler="handlers.api_gateway_handler.lambda_handler",
            code_path="src",
            timeout_seconds=900,  # 15 minutes
            lambda_role=lambda_role,
        )

        lambda_fn = LambdaConstruct(self, "SyncHandlerConstruct", lambda_props)
        
        # Get Knowlio-specific API configuration
        api_props = KnowlioApiConfig.get_api_gateway_props()
        api_routes = KnowlioApiConfig.get_route_definitions()
        
        # Create API Gateway with generic construct
        api_gateway = ApiGatewayConstruct(
            self, "KnowlioApiGateway",
            lambda_function=lambda_fn.lambda_function,
            props=api_props,
            routes=api_routes
        )
        
        # Output the API URL
        CfnOutput(
            self, "ApiUrl",
            value=api_gateway.api_url,
            description="Knowlio REST API Gateway URL",
            export_name="KnowlioApiUrl"
        )
        
        # Store references for potential cross-stack usage
        self.lambda_function = lambda_fn.lambda_function
        self.api_gateway = api_gateway.api
        self.api_url = api_gateway.api_url

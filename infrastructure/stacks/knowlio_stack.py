from aws_cdk import Stack, aws_iam as iam, CfnOutput, aws_cognito as cognito, Fn, RemovalPolicy
from constructs import Construct

from infrastructure.app_constructs.iam_role_construct import IamRole
from infrastructure.app_constructs.lambda_construct import LambdaFunctionConstructProps, LambdaConstruct
from infrastructure.app_constructs.api_gateway_construct import ApiGatewayConstruct
from infrastructure.config.knowlio_api_config import KnowlioApiConfig


class KnowlioStack(Stack):
    """
    Main Knowlio application stack containing Lambda and API Gateway
    that references other stacks like Auth and OpenSearch Serverless.
    """
    
    def __init__(self, scope: Construct, construct_id: str, auth_stack=None, opensearch_stack=None, **kwargs):
        """
        Initialize the KnowlioStack with references to external stacks
        
        Args:
            scope: Parent construct scope
            construct_id: Construct ID
            auth_stack: Optional reference to the AuthStack
            opensearch_stack: Required reference to the OpenSearchServerlessStack
            **kwargs: Additional keyword arguments for the Stack
        """
        super().__init__(scope, construct_id, **kwargs)
        
        # Verify opensearch_stack is provided
        if not opensearch_stack:
            raise ValueError("opensearch_stack parameter is required")

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
        
        # Use the opensearch_stack resources instead of creating our own
        opensearch_collection_arn = opensearch_stack.collection_arn
        opensearch_collection_endpoint = opensearch_stack.collection_endpoint
        opensearch_collection_name = opensearch_stack.collection_name
        
        # Update Lambda role permissions to access OpenSearch Serverless
        opensearch_policy = iam.PolicyStatement(
            actions=[
                "aoss:APIAccessAll",  # Allows all API operations on the collection
                "aoss:DashboardsAccessAll"  # Allows access to OpenSearch Dashboards
            ],
            resources=[opensearch_collection_arn]
        )
        
        lambda_role.add_to_policy(opensearch_policy)
        
        # Create environment variables for Lambda to access OpenSearch Serverless
        opensearch_env = {
            "OPENSEARCH_ENDPOINT": opensearch_collection_endpoint,
            "OPENSEARCH_COLLECTION_NAME": opensearch_collection_name,
            "OPENSEARCH_INDEX_NAME": "content-index",  # Main index for content searching
            "OPENSEARCH_REGION": self.region,
            "OPENSEARCH_SERVERLESS": "true"  # Flag to indicate we're using serverless
        }

        # Create Lambda using LambdaConstruct with OpenSearch environment variables
        lambda_props = LambdaFunctionConstructProps(
            id="SyncHandler",
            handler="handlers.api_gateway_handler.lambda_handler",
            code_path="src",
            timeout_seconds=900,  # 15 minutes
            lambda_role=lambda_role,
            environment=opensearch_env
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

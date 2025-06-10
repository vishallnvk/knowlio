"""
Generic API Gateway construct for creating REST APIs with direct service integrations.
Pure infrastructure wrapper without business logic.
"""

from aws_cdk import (
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    aws_cognito as cognito,
    aws_iam as iam,
    Duration,
)
from constructs import Construct
from typing import List, Dict, Optional, Union
from dataclasses import dataclass


@dataclass
class ApiGatewayProps:
    """Configuration properties for API Gateway"""
    api_name: str
    description: str
    stage_name: str = "prod"
    throttling_rate_limit: int = 1000
    throttling_burst_limit: int = 2000
    cors_allow_origins: List[str] = None
    cors_allow_methods: List[str] = None
    cors_allow_headers: List[str] = None
    cors_allow_credentials: bool = True

    def __post_init__(self):
        if self.cors_allow_origins is None:
            self.cors_allow_origins = ["*"]
        if self.cors_allow_methods is None:
            self.cors_allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        if self.cors_allow_headers is None:
            self.cors_allow_headers = [
                "Content-Type",
                "X-Amz-Date",
                "Authorization", 
                "X-Api-Key",
                "X-Amz-Security-Token",
            ]


@dataclass
class RouteDefinition:
    """Definition for a single API route"""
    method: str
    path: str
    description: Optional[str] = None
    auth_required: bool = False
    allowed_groups: Optional[List[str]] = None  # List of Cognito groups allowed to access this route


class ApiGatewayConstruct(Construct):
    """
    Generic API Gateway construct that creates a REST API with direct service integrations.
    Business logic should be provided externally.
    """
    
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        props: ApiGatewayProps,
        routes: List[RouteDefinition] = None,
        user_pool: Optional[cognito.IUserPool] = None,
        lambda_function: Optional[lambda_.Function] = None
    ) -> None:
        super().__init__(scope, construct_id)
        
        self.props = props
        self.user_pool = user_pool
        self.lambda_function = lambda_function
        
        # Create the REST API
        self.api = self._create_rest_api()
        
        # Create authorizer if user pool is provided
        self.authorizer = None
        if self.user_pool:
            self.authorizer = self._create_authorizer()
        
        # Create API Gateway role for service integrations
        self.api_gateway_role = self._create_api_gateway_role()
        
        # Create routes if provided
        if routes:
            self.add_routes(routes)
        
        # Store API URL for output
        self.api_url = self.api.url
    
    def _create_rest_api(self) -> apigateway.RestApi:
        """Create the REST API with CORS configuration"""
        return apigateway.RestApi(
            self, "RestApi",
            rest_api_name=self.props.api_name,
            description=self.props.description,
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=self.props.cors_allow_origins,
                allow_methods=self.props.cors_allow_methods,
                allow_headers=self.props.cors_allow_headers,
                allow_credentials=self.props.cors_allow_credentials
            ),
            deploy_options=apigateway.StageOptions(
                stage_name=self.props.stage_name,
                throttling_rate_limit=self.props.throttling_rate_limit,
                throttling_burst_limit=self.props.throttling_burst_limit,
            )
        )
    
    def _create_authorizer(self) -> apigateway.CognitoUserPoolsAuthorizer:
        """Create Cognito User Pools Authorizer"""
        return apigateway.CognitoUserPoolsAuthorizer(
            self, "CognitoAuthorizer",
            cognito_user_pools=[self.user_pool],
            authorizer_name=f"{self.props.api_name}-authorizer",
            identity_source="method.request.header.Authorization"
        )
    
    def _create_api_gateway_role(self) -> iam.Role:
        """Create IAM role for API Gateway service integrations"""
        role = iam.Role(
            self, "ApiGatewayServiceRole",
            assumed_by=iam.ServicePrincipal("apigateway.amazonaws.com"),
            description="Role for API Gateway to access AWS services",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonDynamoDBReadOnlyAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3ReadOnlyAccess")
            ]
        )
        
        # Add custom policies as needed for specific services
        
        return role
        
    def _create_service_integration_for_route(self, route: RouteDefinition) -> apigateway.Integration:
        """Create appropriate service integration based on route processor_name"""
        cors_response_parameters = {
            "method.response.header.Access-Control-Allow-Origin": "'*'",
            "method.response.header.Access-Control-Allow-Headers": f"'{','.join(self.props.cors_allow_headers)}'",
            "method.response.header.Access-Control-Allow-Methods": f"'{','.join(self.props.cors_allow_methods)}'"
        }
        
        # Match the route to specific service integrations based on processor_name and path patterns
        if not hasattr(route, 'processor_name'):
            processor_name = ''
        else:
            processor_name = route.processor_name
            
        # S3 integrations
        if processor_name == 's3_upload' or 'uploads' in route.path:
            if 'download' in route.path and route.method == 'GET':
                return self._create_s3_download_integration(route, cors_response_parameters)
            elif 'url' in route.path and route.method == 'POST':
                return self._create_s3_presigned_url_integration(route, cors_response_parameters)
        
        # DynamoDB integrations
        elif processor_name == 'content' or 'content' in route.path:
            if route.method == 'GET':
                return self._create_dynamodb_get_integration(route, cors_response_parameters)
            elif route.method == 'POST':
                return self._create_dynamodb_put_integration(route, cors_response_parameters)
        
        # User management integrations
        elif processor_name == 'user' or 'users' in route.path:
            return self._create_cognito_integration(route, cors_response_parameters)
        
        # For demonstration purposes, we'll use the Lambda function if it was provided
        # as a fallback for routes without specific service integration
        if self.lambda_function:
            return apigateway.LambdaIntegration(
                self.lambda_function,
                proxy=False,  # Not using proxy integration
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_parameters=cors_response_parameters
                    )
                ]
            )
            
        # Default to mock integration
        return apigateway.MockIntegration(
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_templates={
                        "application/json": '{"message": "Service integration configured for path: ' + route.path + '"}'
                    },
                    response_parameters=cors_response_parameters
                )
            ],
            request_templates={
                "application/json": '{"statusCode": 200}'
            }
        )
    
    def _create_s3_download_integration(self, route: RouteDefinition, cors_response_parameters: Dict) -> apigateway.AwsIntegration:
        """Create integration for S3 object download"""
        return apigateway.AwsIntegration(
            service="s3",
            integration_http_method="GET",
            path="bucket-name/{key}",  # Parameterized path
            options=apigateway.IntegrationOptions(
                credentials_role=self.api_gateway_role,
                request_parameters={
                    "integration.request.path.key": "method.request.path.key"
                },
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_parameters=cors_response_parameters
                    )
                ]
            )
        )
    
    def _create_s3_presigned_url_integration(self, route: RouteDefinition, cors_response_parameters: Dict) -> apigateway.AwsIntegration:
        """Create integration for generating S3 presigned URLs"""
        # For presigned URLs, we'd typically use a Lambda function since API Gateway can't 
        # directly generate these. For demonstration, we'll use a mock integration
        return apigateway.MockIntegration(
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_templates={
                        "application/json": '{"url": "https://s3-presigned-url-example.com/object?signature=xxx"}'
                    },
                    response_parameters=cors_response_parameters
                )
            ],
            request_templates={
                "application/json": '{"statusCode": 200}'
            }
        )
    
    def _create_dynamodb_get_integration(self, route: RouteDefinition, cors_response_parameters: Dict) -> apigateway.AwsIntegration:
        """Create integration for DynamoDB GetItem/Query operations"""
        # Extract parameter from path if it exists
        path_param = None
        if "{" in route.path and "}" in route.path:
            path_param = route.path[route.path.find("{")+1:route.path.find("}")]
        
        # Create appropriate request template based on the operation
        request_template = {}
        if path_param:
            # GetItem operation if we have a path parameter (like an ID)
            request_template = {
                "application/json": """
                {
                    "TableName": "KnowlioContentTable",
                    "Key": {
                        "id": {
                            "S": "$input.params('""" + path_param + """')"
                        }
                    }
                }
                """
            }
        else:
            # Query/Scan operation if we don't have a specific ID
            request_template = {
                "application/json": """
                {
                    "TableName": "KnowlioContentTable",
                    "Limit": 20
                }
                """
            }
        
        return apigateway.AwsIntegration(
            service="dynamodb",
            action="GetItem" if path_param else "Scan",
            options=apigateway.IntegrationOptions(
                credentials_role=self.api_gateway_role,
                request_templates=request_template,
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_templates={
                            "application/json": "$input.json('$')"
                        },
                        response_parameters=cors_response_parameters
                    )
                ]
            )
        )
    
    def _create_dynamodb_put_integration(self, route: RouteDefinition, cors_response_parameters: Dict) -> apigateway.AwsIntegration:
        """Create integration for DynamoDB PutItem operations"""
        return apigateway.AwsIntegration(
            service="dynamodb",
            action="PutItem",
            options=apigateway.IntegrationOptions(
                credentials_role=self.api_gateway_role,
                request_templates={
                    "application/json": """
                    {
                        "TableName": "KnowlioContentTable",
                        "Item": {
                            "id": {
                                "S": "$context.requestId"
                            },
                            "createdAt": {
                                "S": "$context.requestTime"
                            },
                            "data": {
                                "S": "$input.json('$.data')"
                            }
                        }
                    }
                    """
                },
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_templates={
                            "application/json": '{"status": "success", "id": "$context.requestId"}'
                        },
                        response_parameters=cors_response_parameters
                    )
                ]
            )
        )
    
    def _create_cognito_integration(self, route: RouteDefinition, cors_response_parameters: Dict) -> apigateway.Integration:
        """Create integration for Cognito user management operations"""
        # For user management operations, we typically need Lambda to interact with Cognito
        # For demonstration, we'll use a mock integration
        return apigateway.MockIntegration(
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_templates={
                        "application/json": '{"message": "User operation successful"}'
                    },
                    response_parameters=cors_response_parameters
                )
            ],
            request_templates={
                "application/json": '{"statusCode": 200}'
            }
        )
    
    def add_routes(self, routes: List[RouteDefinition]) -> None:
        """Add multiple routes to the API"""
        resource_cache = {}
        
        for route in routes:
            self.add_route(route, resource_cache)
    
    def add_route(self, route: RouteDefinition, resource_cache: Dict = None) -> apigateway.Resource:
        """Add a single route to the API with improved path parameter handling"""
        if resource_cache is None:
            resource_cache = {}
        
        # Build the resource hierarchy
        current_resource = self.api.root
        current_path = ""
        
        path_segments = route.path.split('/')
        
        for i, segment in enumerate(path_segments):
            if current_path:
                current_path += f"/{segment}"
            else:
                current_path = segment
            
            # Check if segment contains a path parameter
            is_path_param = segment.startswith('{') and segment.endswith('}')
            
            # Modified cache key - use position in the path to avoid conflicts
            # For path parameters, include the position to avoid conflicts with other path parameters
            cache_key = current_path if not is_path_param else f"{current_path}_pos_{i}"
            
            # Check if we already have this resource
            if cache_key not in resource_cache:
                # Create new resource
                resource_cache[cache_key] = current_resource.add_resource(
                    segment,
                    default_cors_preflight_options=apigateway.CorsOptions(
                        allow_origins=self.props.cors_allow_origins,
                        allow_methods=self.props.cors_allow_methods,
                        allow_headers=self.props.cors_allow_headers
                    )
                )
            
            current_resource = resource_cache[cache_key]
        
        # Prepare method options
        method_options = {
            "method_responses": [
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True,
                    }
                )
            ]
        }
        
        # Add authorization if required
        if route.auth_required and self.authorizer:
            method_options["authorizer"] = self.authorizer
            
            # Add authorization scopes if groups are specified
            if route.allowed_groups:
                # For Cognito groups, we'll use custom Lambda authorizer logic
                # The Lambda function will need to check the user's groups
                method_options["authorization_scopes"] = route.allowed_groups
        
        # Create appropriate integration based on the route
        integration = self._create_service_integration_for_route(route)
        
        # Add the HTTP method to the final resource
        current_resource.add_method(
            route.method,
            integration,
            **method_options
        )
        
        return current_resource
    
    def add_custom_integration(
        self, 
        method: str, 
        path: str, 
        integration: apigateway.Integration,
        auth_required: bool = False,
        allowed_groups: Optional[List[str]] = None
    ) -> apigateway.Resource:
        """Add a route with a custom integration (not Lambda)"""
        route = RouteDefinition(
            method=method, 
            path=path, 
            auth_required=auth_required,
            allowed_groups=allowed_groups
        )
        resource = self._build_resource_for_path(route.path)
        
        method_options = {}
        if auth_required and self.authorizer:
            method_options["authorizer"] = self.authorizer
            if allowed_groups:
                method_options["authorization_scopes"] = allowed_groups
                
        if integration is None:
            # If no specific integration provided, create one based on route
            integration = self._create_service_integration_for_route(
                RouteDefinition(method=method, path=path, auth_required=auth_required, allowed_groups=allowed_groups)
            )
            
        resource.add_method(method, integration, **method_options)
        return resource
    
    def _build_resource_for_path(self, path: str) -> apigateway.Resource:
        """Build resource hierarchy for a given path with improved path parameter handling"""
        current_resource = self.api.root
        path_segments = path.split('/')
        resource_cache = {}
        current_path = ""
        
        for i, segment in enumerate(path_segments):
            if current_path:
                current_path += f"/{segment}"
            else:
                current_path = segment
            
            # Check if segment contains a path parameter
            is_path_param = segment.startswith('{') and segment.endswith('}')
            
            # Modified cache key - use position in the path to avoid conflicts
            cache_key = current_path if not is_path_param else f"{current_path}_pos_{i}"
            
            # Check if we already have this resource
            if cache_key not in resource_cache:
                # Create new resource
                resource_cache[cache_key] = current_resource.add_resource(
                    segment,
                    default_cors_preflight_options=apigateway.CorsOptions(
                        allow_origins=self.props.cors_allow_origins,
                        allow_methods=self.props.cors_allow_methods,
                        allow_headers=self.props.cors_allow_headers
                    )
                )
            
            current_resource = resource_cache[cache_key]
        
        return current_resource

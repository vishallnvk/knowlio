"""
Generic API Gateway construct for creating REST APIs with Lambda integration.
Pure infrastructure wrapper without business logic.
"""

from aws_cdk import (
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
    aws_cognito as cognito,
    aws_iam as iam,
    Stack
)
from aws_cdk.aws_lambda import CfnPermission
from constructs import Construct
from typing import List, Dict, Optional
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
            self.cors_allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
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
    auth_required: bool = False  # Default to no authentication for development
    allowed_groups: Optional[List[str]] = None  # Optional list of Cognito groups that can access the route


class ApiGatewayConstruct(Construct):
    """
    Generic API Gateway construct that creates a REST API with Lambda Proxy Integration.
    Business logic should be provided externally.
    """

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            lambda_function: lambda_.Function,
            props: ApiGatewayProps,
            routes: List[RouteDefinition] = None,
            user_pool: Optional[cognito.UserPool] = None
    ) -> None:
        super().__init__(scope, construct_id)

        self.lambda_function = lambda_function
        self.props = props
        self.user_pool = user_pool

        # Create Cognito authorizer if user pool is provided
        self.authorizer = None
        if self.user_pool:
            self.authorizer = self._create_cognito_authorizer()

        # Create the REST API
        self.api = self._create_rest_api()

        # Create Lambda integration
        self.lambda_integration = self._create_lambda_integration()

        # Create routes if provided
        if routes:
            self.add_routes(routes)

        # Store API URL for output
        self.api_url = self.api.url

    def _create_cognito_authorizer(self) -> apigateway.CognitoUserPoolsAuthorizer:
        """Create a Cognito authorizer for the API Gateway"""
        return apigateway.CognitoUserPoolsAuthorizer(
            self, "CognitoAuthorizer",
            cognito_user_pools=[self.user_pool],
            authorizer_name="cognito-authorizer",
            identity_source="method.request.header.Authorization"
        )

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

    def _create_lambda_integration(self) -> apigateway.LambdaIntegration:
        class LambdaIntegrationNoPermission(apigateway.LambdaIntegration):
            def __init__(self, handler, **kwargs):
                super().__init__(handler, **kwargs)

            def bind(self, method: apigateway.Method):
                integration_config = super().bind(method)
                permissions = filter(lambda x: isinstance(x, CfnPermission), method.node.children)
                # Removing permissions policy for each integration
                for p in permissions:
                    method.node.try_remove_child(p.node.id)
                return integration_config

        """Create Lambda Proxy Integration"""
        return LambdaIntegrationNoPermission(
            self.lambda_function,
            proxy=True,
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'",
                        "method.response.header.Access-Control-Allow-Headers": f"'{','.join(self.props.cors_allow_headers)}'",
                        "method.response.header.Access-Control-Allow-Methods": f"'{','.join(self.props.cors_allow_methods)}'"
                    }
                )
            ]
        )

    def add_routes(self, routes: List[RouteDefinition]) -> None:
        """
        Add multiple routes to the API.
        Optimizes permissions by reducing individual Lambda permissions.
        """
        # Create a resource cache to avoid duplicate resources
        resource_cache = {}

        # First, add a resource policy to allow API Gateway to invoke Lambda
        # instead of creating individual Lambda permissions for each method
        # This significantly reduces policy size
        self.lambda_function.add_permission(
            "AllowApiGatewayInvoke",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:execute-api:{Stack.of(self).region}:{Stack.of(self).account}:{self.api.rest_api_id}/*/*/*"
            # Allow all methods and paths
        )

        # Add routes with shared Lambda permission
        for route in routes:
            self.add_route(route, resource_cache)

    def add_route(self, route: RouteDefinition, resource_cache: Dict = None) -> apigateway.Resource:
        """Add a single route to the API"""
        if resource_cache is None:
            resource_cache = {}

        # Build the resource hierarchy
        current_resource = self.api.root
        current_path = ""

        path_segments = route.path.split('/')

        for segment in path_segments:
            if current_path:
                current_path += f"/{segment}"
            else:
                current_path = segment

            # Check if we already have this resource
            if current_path not in resource_cache:
                # Create new resource
                resource_cache[current_path] = current_resource.add_resource(
                    segment,
                    default_cors_preflight_options=apigateway.CorsOptions(
                        allow_origins=self.props.cors_allow_origins,
                        allow_methods=self.props.cors_allow_methods,
                        allow_headers=self.props.cors_allow_headers
                    )
                )

            current_resource = resource_cache[current_path]

        # Add the HTTP method to the final resource
        # Note: We've simplified the system by optimizing routes in knowlio_api_config.py
        # This uses fewer unique paths with wildcards to keep policy size small

        # Set up method options
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

        # Apply authorization if required and authorizer exists
        # Only use Cognito authorizer for token validation, not for group-based access control
        if route.auth_required and self.authorizer:
            method_options["authorization_type"] = apigateway.AuthorizationType.COGNITO
            method_options["authorizer"] = self.authorizer

            # NOTE: We don't use authorization_scopes for Cognito groups
            # Groups-based authorization will be handled in Lambda using cognito_helper.py

        # Add the method with appropriate authorization
        current_resource.add_method(
            route.method,
            self.lambda_integration,
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

        # Set up method options
        method_options = {}

        # Apply authorization if required and authorizer exists
        if auth_required and self.authorizer:
            method_options["authorization_type"] = apigateway.AuthorizationType.COGNITO
            method_options["authorizer"] = self.authorizer

            # NOTE: We don't use authorization_scopes for Cognito groups
            # Groups-based authorization will be handled in Lambda using cognito_helper.py

        # Add the method with appropriate authorization
        resource.add_method(method, integration, **method_options)
        return resource

    def _build_resource_for_path(self, path: str) -> apigateway.Resource:
        """Build resource hierarchy for a given path"""
        current_resource = self.api.root

        # Split the path and filter out empty segments
        path_segments = [seg for seg in path.split('/') if seg]

        # Use the same algorithm as add_route for path parameters
        resource_cache = {}
        current_path = ""

        for i, segment in enumerate(path_segments):
            if current_path:
                current_path += f"/{segment}"
            else:
                current_path = segment

            # Check if this is a path parameter segment {param}
            is_param = segment.startswith('{') and segment.endswith('}')

            # Create a unique cache key that differentiates between path parameters at the same level
            cache_key = current_path
            if is_param:
                param_name = segment[1:-1]  # Extract name without braces
                position_key = f"{current_path}__param_{i}"
                cache_key = position_key

            # Check if we already have this resource
            if cache_key not in resource_cache:
                # For path parameters, use a consistent resource ID
                if is_param:
                    segment = f"{{{param_name}}}"

                resource_cache[cache_key] = current_resource.add_resource(segment)

            current_resource = resource_cache[cache_key]

        return current_resource

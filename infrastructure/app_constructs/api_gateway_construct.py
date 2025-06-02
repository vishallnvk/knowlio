"""
Generic API Gateway construct for creating REST APIs with Lambda integration.
Pure infrastructure wrapper without business logic.
"""

from aws_cdk import (
    aws_apigateway as apigateway,
    aws_lambda as lambda_,
)
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
        routes: List[RouteDefinition] = None
    ) -> None:
        super().__init__(scope, construct_id)
        
        self.lambda_function = lambda_function
        self.props = props
        
        # Create the REST API
        self.api = self._create_rest_api()
        
        # Create Lambda integration
        self.lambda_integration = self._create_lambda_integration()
        
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
    
    def _create_lambda_integration(self) -> apigateway.LambdaIntegration:
        """Create Lambda Proxy Integration"""
        return apigateway.LambdaIntegration(
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
        """Add multiple routes to the API"""
        resource_cache = {}
        
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
        current_resource.add_method(
            route.method,
            self.lambda_integration,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True,
                    }
                )
            ]
        )
        
        return current_resource
    
    def add_custom_integration(
        self, 
        method: str, 
        path: str, 
        integration: apigateway.Integration
    ) -> apigateway.Resource:
        """Add a route with a custom integration (not Lambda)"""
        route = RouteDefinition(method=method, path=path)
        resource = self._build_resource_for_path(route.path)
        resource.add_method(method, integration)
        return resource
    
    def _build_resource_for_path(self, path: str) -> apigateway.Resource:
        """Build resource hierarchy for a given path"""
        current_resource = self.api.root
        path_segments = path.split('/')
        
        for segment in path_segments:
            current_resource = current_resource.add_resource(segment)
        
        return current_resource

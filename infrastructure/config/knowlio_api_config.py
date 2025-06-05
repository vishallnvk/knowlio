"""
Knowlio-specific API Gateway configuration.
Business logic for setting up the Knowlio REST API using the generic API Gateway construct.
"""

from typing import List
from infrastructure.app_constructs.api_gateway_construct import ApiGatewayProps, RouteDefinition
from infrastructure.config.api_routes import KnowlioApiRoutes


class KnowlioApiConfig:
    """Configuration builder for Knowlio REST API"""
    
    @staticmethod
    def get_api_gateway_props() -> ApiGatewayProps:
        """Get API Gateway properties for Knowlio"""
        return ApiGatewayProps(
            api_name="KnowlioAPI",
            description="Knowlio REST API for content licensing and analytics",
            stage_name="prod",
            throttling_rate_limit=1000,
            throttling_burst_limit=2000,
            # Use defaults for CORS settings
        )
    
    @staticmethod
    def get_route_definitions() -> List[RouteDefinition]:
        """Convert KnowlioApiRoutes to generic RouteDefinition format."""
        knowlio_routes = KnowlioApiRoutes.get_all_routes()
        
        # Group common routes by method to reduce IAM policy size
        # Use method-based grouping instead of path wildcards since API Gateway doesn't allow * in paths
        route_definitions = []
        processed_paths = set()
        
        # First pass: Add routes with greedy path parameters where possible
        # API Gateway allows {proxy+} for greedy path parameters
        for path_base in ["users", "content", "licenses", "analytics", "books", "uploads"]:
            # Add base path with greedy parameter for each HTTP method
            for method in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                # Check if any route matches this pattern
                has_matching_routes = False
                for route in knowlio_routes:
                    if route.path.startswith(f"{path_base}/") and route.method == method:
                        has_matching_routes = True
                        break
                
                if has_matching_routes:
                    # Add a greedy route for this base path and method
                    route_def = RouteDefinition(
                        method=method,
                        # Use API Gateway's greedy path parameter syntax
                        path=f"{path_base}/{{proxy+}}",
                        description=f"{method} requests for {path_base}"
                    )
                    route_definitions.append(route_def)
                    # Mark all matching routes as processed
                    for route in knowlio_routes:
                        if route.path.startswith(f"{path_base}/") and route.method == method:
                            processed_paths.add(f"{route.method}:{route.path}")
        
        # Second pass: Add any routes that weren't covered by greedy paths
        for route in knowlio_routes:
            route_key = f"{route.method}:{route.path}"
            if route_key not in processed_paths:
                route_def = RouteDefinition(
                    method=route.method,
                    path=route.path,
                    description=route.description
                )
                route_definitions.append(route_def)
                processed_paths.add(route_key)
        
        return route_definitions
    
    @staticmethod
    def get_routes_by_category():
        """Get routes organized by category for documentation/debugging"""
        all_routes = KnowlioApiRoutes.get_all_routes()
        
        categories = {
            "user": [],
            "content": [],
            "license": [],
            "analytics": []
        }
        
        for route in all_routes:
            if route.processor_name in categories:
                categories[route.processor_name].append({
                    "method": route.method,
                    "path": route.path,
                    "action": route.action,
                    "description": route.description
                })
        
        return categories
    
    @staticmethod
    def get_api_summary():
        """Get a summary of the API for logging/documentation"""
        routes = KnowlioApiRoutes.get_all_routes()
        
        summary = {
            "total_routes": len(routes),
            "methods": {},
            "processors": {},
        }
        
        for route in routes:
            # Count methods
            summary["methods"][route.method] = summary["methods"].get(route.method, 0) + 1
            
            # Count processors
            summary["processors"][route.processor_name] = summary["processors"].get(route.processor_name, 0) + 1
        
        return summary

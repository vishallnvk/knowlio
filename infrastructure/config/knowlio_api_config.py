"""
Knowlio-specific API Gateway configuration.
Business logic for setting up the Knowlio REST API using the generic API Gateway construct.
"""

from typing import List
from infrastructure.app_constructs.api_gateway_construct import ApiGatewayProps, RouteDefinition
from src.config.api_routes import KnowlioApiRoutes


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
        """Convert KnowlioApiRoutes to generic RouteDefinition format"""
        knowlio_routes = KnowlioApiRoutes.get_all_routes()
        
        route_definitions = []
        for route in knowlio_routes:
            route_def = RouteDefinition(
                method=route.method,
                path=route.path,
                description=route.description
            )
            route_definitions.append(route_def)
        
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

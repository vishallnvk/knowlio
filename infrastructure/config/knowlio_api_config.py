"""
Knowlio-specific API Gateway configuration.
Business logic for setting up the Knowlio REST API using the generic API Gateway construct.
"""

from typing import List
from infrastructure.app_constructs.api_gateway_construct import ApiGatewayProps, RouteDefinition
import sys
import os

# Add src directory to path to access src/config/api_routes.py
src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Import from src/config directory
from config.api_routes import KnowlioApiRoutes


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
        """Convert KnowlioApiRoutes to generic RouteDefinition format with authentication."""
        knowlio_routes = KnowlioApiRoutes.get_all_routes()
        
        route_definitions = []
        
        # Convert each KnowlioApiRoute to RouteDefinition
        for route in knowlio_routes:
            route_def = RouteDefinition(
                method=route.method,
                path=route.path,
                description=route.description,
                auth_required=route.auth_required,
                allowed_groups=route.allowed_groups
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
            "analytics": [],
            "google_books": [],
            "s3_upload": []
        }
        
        for route in all_routes:
            if route.processor_name in categories:
                categories[route.processor_name].append({
                    "method": route.method,
                    "path": route.path,
                    "action": route.action,
                    "description": route.description,
                    "auth_required": route.auth_required,
                    "allowed_groups": route.allowed_groups
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
            "auth_required_routes": 0,
            "public_routes": 0,
            "group_restricted_routes": {}
        }
        
        for route in routes:
            # Count methods
            summary["methods"][route.method] = summary["methods"].get(route.method, 0) + 1
            
            # Count processors
            summary["processors"][route.processor_name] = summary["processors"].get(route.processor_name, 0) + 1
            
            # Count auth requirements
            if route.auth_required:
                summary["auth_required_routes"] += 1
            else:
                summary["public_routes"] += 1
            
            # Count group restrictions
            if route.allowed_groups:
                for group in route.allowed_groups:
                    summary["group_restricted_routes"][group] = summary["group_restricted_routes"].get(group, 0) + 1
        
        return summary
    
    @staticmethod
    def get_group_permissions_summary():
        """Get a summary of which routes each group can access"""
        groups = ["Admin", "Publisher", "Consumer"]
        permissions = {}
        
        for group in groups:
            accessible_routes = KnowlioApiRoutes.get_routes_by_group(group)
            permissions[group] = {
                "total_accessible_routes": len(accessible_routes),
                "routes": [f"{route.method} {route.path}" for route in accessible_routes]
            }
        
        # Add unauthenticated routes
        public_routes = [route for route in KnowlioApiRoutes.get_all_routes() if not route.auth_required]
        permissions["Unauthenticated"] = {
            "total_accessible_routes": len(public_routes),
            "routes": [f"{route.method} {route.path}" for route in public_routes]
        }
        
        return permissions

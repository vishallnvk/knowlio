"""
API Gateway authentication interceptor for Cognito authorization.
Provides a middleware layer for handling authentication and group-based authorization
before executing business logic in processor functions.

This implements the "Layered Architecture" pattern recommended by AWS.
"""

import json
import logging
from typing import Dict, Any, Callable, List, Optional, Tuple

from helpers.common_helper.cognito_helper import (
    get_user_details_from_event,
    validate_user_access
)

# Configure logger
logger = logging.getLogger(__name__)

class AuthInterceptor:
    """
    Authentication and authorization interceptor for API Gateway requests.
    Implements the middleware pattern to intercept requests before they reach business logic.
    """
    
    @staticmethod
    def intercept_request(
        event: Dict[str, Any],
        context: Any,
        handler_func: Callable,
        required_groups: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Intercept API Gateway event, validate auth, and call handler if authorized.
        
        Args:
            event: API Gateway event
            context: Lambda context
            handler_func: Handler function to call if auth passes
            required_groups: Optional list of Cognito groups that can access this endpoint
            
        Returns:
            API Gateway response dictionary with status code, headers, and body
        """
        try:
            # Extract user details from the event
            user_details = get_user_details_from_event(event)
            
            # Log user information
            if user_details['authenticated']:
                logger.info(f"Authenticated user: {user_details['email']} in groups: {user_details['groups']}")
            else:
                logger.info("Unauthenticated request")
            
            # Validate user access based on required groups
            has_access, message = validate_user_access(user_details, required_groups)
            
            # If user does not have access, return 403 Forbidden response
            if not has_access:
                logger.warning(f"Access denied: {message}")
                return _http_response(403, {"error": "Forbidden", "message": message})
            
            # Add user details to event for downstream handlers
            event['userData'] = user_details
            
            # Call the original handler function
            return handler_func(event, context)
        
        except Exception as e:
            logger.exception(f"Error in auth interceptor: {str(e)}")
            return _http_response(500, {"error": "Internal server error", "message": str(e)})


def with_auth(required_groups: Optional[List[str]] = None) -> Callable:
    """
    Decorator for Lambda handlers that require authentication.
    
    Usage:
        @with_auth(required_groups=['Admin', 'Publisher'])
        def my_handler(event, context):
            # This will only run if auth passes
            return {"statusCode": 200, "body": "Success"}
    
    Args:
        required_groups: Optional list of groups that can access this endpoint.
                        If None, any authenticated user can access.
                        
    Returns:
        Decorated handler function with auth check
    """
    def decorator(handler_func: Callable) -> Callable:
        def wrapper(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
            return AuthInterceptor.intercept_request(
                event,
                context,
                handler_func,
                required_groups
            )
        return wrapper
    return decorator


def authorize_route(
    event: Dict[str, Any],
    required_groups: Optional[List[str]] = None
) -> Tuple[bool, Optional[Dict], Dict]:
    """
    Authorize a route based on user groups without decorating the entire function.
    Used for more granular control of authorization within a single handler.
    
    Args:
        event: API Gateway event
        required_groups: Optional list of groups that can access this endpoint
        
    Returns:
        Tuple of (authorized: bool, response: Optional[Dict], user_details: Dict)
        - If authorized, response will be None and user_details will contain the user info
        - If not authorized, response will contain a 403 error response and user_details will be empty
    """
    # Extract user details
    user_details = get_user_details_from_event(event)
    
    # Validate user access
    has_access, message = validate_user_access(user_details, required_groups)
    
    if not has_access:
        # Return unauthorized tuple
        return False, _http_response(403, {"error": "Forbidden", "message": message}), user_details
    
    # Return authorized tuple
    return True, None, user_details


def _http_response(status_code: int, body: Any) -> Dict[str, Any]:
    """Create HTTP response with CORS headers"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        },
        "body": json.dumps(body, default=str)
    }

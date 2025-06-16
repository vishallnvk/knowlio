"""
Example Lambda handler demonstrating how to use Cognito authentication in API Gateway.
This shows the recommended approach for handling group-based access control in Lambda
rather than using API Gateway's authorization_scopes.
"""

import json
import logging
from typing import Dict, Any

# Import the Cognito helper utilities
from helpers.common_helper.cognito_helper import (
    get_user_details_from_event,
    validate_user_access
)

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Example Lambda handler
def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Example Lambda handler with Cognito authentication and group-based access control.
    
    Args:
        event: API Gateway Lambda proxy event
        context: Lambda context
        
    Returns:
        API Gateway response object
    """
    # Log the event for debugging
    logger.info("Received event: %s", json.dumps(event))
    
    try:
        # 1. Extract user details from the JWT token (already validated by API Gateway)
        user_details = get_user_details_from_event(event)
        
        # 2. Determine which resource/method is being accessed
        # In a real implementation, you'd likely use a more sophisticated routing approach
        path = event.get('path', '')
        method = event.get('httpMethod', '')
        
        logger.info(f"Request: {method} {path}")
        logger.info(f"User authenticated: {user_details['authenticated']}")
        logger.info(f"User groups: {user_details['groups']}")
        
        # 3. Define access control based on path and method
        required_groups = None  # Default: no specific groups required if authenticated
        
        # Example access control rules
        if 'content' in path:
            required_groups = ['Admin', 'Publisher']
        elif 'analytics' in path:
            required_groups = ['Admin', 'Publisher']
        elif 'admin' in path:
            required_groups = ['Admin']
        
        # 4. Validate user access based on group membership
        if required_groups:
            has_access, message = validate_user_access(user_details, required_groups)
            
            # 5. Return 403 Forbidden if the user doesn't have the required group membership
            if not has_access:
                return {
                    'statusCode': 403,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': message})
                }
            
            logger.info(f"Access granted to {path} for user in groups: {user_details['groups']}")
        
        # 6. Process the request (your actual business logic here)
        # ...
        
        # 7. Return the response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'Success',
                'user': {
                    'id': user_details['user_id'],
                    'email': user_details['email'],
                    'groups': user_details['groups']
                },
                'access': {
                    'path': path,
                    'method': method,
                    'required_groups': required_groups
                }
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }


# Example more complex handler with role-based permissions
def advanced_lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Advanced example with more sophisticated access control logic.
    This demonstrates a more complete approach to permission mapping.
    
    Args:
        event: API Gateway Lambda proxy event
        context: Lambda context
        
    Returns:
        API Gateway response object
    """
    try:
        # Extract user details
        user_details = get_user_details_from_event(event)
        
        # Extract path and method
        path = event.get('path', '')
        method = event.get('httpMethod', '')
        
        # Map of endpoints to required groups
        permission_map = {
            # Content endpoints
            '/content/metadata/upload': ['Admin', 'Publisher'],
            '/content/id/': ['Admin', 'Publisher', 'Consumer'],  # Path prefix for content viewing
            '/content/search/query': ['Admin'],
            
            # Analytics endpoints
            '/analytics/access/log': ['Admin', 'Publisher', 'Consumer'],
            '/analytics/reports/': ['Admin', 'Publisher'],
            
            # License endpoints
            '/licenses/': ['Admin', 'Publisher', 'Consumer'],
            
            # User management endpoints
            '/users/profile': ['Admin', 'Publisher', 'Consumer'],  # View own profile
            '/admin/users/': ['Admin']  # Admin-only user management
        }
        
        # Determine required groups for this request
        required_groups = None
        
        # Check for exact match first
        if path in permission_map:
            required_groups = permission_map[path]
        else:
            # Check for prefix match
            for prefix, groups in permission_map.items():
                if path.startswith(prefix):
                    required_groups = groups
                    break
        
        # Validate access if groups are required
        if required_groups:
            has_access, message = validate_user_access(user_details, required_groups)
            
            if not has_access:
                return {
                    'statusCode': 403,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': message})
                }
        
        # Process the request (actual business logic here)
        # ...
        
        # Return success response
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'message': 'Access granted'})
        }
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': str(e)})
        }

"""
Helper functions for Cognito authentication in Lambda functions.
Provides utilities to extract and validate user details from Cognito tokens.
"""

import os
import json
import logging
import boto3
from typing import Dict, List, Optional, Union, Tuple
from botocore.exceptions import ClientError

# Configure logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
USER_POOL_ID = os.environ.get('USER_POOL_ID')
USER_POOL_CLIENT_ID = os.environ.get('USER_POOL_CLIENT_ID')
COGNITO_REGION = os.environ.get('COGNITO_REGION')
COGNITO_AUTH_ENABLED = os.environ.get('COGNITO_AUTH_ENABLED', 'false').lower() == 'true'


def get_user_details_from_event(event: Dict) -> Dict:
    """
    Extract user details from API Gateway event after Cognito authorization.
    
    The function extracts claims from the JWT token that was validated by the
    API Gateway Cognito authorizer. These claims include user ID, email, groups,
    and other attributes from the token.
    
    Args:
        event: API Gateway Lambda proxy event
        
    Returns:
        Dictionary containing user details from Cognito claims
    """
    user_details = {
        'user_id': None,
        'email': None,
        'first_name': None,
        'last_name': None,
        'name': None,
        'groups': [],
        'authenticated': False,
        'claims': {}
    }
    
    # Check if authentication is enabled and authorizer is present
    if not COGNITO_AUTH_ENABLED:
        logger.info("Cognito authentication is disabled")
        return user_details
        
    # Extract claims from event
    try:
        if ('requestContext' in event and 
            'authorizer' in event['requestContext'] and 
            'claims' in event['requestContext']['authorizer']):
            
            claims = event['requestContext']['authorizer']['claims']
            
            # Extract basic user information
            user_details['user_id'] = claims.get('sub')
            user_details['email'] = claims.get('email')
            user_details['authenticated'] = True
            user_details['claims'] = claims
            
            # Extract name information from Cognito claims
            user_details['first_name'] = claims.get('given_name', '')
            user_details['last_name'] = claims.get('family_name', '')
            
            # Compute full name from first and last names
            if user_details['first_name'] or user_details['last_name']:
                user_details['name'] = f"{user_details['first_name']} {user_details['last_name']}".strip()
            else:
                # Fallback to name claim if available
                user_details['name'] = claims.get('name', '')
            
            # Extract groups - could be a string or list depending on number of groups
            groups = claims.get('cognito:groups', '')
            if isinstance(groups, str):
                if groups:  # Non-empty string - single group
                    user_details['groups'] = [item.strip() for item in groups.split(',')]
            else:  # Already a list
                user_details['groups'] = groups
                
            logger.info(f"Extracted user details from token: {user_details['email']} ({user_details['name']}) with groups {user_details['groups']}")
            
    except Exception as e:
        logger.error(f"Error extracting user details from event: {str(e)}")
        
    return user_details


def validate_user_access(user_details: Dict, required_groups: List[str] = None) -> Tuple[bool, str]:
    """
    Validate if a user has access based on their group membership.
    
    Args:
        user_details: User details dictionary from get_user_details_from_event()
        required_groups: List of groups that have access, if None, authentication is sufficient
        
    Returns:
        Tuple of (access_granted: bool, message: str)
    """
    if not COGNITO_AUTH_ENABLED:
        return True, "Authentication disabled"
        
    if not user_details['authenticated']:
        return False, "User is not authenticated"
    
    # If no specific groups are required, just being authenticated is enough
    if not required_groups:
        return True, "No specific group membership required"
    
    # Check if user is in any of the required groups
    user_groups = set(user_details['groups'])
    required_groups_set = set(required_groups)
    
    if user_groups.intersection(required_groups_set):
        return True, "User has required group membership"
    else:
        return False, f"User is not a member of any required groups: {required_groups}"


def get_additional_user_attributes(user_id: str) -> Optional[Dict]:
    """
    Get additional user attributes directly from Cognito User Pool.
    This is useful when you need attributes not included in the JWT token.
    
    Args:
        user_id: Cognito user ID (sub claim from token)
        
    Returns:
        Dictionary of user attributes or None if not found
    """
    if not USER_POOL_ID or not COGNITO_REGION:
        logger.warning("Missing Cognito configuration for additional attribute retrieval")
        return None
        
    try:
        # Initialize Cognito Identity Provider client
        cognito_client = boto3.client('cognito-idp', region_name=COGNITO_REGION)
        
        # Get user details
        response = cognito_client.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=user_id
        )
        
        # Extract user attributes
        user_attributes = {}
        for attr in response.get('UserAttributes', []):
            user_attributes[attr['Name']] = attr['Value']
            
        return {
            'username': response.get('Username'),
            'user_status': response.get('UserStatus'),
            'enabled': response.get('Enabled', False),
            'created_date': response.get('UserCreateDate'),
            'last_modified_date': response.get('UserLastModifiedDate'),
            'attributes': user_attributes
        }
        
    except ClientError as e:
        logger.error(f"Error retrieving user details from Cognito: {str(e)}")
        return None


def update_user_group(user_id: str, group_name: str, action: str = 'add') -> bool:
    """
    Add or remove a user from a Cognito user group.
    
    Args:
        user_id: Cognito user ID (sub claim from token)
        group_name: Name of the group
        action: Either 'add' or 'remove'
        
    Returns:
        True if successful, False otherwise
    """
    if not USER_POOL_ID or not COGNITO_REGION:
        logger.warning("Missing Cognito configuration for group management")
        return False
        
    try:
        # Initialize Cognito Identity Provider client
        cognito_client = boto3.client('cognito-idp', region_name=COGNITO_REGION)
        
        if action.lower() == 'add':
            # Add user to group
            cognito_client.admin_add_user_to_group(
                UserPoolId=USER_POOL_ID,
                Username=user_id,
                GroupName=group_name
            )
            logger.info(f"User {user_id} added to group {group_name}")
            return True
            
        elif action.lower() == 'remove':
            # Remove user from group
            cognito_client.admin_remove_user_from_group(
                UserPoolId=USER_POOL_ID,
                Username=user_id,
                GroupName=group_name
            )
            logger.info(f"User {user_id} removed from group {group_name}")
            return True
            
        else:
            logger.error(f"Invalid action: {action}. Must be 'add' or 'remove'")
            return False
            
    except ClientError as e:
        logger.error(f"Error managing user group: {str(e)}")
        return False


def get_user_groups(user_id: str) -> List[str]:
    """
    Get a list of groups that a user belongs to directly from Cognito.
    
    Args:
        user_id: Cognito user ID (sub claim from token)
        
    Returns:
        List of group names
    """
    if not USER_POOL_ID or not COGNITO_REGION:
        logger.warning("Missing Cognito configuration for group retrieval")
        return []
        
    try:
        # Initialize Cognito Identity Provider client
        cognito_client = boto3.client('cognito-idp', region_name=COGNITO_REGION)
        
        # Get user groups
        response = cognito_client.admin_list_groups_for_user(
            UserPoolId=USER_POOL_ID,
            Username=user_id
        )
        
        # Extract group names
        groups = [group['GroupName'] for group in response.get('Groups', [])]
        return groups
        
    except ClientError as e:
        logger.error(f"Error retrieving user groups from Cognito: {str(e)}")
        return []


def auto_register_user(user_details: Dict) -> Dict:
    """
    Auto-register a new user with default Publisher group in both Cognito and database.
    
    Args:
        user_details: User details dictionary from get_user_details_from_event()
        
    Returns:
        Dictionary with registration result
    """
    from config.user_config import AUTO_REGISTRATION_ENABLED, DEFAULT_AUTO_REGISTRATION_GROUP
    
    if not AUTO_REGISTRATION_ENABLED:
        return {"success": False, "message": "Auto-registration is disabled"}
    
    if not user_details.get('authenticated'):
        return {"success": False, "message": "User is not authenticated"}
    
    user_id = user_details.get('user_id')
    email = user_details.get('email')
    
    if not user_id or not email:
        return {"success": False, "message": "Missing user ID or email"}
    
    try:
        # Step 1: Add user to default group in Cognito
        cognito_success = update_user_group(user_id, DEFAULT_AUTO_REGISTRATION_GROUP, 'add')
        
        if not cognito_success:
            return {"success": False, "message": "Failed to add user to Cognito group"}
        
        # Step 2: Register user in database
        try:
            from sync_processors.user_processor import UserProcessor
            user_processor = UserProcessor()
            
            # Build payload for database registration
            db_payload = {
                "user_id": user_id,
                "email": email,
                "first_name": user_details.get('first_name', ''),
                "last_name": user_details.get('last_name', ''),
                "name": user_details.get('name', ''),
                "auth_provider": "Google"
            }
            
            # Call the auto-registration method
            db_result = user_processor._auto_register_user(db_payload)
            
            if db_result.get('success', False):
                logger.info(f"Successfully registered user {email} in database")
            else:
                logger.warning(f"Database registration failed for user {email}: {db_result.get('message', 'Unknown error')}")
                # Continue with Cognito registration even if database fails
            
        except Exception as db_e:
            logger.error(f"Error registering user {email} in database: {str(db_e)}")
            # Continue with Cognito registration even if database fails
        
        # Step 3: Update user_details with new group
        if 'groups' not in user_details:
            user_details['groups'] = []
        if DEFAULT_AUTO_REGISTRATION_GROUP not in user_details['groups']:
            user_details['groups'].append(DEFAULT_AUTO_REGISTRATION_GROUP)
        
        logger.info(f"Auto-registered user {email} with group {DEFAULT_AUTO_REGISTRATION_GROUP}")
        return {
            "success": True, 
            "message": f"User auto-registered with {DEFAULT_AUTO_REGISTRATION_GROUP} group",
            "group_added": DEFAULT_AUTO_REGISTRATION_GROUP
        }
            
    except Exception as e:
        logger.error(f"Error in auto-registration for user {email}: {str(e)}")
        return {"success": False, "message": f"Auto-registration failed: {str(e)}"}


def ensure_user_has_groups(user_details: Dict) -> Dict:
    """
    Ensure user has at least one group, adding default if needed.
    
    Args:
        user_details: User details dictionary from get_user_details_from_event()
        
    Returns:
        Updated user_details with groups ensured
    """
    from config.user_config import DEFAULT_AUTO_REGISTRATION_GROUP
    
    if not user_details.get('authenticated'):
        return user_details
    
    # If user has no groups, try to get them from Cognito directly
    if not user_details.get('groups'):
        user_id = user_details.get('user_id')
        if user_id:
            fresh_groups = get_user_groups(user_id)
            user_details['groups'] = fresh_groups
            logger.info(f"Refreshed groups for user {user_details.get('email')}: {fresh_groups}")
    
    # If still no groups, auto-register with default group
    if not user_details.get('groups'):
        logger.info(f"User {user_details.get('email')} has no groups, attempting auto-registration")
        registration_result = auto_register_user(user_details)
        
        if registration_result.get('success'):
            logger.info(f"Successfully auto-registered user {user_details.get('email')}")
        else:
            logger.warning(f"Auto-registration failed for user {user_details.get('email')}: {registration_result.get('message')}")
    
    return user_details


# Example usage in Lambda handler:
"""
def lambda_handler(event, context):
    # Extract user details from the event
    user = cognito_helper.get_user_details_from_event(event)
    
    # Ensure user has groups (auto-register if needed)
    user = cognito_helper.ensure_user_has_groups(user)
    
    # Check if the user has access to this endpoint
    has_access, message = cognito_helper.validate_user_access(
        user, 
        required_groups=['Admin', 'Publisher']
    )
    
    if not has_access:
        return {
            'statusCode': 403,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': message})
        }
    
    # If needed, get additional user attributes
    if user['authenticated']:
        additional_info = cognito_helper.get_additional_user_attributes(user['user_id'])
        
    # Process the request with user context
    # ...
    
    # Include user information in response if needed
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({
            'message': 'Success',
            'user': {
                'id': user['user_id'],
                'email': user['email'],
                'groups': user['groups']
            }
        })
    }
"""

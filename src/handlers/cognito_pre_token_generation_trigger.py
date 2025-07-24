"""
Cognito Pre-Token Generation Trigger Lambda Handler
Automatically adds User Pool groups to JWT tokens for proper authorization.

This Lambda function:
1. Runs before JWT token generation
2. Queries user's actual User Pool groups from Cognito
3. Adds groups to the JWT token claims
4. Ensures API receives correct group information

Trigger Type: PreTokenGeneration
Event Source: Cognito User Pool
"""

import json
import logging
import os
import boto3
from typing import Dict, Any, List
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
COGNITO_REGION = os.environ.get('COGNITO_REGION', 'us-east-1')
DEFAULT_USER_GROUP = os.environ.get('DEFAULT_USER_GROUP', 'Publisher')
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'users')

# AWS clients
cognito_client = boto3.client('cognito-idp', region_name=COGNITO_REGION)
dynamodb = boto3.resource('dynamodb', region_name=COGNITO_REGION)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Cognito Pre-Token Generation Trigger Handler
    
    Args:
        event: Cognito trigger event
        context: Lambda context
        
    Returns:
        The modified event with updated claims
    """
    logger.info("Pre-Token Generation trigger received event: %s", json.dumps(event, default=str))
    
    try:
        # Extract user information from the event
        user_id = event['userName']
        user_pool_id = event['userPoolId']
        
        logger.info(f"Processing pre-token generation for user: {user_id}")
        
        # Get user's actual groups from Cognito
        user_groups = get_user_groups(user_pool_id, user_id)
        logger.info(f"User {user_id} belongs to groups: {user_groups}")
        
        # Get user attributes from the event (standard approach)
        user_attributes = event.get('request', {}).get('userAttributes', {})
        logger.info(f"User attributes from event: {list(user_attributes.keys())}")
        
        # Check if this is first login (user doesn't exist in database)
        is_first_login = not user_exists_in_database(user_id)
        logger.info(f"User {user_id} first login: {is_first_login}")
        
        # Handle group assignment and user creation for first login only
        if is_first_login:
            logger.info(f"First login for user {user_id} - setting up user account")
            
            # Add user to Publisher group if they don't have it specifically
            if DEFAULT_USER_GROUP not in user_groups:
                logger.info(f"User {user_id} does not have {DEFAULT_USER_GROUP} group. Current groups: {user_groups}")
                logger.info(f"Adding user {user_id} to default group: {DEFAULT_USER_GROUP}")
                success = add_user_to_default_group(user_pool_id, user_id)
                if success:
                    # Re-fetch groups after assignment
                    user_groups = get_user_groups(user_pool_id, user_id)
                    logger.info(f"Successfully added user {user_id} to default group. New groups: {user_groups}")
                else:
                    logger.error(f"Failed to add user {user_id} to default group")
            else:
                logger.info(f"User {user_id} already has {DEFAULT_USER_GROUP} group: {user_groups}")
            
            # Create user record in database
            create_user_in_database(user_id, user_attributes)
        else:
            logger.info(f"Subsequent login for user {user_id} - skipping group assignment")
        
        # Prepare claims to add to token
        claims_to_add = {}
        
        # Add groups to the JWT token claims
        if user_groups:
            # For multiple groups, Cognito expects a comma-separated string
            groups_string = ','.join(user_groups)
            claims_to_add['cognito:groups'] = groups_string
            logger.info(f"Added groups to token claims: {groups_string}")
        else:
            logger.warning(f"User {user_id} has no groups - token will not include group claims")
        
        # Add name information to token claims if available
        if user_attributes:
            # Add first and last name if available
            if user_attributes.get('given_name'):
                claims_to_add['given_name'] = user_attributes['given_name']
                logger.info(f"Added given_name to token: {user_attributes['given_name']}")
            if user_attributes.get('family_name'):
                claims_to_add['family_name'] = user_attributes['family_name']
                logger.info(f"Added family_name to token: {user_attributes['family_name']}")
            
            # Create full name from first and last name
            given_name = user_attributes.get('given_name', '')
            family_name = user_attributes.get('family_name', '')
            if given_name or family_name:
                full_name = f"{given_name} {family_name}".strip()
                claims_to_add['name'] = full_name
                logger.info(f"Added name to token claims: {full_name}")
        
        # Add claims to token if we have any
        if claims_to_add:
            event['response']['claimsOverrideDetails'] = {
                'claimsToAddOrOverride': claims_to_add
            }
            logger.info(f"Added claims to token: {list(claims_to_add.keys())}")
        
        # Return the modified event
        return event
        
    except Exception as e:
        logger.error(f"Error in pre-token generation trigger: {str(e)}")
        # Don't fail the token generation - just log the error
        # Return the original event to allow authentication to proceed
        return event


def get_user_groups(user_pool_id: str, user_id: str) -> List[str]:
    """Get list of groups that a user belongs to"""
    try:
        response = cognito_client.admin_list_groups_for_user(
            UserPoolId=user_pool_id,
            Username=user_id
        )
        groups = [group['GroupName'] for group in response.get('Groups', [])]
        return groups
    except ClientError as e:
        logger.error(f"Error getting user groups: {str(e)}")
        return []


def add_user_to_default_group(user_pool_id: str, user_id: str) -> bool:
    """Add user to the default group"""
    try:
        cognito_client.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=user_id,
            GroupName=DEFAULT_USER_GROUP
        )
        logger.info(f"Successfully added user {user_id} to group {DEFAULT_USER_GROUP}")
        return True
    except ClientError as e:
        logger.error(f"Error adding user {user_id} to group {DEFAULT_USER_GROUP}: {str(e)}")
        return False


def user_exists_in_database(user_id: str) -> bool:
    """Check if user exists in the database"""
    try:
        if not USERS_TABLE_NAME:
            logger.warning("USERS_TABLE_NAME not configured, assuming user doesn't exist")
            return False
            
        table = dynamodb.Table(USERS_TABLE_NAME)
        response = table.get_item(Key={'user_id': user_id})
        exists = 'Item' in response
        logger.info(f"User {user_id} exists in database: {exists}")
        return exists
        
    except ClientError as e:
        logger.error(f"Error checking user existence: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking user existence: {str(e)}")
        return False


def create_user_in_database(user_id: str, user_attributes: dict) -> None:
    """Create user record in the database"""
    try:
        if not USERS_TABLE_NAME:
            logger.warning("USERS_TABLE_NAME not configured, skipping database registration")
            return
            
        # Extract user information
        email = user_attributes.get('email', '')
        given_name = user_attributes.get('given_name', '')
        family_name = user_attributes.get('family_name', '')
        full_name = f"{given_name} {family_name}".strip()
        
        logger.info(f"Creating user record for {user_id} in database")
        
        table = dynamodb.Table(USERS_TABLE_NAME)
        
        # Create user record
        from datetime import datetime
        
        user_data = {
            'user_id': user_id,
            'email': email,
            'first_name': given_name,
            'last_name': family_name,
            'name': full_name,
            'role': 'PUBLISHER',
            'auth_provider': 'Google',
            'is_active': True,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        table.put_item(Item=user_data)
        logger.info(f"Successfully created user record for {user_id} in database")
        
    except Exception as e:
        logger.error(f"Error creating user in database: {str(e)}")
        # Don't fail the token generation - just log the error




# Example event structure for reference:
"""
{
    "version": "1",
    "region": "us-east-1",
    "userPoolId": "us-east-1_EXAMPLE",
    "userName": "user-id-from-cognito",
    "callerContext": {
        "awsSdkVersion": "aws-sdk-nodejs-2.49.0",
        "clientId": "client-id"
    },
    "triggerSource": "TokenGeneration_HostedAuth",
    "request": {
        "userAttributes": {
            "sub": "user-id-from-cognito",
            "email_verified": "true",
            "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_EXAMPLE",
            "cognito:username": "user-id-from-cognito",
            "given_name": "John",
            "family_name": "Doe",
            "aud": "client-id",
            "email": "john.doe@example.com"
        },
        "groupConfiguration": {
            "groupsToOverride": [],
            "iamRolesToOverride": [],
            "preferredRole": null
        }
    },
    "response": {
        "claimsOverrideDetails": {
            "claimsToAddOrOverride": {},
            "claimsToSuppress": [],
            "groupOverrideDetails": {
                "groupsToOverride": [],
                "iamRolesToOverride": [],
                "preferredRole": null
            }
        }
    }
}
"""

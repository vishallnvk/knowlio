"""
Cognito Post-Authentication Trigger Lambda Handler
Automatically runs after every successful Cognito login to ensure users are properly registered.

This Lambda function:
1. Adds new users to the default "Publisher" group in Cognito
2. Creates user records in the database
3. Ensures consistent user permissions across the system

Trigger Type: PostAuthentication
Event Source: Cognito User Pool
"""

import json
import logging
import os
import boto3
from typing import Dict, Any
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
COGNITO_REGION = os.environ.get('COGNITO_REGION', 'us-east-1')
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME')
DEFAULT_GROUP = os.environ.get('DEFAULT_USER_GROUP', 'Publisher')
DEFAULT_ROLE = os.environ.get('DEFAULT_USER_ROLE', 'PUBLISHER')

# AWS clients
cognito_client = boto3.client('cognito-idp', region_name=COGNITO_REGION)
dynamodb = boto3.resource('dynamodb', region_name=COGNITO_REGION)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Cognito Post-Authentication Trigger Handler
    
    Args:
        event: Cognito trigger event
        context: Lambda context
        
    Returns:
        The original event (required by Cognito triggers)
    """
    logger.info("Post-Authentication trigger received event: %s", json.dumps(event, default=str))
    
    try:
        # Extract user information from the event
        user_pool_id = event['userPoolId']
        
        # Get user attributes
        user_attributes = event.get('request', {}).get('userAttributes', {})
        
        # Use the 'sub' claim as the user_id (this is the actual Cognito User Pool user ID)
        # NOT event['userName'] which is the federated identity ID
        user_id = user_attributes.get('sub')
        if not user_id:
            logger.error("No 'sub' claim found in user attributes")
            return event
        email = user_attributes.get('email', '')
        given_name = user_attributes.get('given_name', '')
        family_name = user_attributes.get('family_name', '')
        
        logger.info(f"Processing post-auth for user: {user_id} ({email})")
        
        # Step 1: Check if user is already in any groups
        user_groups = get_user_groups(user_pool_id, user_id)
        logger.info(f"User {user_id} current groups: {user_groups}")
        
        # Step 2: Add user to default group if they have no groups
        if not user_groups:
            success = add_user_to_group(user_pool_id, user_id, DEFAULT_GROUP)
            if success:
                logger.info(f"Successfully added user {user_id} to group {DEFAULT_GROUP}")
            else:
                logger.error(f"Failed to add user {user_id} to group {DEFAULT_GROUP}")
        else:
            logger.info(f"User {user_id} already in groups: {user_groups}")
        
        # Step 3: Ensure user exists in database
        ensure_user_in_database(user_id, email, given_name, family_name)
        
        # Step 4: Return the original event (required by Cognito)
        return event
        
    except Exception as e:
        logger.error(f"Error in post-authentication trigger: {str(e)}")
        # Don't fail the authentication - just log the error
        # Cognito will still allow the login to proceed
        return event


def get_user_groups(user_pool_id: str, user_id: str) -> list:
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


def add_user_to_group(user_pool_id: str, user_id: str, group_name: str) -> bool:
    """Add user to a Cognito group"""
    try:
        cognito_client.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=user_id,
            GroupName=group_name
        )
        return True
    except ClientError as e:
        logger.error(f"Error adding user to group: {str(e)}")
        return False


def ensure_user_in_database(user_id: str, email: str, given_name: str, family_name: str) -> None:
    """Ensure user exists in the database"""
    if not USERS_TABLE_NAME:
        logger.warning("USERS_TABLE_NAME not configured, skipping database registration")
        return
    
    try:
        # Prepare user data
        full_name = f"{given_name} {family_name}".strip()
        user_data = {
            'user_id': user_id,
            'email': email,
            'first_name': given_name,
            'last_name': family_name,
            'name': full_name,
            'role': DEFAULT_ROLE,
            'auth_provider': 'Google',
            'is_active': True
        }
        
        # Check if user already exists
        table = dynamodb.Table(USERS_TABLE_NAME)
        
        try:
            response = table.get_item(Key={'user_id': user_id})
            if 'Item' in response:
                logger.info(f"User {user_id} already exists in database")
                return
        except ClientError as e:
            logger.error(f"Error checking user existence: {str(e)}")
        
        # Create user record
        import time
        from datetime import datetime
        
        user_data['created_at'] = datetime.utcnow().isoformat()
        user_data['updated_at'] = datetime.utcnow().isoformat()
        
        table.put_item(Item=user_data)
        logger.info(f"Successfully created user record for {user_id} in database")
        
    except Exception as e:
        logger.error(f"Error ensuring user in database: {str(e)}")
        # Don't fail the authentication - just log the error


def create_user_via_processor(user_id: str, email: str, given_name: str, family_name: str) -> None:
    """
    Alternative method to create user via UserProcessor
    (In case direct DynamoDB approach doesn't work)
    """
    try:
        # This would require importing the processor, which might cause issues
        # in the Lambda environment. Using direct DynamoDB approach instead.
        pass
    except Exception as e:
        logger.error(f"Error creating user via processor: {str(e)}")


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
    "triggerSource": "PostAuthentication_Authentication",
    "request": {
        "userAttributes": {
            "sub": "user-id-from-cognito",
            "email_verified": "true",
            "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_EXAMPLE",
            "cognito:username": "user-id-from-cognito",
            "given_name": "John",
            "family_name": "Doe",
            "aud": "client-id",
            "identities": "[{\"userId\":\"google-user-id\",\"providerName\":\"Google\",\"providerType\":\"Google\",\"issuer\":null,\"primary\":true,\"dateCreated\":1234567890}]",
            "token_use": "id",
            "auth_time": "1234567890",
            "exp": "1234567890",
            "iat": "1234567890",
            "email": "john.doe@example.com"
        }
    },
    "response": {}
}
"""

import uuid
import re
from typing import Optional, Dict, List, Any, Union

from helpers.aws_service_helpers.dynamodb_helper import DynamoDBHelper
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.common_helper import Retry
from helpers.common_helper.auth_helper import RoleBasedAuth, AuthorizationError
from models.user_model import UserModel
import botocore.exceptions

logger = LoggerHelper(__name__).get_logger()

USERS_TABLE = "users"

class UserValidationError(Exception):
    """Exception raised for user data validation failures."""
    pass

class UserHelper:
    def __init__(self):
        self.db = DynamoDBHelper(table_name=USERS_TABLE)

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def register_user(self, user_data: Dict) -> Dict:
        """
        Register a new user with validation.
        
        Args:
            user_data: User information including required fields
            
        Returns:
            Dict with success message and user_id
            
        Raises:
            UserValidationError: If validation fails
        """
        # Validate required fields
        required_fields = ["email", "role"]
        for field in required_fields:
            if field not in user_data:
                raise UserValidationError(f"Missing required field: {field}")
        
        # Validate email format
        if not self._is_valid_email(user_data["email"]):
            raise UserValidationError(f"Invalid email format: {user_data['email']}")
            
        # Validate role
        if not RoleBasedAuth.validate_role(user_data["role"]):
            valid_roles = ", ".join(RoleBasedAuth.VALID_ROLES)
            raise UserValidationError(f"Invalid role: {user_data['role']}. Valid roles: {valid_roles}")
            
        # Check if email already exists
        existing_users = self.search_users({"email": user_data["email"]})
        if existing_users and len(existing_users.get("items", [])) > 0:
            raise UserValidationError(f"User with email {user_data['email']} already exists")
            
        # Validate metadata based on role
        self._validate_role_specific_metadata(user_data.get("role"), user_data.get("metadata", {}))
                
        # Create user
        user_id = str(uuid.uuid4())
        user_item = UserModel(user_data).__dict__

        logger.info("Registering user: %s", user_item)
        self.db.put_item(user_item)
        return {"message": "User registered successfully", "user_id": user_id}

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """
        Get user profile by ID.
        
        Args:
            user_id: ID of the user to fetch
            
        Returns:
            User profile data or None if not found
        """
        logger.info("Fetching user profile for user_id: %s", user_id)
        return self.db.get_item({"user_id": user_id})

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def update_user_profile(self, user_id: str, updates: Dict) -> Dict:
        """
        Update user profile with validation.
        
        Args:
            user_id: ID of the user to update
            updates: Fields to update
            
        Returns:
            Updated user data
            
        Raises:
            UserValidationError: If validation fails
        """
        logger.info("Updating user profile for user_id: %s with updates: %s", user_id, updates)
        
        # If role is being updated, validate it
        if "role" in updates and not RoleBasedAuth.validate_role(updates["role"]):
            valid_roles = ", ".join(RoleBasedAuth.VALID_ROLES)
            raise UserValidationError(f"Invalid role: {updates['role']}. Valid roles: {valid_roles}")
            
        # If email is being updated, validate format and uniqueness
        if "email" in updates:
            if not self._is_valid_email(updates["email"]):
                raise UserValidationError(f"Invalid email format: {updates['email']}")
                
            existing_users = self.search_users({"email": updates["email"]})
            if existing_users and len(existing_users.get("items", [])) > 0:
                user_list = existing_users.get("items", [])
                for user in user_list:
                    if user.get("user_id") != user_id:  # Skip the current user
                        raise UserValidationError(f"User with email {updates['email']} already exists")
        
        # If metadata is being updated and role exists, validate metadata
        if "metadata" in updates:
            # Get current user to check role
            user = self.get_user_profile(user_id)
            if user:
                role = updates.get("role", user.get("role"))
                self._validate_role_specific_metadata(role, updates["metadata"])
        
        return self.db.update_item("user_id", user_id, updates)

    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def list_users_by_role(self, role: str, limit: int = None, pagination_token: str = None) -> Dict:
        """
        List users by role with pagination.
        
        Args:
            role: Role to filter by
            limit: Maximum number of items to return
            pagination_token: Token for pagination
            
        Returns:
            Dict with users and pagination info
            
        Raises:
            UserValidationError: If role is invalid
        """
        if not RoleBasedAuth.validate_role(role):
            valid_roles = ", ".join(RoleBasedAuth.VALID_ROLES)
            raise UserValidationError(f"Invalid role: {role}. Valid roles: {valid_roles}")
            
        logger.info("Listing users with role: %s (limit: %s)", role, limit)
        
        return self.db.query_items(
            key_name="role", 
            key_value=role,
            limit=limit,
            last_evaluated_key=self._decode_pagination_token(pagination_token)
        )
        
    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def search_users(self, search_params: Dict, limit: int = None, pagination_token: str = None) -> Dict:
        """
        Generic search users method that can handle various criteria.
        
        Args:
            search_params: Dict of search parameters
            limit: Maximum number of items to return
            pagination_token: Token for pagination
            
        Returns:
            Dict with matching users and pagination info
        """
        logger.info("Searching users with parameters: %s (limit: %s)", search_params, limit)
        
        # Start with all users or filter by a specific field if indexed
        base_result = {}
        last_evaluated_key = self._decode_pagination_token(pagination_token)
        
        # See if we can use an indexed field for more efficient querying
        indexed_fields = ["role", "email"]  # Fields that might have indexes
        for field in indexed_fields:
            if field in search_params:
                try:
                    # Attempt to use the index
                    base_result = self.db.query_items(
                        key_name=field, 
                        key_value=search_params[field],
                        limit=limit,
                        last_evaluated_key=last_evaluated_key
                    )
                    # If successful, remove this param so we don't filter again
                    del search_params[field]
                    break
                except Exception as e:
                    logger.warning(f"Failed to use index for {field}: {str(e)}")
                    # Continue to try other fields or fall back to scan
        
        # If no indexed field was found or query failed, fall back to scan
        if not base_result:
            base_result = self.db.scan_items(
                limit=limit,
                last_evaluated_key=last_evaluated_key
            )
        
        # Apply additional filters based on search_params
        if search_params:
            filtered_items = []
            for item in base_result.get("items", []):
                if self._matches_search_criteria(item, search_params):
                    filtered_items.append(item)
            
            # Update the results with filtered items
            base_result["items"] = filtered_items
            base_result["count"] = len(filtered_items)
        
        return base_result
        
    @Retry(max_attempts=3, initial_wait=1.0, exceptions=[botocore.exceptions.ClientError, botocore.exceptions.BotoCoreError])
    def admin_update_user(self, user_id: str, field: str, value: Any) -> Dict:
        """
        Generic admin method to update any user field.
        
        Args:
            user_id: ID of user to update
            field: Field name to update
            value: New value for the field
            
        Returns:
            Updated user data
            
        Raises:
            UserValidationError: If field or value is invalid
        """
        if field in ["user_id", "created_at"]:
            raise UserValidationError(f"Cannot update immutable field: {field}")
            
        # Special validation for certain fields
        if field == "role" and not RoleBasedAuth.validate_role(value):
            valid_roles = ", ".join(RoleBasedAuth.VALID_ROLES)
            raise UserValidationError(f"Invalid role: {value}. Valid roles: {valid_roles}")
        
        if field == "email" and not self._is_valid_email(value):
            raise UserValidationError(f"Invalid email format: {value}")
            
        logger.info("Admin updating user %s field %s to %s", user_id, field, value)
        return self.db.update_item("user_id", user_id, {field: value})
        
    # Helper methods
    def _is_valid_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))
        
    def _validate_role_specific_metadata(self, role: str, metadata: Dict) -> None:
        """
        Validate metadata based on user role.
        
        Args:
            role: User role
            metadata: Metadata to validate
            
        Raises:
            UserValidationError: If validation fails
        """
        if role == "PUBLISHER":
            # Optional validation for publisher specific fields
            if "legal_entity" in metadata and not isinstance(metadata["legal_entity"], str):
                raise UserValidationError("legal_entity must be a string")
                
            if "content_types" in metadata and not isinstance(metadata["content_types"], list):
                raise UserValidationError("content_types must be a list")
                
        elif role == "CONSUMER":
            # Optional validation for consumer specific fields
            if "license_tier" in metadata and not isinstance(metadata["license_tier"], str):
                raise UserValidationError("license_tier must be a string")
                
            if "api_quota" in metadata and not isinstance(metadata["api_quota"], (int, float)):
                raise UserValidationError("api_quota must be a number")
    
    def _matches_search_criteria(self, item: Dict, search_params: Dict) -> bool:
        """
        Check if an item matches all search criteria.
        
        Args:
            item: User item to check
            search_params: Search parameters to match
            
        Returns:
            True if matches all criteria, False otherwise
        """
        for key, value in search_params.items():
            # Handle nested keys like metadata.field
            if "." in key:
                parts = key.split(".")
                curr_item = item
                for part in parts[:-1]:
                    if part not in curr_item:
                        return False
                    curr_item = curr_item[part]
                
                last_part = parts[-1]
                if last_part not in curr_item or curr_item[last_part] != value:
                    return False
                    
            # Handle normal keys with string partial matching
            elif key in item:
                if isinstance(item[key], str) and isinstance(value, str):
                    # Case-insensitive partial match for strings
                    if value.lower() not in item[key].lower():
                        return False
                elif item[key] != value:
                    return False
            else:
                return False
                
        return True
        
    def _decode_pagination_token(self, pagination_token: Optional[str]) -> Optional[Dict]:
        """
        Decode a pagination token to a DynamoDB last_evaluated_key.
        
        Args:
            pagination_token: Base64 encoded token
            
        Returns:
            Decoded last_evaluated_key or None if no token
        """
        if not pagination_token:
            return None
            
        try:
            import json
            import base64
            decoded_token = base64.b64decode(pagination_token)
            return json.loads(decoded_token)
        except Exception as e:
            logger.error(f"Failed to decode pagination token: {e}")
            raise ValueError(f"Invalid pagination token: {pagination_token}")

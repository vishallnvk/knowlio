from typing import Dict, Any, List

from helpers.common_helper.common_helper import require_keys
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.auth_helper import RoleBasedAuth, require_role, AuthorizationError
from helpers.common_helper.auth_helper import get_authenticated_user_id, get_authenticated_user_role
from helpers.common_helper.auth_context import AuthContext
from helpers.common_helper.response_formatter import ResponseFormatter
from helpers.app_logic_helpers.user_helper import UserHelper, UserValidationError
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor
from config.user_config import IMMUTABLE_FIELDS

logger = LoggerHelper(__name__).get_logger()


@ProcessorRegistry.register("user")
class UserProcessor(BaseProcessor):
    def __init__(self):
        self.helper = UserHelper()
        super().__init__({
            "register_user": self._register_user,
            "get_user_profile": self._get_user_profile,
            "update_user_profile": self._update_user_profile,
            "search_users": self._search_users,
            "admin_update_user": self._admin_update_user,
        })

    def _register_user(self, payload: Dict) -> Dict:
        """
        Register a new user with validation.
        
        Required payload keys:
        - email: User email address
        - role: User role (PUBLISHER/CONSUMER/ADMIN)
        
        Optional payload keys:
        - name: User display name
        - organization: Organization name
        - auth_provider: Authentication provider
        - metadata: Role-specific metadata
        """
        try:
            require_keys(payload, ["email", "role"])
            
            # Add authenticated user ID as creator if available
            creator_id = get_authenticated_user_id(payload)
            if creator_id:
                payload["created_by"] = creator_id
            
            result = self.helper.register_user(payload)
            
            # Handle error response from helper
            if "error" in result:
                message, code = ResponseFormatter.extract_error_info(result)
                return ResponseFormatter.format_error(message, ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
            
            # Format successful create response
            return ResponseFormatter.format_create_response(
                resource_type="user",
                resource_id=result.get("user_id"),
                resource_data=result
            )
        except UserValidationError as e:
            logger.warning(f"User registration validation error: {str(e)}")
            return ResponseFormatter.format_error(str(e), ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
        except Exception as e:
            logger.error(f"Error registering user: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to register user: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

    def _get_user_profile(self, payload: Dict) -> Dict:
        """
        Get user profile by ID.
        
        Required payload keys:
        - user_id: ID of user to fetch
        """
        try:
            require_keys(payload, ["user_id"])
            user_profile = self.helper.get_user_profile(payload["user_id"])
            
            if not user_profile:
                return ResponseFormatter.format_error(
                    f"User not found with ID: {payload['user_id']}", 
                    ResponseFormatter.ERROR_CODES["NOT_FOUND"]
                )
            
            # Format successful response with user data
            return ResponseFormatter.format_success(user_profile)
        except Exception as e:
            logger.error(f"Error fetching user profile: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to fetch user profile: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

    def _update_user_profile(self, payload: Dict) -> Dict:
        """
        Update user profile with validation.
        
        Required payload keys:
        - user_id: ID of user to update
        - updates: Dictionary of fields to update
        
        Possible updates:
        - name: Update display name
        - organization: Update organization name
        - email: Update email (with validation)
        - metadata: Update metadata (with role-specific validation)
        """
        try:
            require_keys(payload, ["user_id", "updates"])
            
            # Get authenticated user from context
            auth_context = AuthContext.from_payload(payload)
            
            # Ensure we're not trying to update immutable fields
            updates = payload["updates"]
            for field in IMMUTABLE_FIELDS:
                if field in updates:
                    return ResponseFormatter.format_error(
                        f"Cannot update immutable field: {field}",
                        ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"],
                        field=field
                    )
            
            # Add modification audit info
            if auth_context.is_authenticated():
                if "metadata" not in updates:
                    updates["metadata"] = {}
                    
                updates["metadata"]["last_modified_by"] = auth_context.user_id
            
            updated_user = self.helper.update_user_profile(payload["user_id"], updates)
            
            # Handle error response from helper
            if "error" in updated_user:
                message, code = ResponseFormatter.extract_error_info(updated_user)
                return ResponseFormatter.format_error(message, code)
            
            # Format successful update response
            return ResponseFormatter.format_update_response(
                resource_type="user",
                resource_id=payload["user_id"],
                updated_resource=updated_user
            )
        except UserValidationError as e:
            logger.warning(f"User update validation error: {str(e)}")
            return ResponseFormatter.format_error(str(e), ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to update user profile: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

    def _search_users(self, payload: Dict) -> Dict:
        """
        Search for users with various criteria.
        
        Optional payload keys:
        - Any field to search by (e.g. email, name, organization)
        - metadata.field: Search in nested metadata (dot notation)
        - limit: Maximum number of results
        - pagination_token: Pagination token
        """
        try:
            # Extract pagination parameters
            search_params = payload.copy()
            limit = search_params.pop("limit", None)
            pagination_token = search_params.pop("pagination_token", None)
            
            result = self.helper.search_users(search_params, limit, pagination_token)
            
            # Handle error case
            if "error" in result:
                message, code = ResponseFormatter.extract_error_info(result)
                return ResponseFormatter.format_error(message, code)
            
            # Extract pagination info
            pagination_info = result.get("pagination", {})
            
            # Format standardized list response
            return ResponseFormatter.format_list_response(
                items=result.get("items", []),
                count=result.get("count", 0),
                total_scanned=result.get("scanned_count", 0),
                pagination_token=pagination_info.get("next_token"),
                has_more=pagination_info.get("has_more", False)
            )
        except Exception as e:
            logger.error(f"Error searching users: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to search users: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])
    
    @require_role("ADMIN")
    def _admin_update_user(self, payload: Dict) -> Dict:
        """
        Generic admin method to update any user field.
        Requires ADMIN role.
        
        Required payload keys:
        - user_id: ID of user to update
        - field: Field name to update
        - value: New value for the field
        """
        try:
            require_keys(payload, ["user_id", "field", "value"])
            
            user_id = payload["user_id"]
            field = payload["field"]
            value = payload["value"]
            
            # Log who made the admin change
            admin_user_id = get_authenticated_user_id(payload)
            logger.info(f"Admin user {admin_user_id} updating user {user_id}, field {field}")
            
            updated_user = self.helper.admin_update_user(user_id, field, value)
            
            # Handle error response from helper
            if "error" in updated_user:
                message, code = ResponseFormatter.extract_error_info(updated_user)
                return ResponseFormatter.format_error(message, code)
            
            # Format successful update response
            return ResponseFormatter.format_update_response(
                resource_type="user",
                resource_id=user_id,
                updated_resource=updated_user
            )
        except UserValidationError as e:
            logger.warning(f"User update validation error: {str(e)}")
            return ResponseFormatter.format_error(str(e), ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"])
        except AuthorizationError as e:
            logger.warning(f"Authorization failed for admin_update_user: {str(e)}")
            return ResponseFormatter.format_error("Not authorized to perform this action", 
                                               ResponseFormatter.ERROR_CODES["FORBIDDEN"])
        except Exception as e:
            logger.error(f"Error in admin_update_user: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to update user: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

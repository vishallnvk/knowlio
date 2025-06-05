from typing import Dict, Any, List

from helpers.common_helper.common_helper import require_keys
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.auth_helper import RoleBasedAuth, require_role, AuthorizationError
from helpers.app_logic_helpers.user_helper import UserHelper, UserValidationError
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor

logger = LoggerHelper(__name__).get_logger()


@ProcessorRegistry.register("user")
class UserProcessor(BaseProcessor):
    def __init__(self):
        self.helper = UserHelper()
        super().__init__({
            "register_user": self._register_user,
            "get_user_profile": self._get_user_profile,
            "update_user_profile": self._update_user_profile,
            "list_users_by_role": self._list_users_by_role,
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
            return self.helper.register_user(payload)
        except UserValidationError as e:
            logger.warning(f"User registration validation error: {str(e)}")
            return {"error": str(e)}

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
                return {"error": f"User not found with ID: {payload['user_id']}"}
            
            return user_profile
        except Exception as e:
            logger.error(f"Error fetching user profile: {str(e)}")
            return {"error": f"Failed to fetch user profile: {str(e)}"}

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
            
            # Ensure we're not trying to update immutable fields
            updates = payload["updates"]
            immutable_fields = ["user_id", "created_at"]
            for field in immutable_fields:
                if field in updates:
                    return {"error": f"Cannot update immutable field: {field}"}
            
            updated_user = self.helper.update_user_profile(payload["user_id"], updates)
            return updated_user
        except UserValidationError as e:
            logger.warning(f"User update validation error: {str(e)}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            return {"error": f"Failed to update user profile: {str(e)}"}

    def _list_users_by_role(self, payload: Dict) -> Dict:
        """
        List users by role with pagination.
        
        Required payload keys:
        - role: Role to filter by (PUBLISHER/CONSUMER/ADMIN)
        
        Optional payload keys:
        - limit: Maximum number of items to return
        - pagination_token: Token for retrieving the next page of results
        """
        try:
            require_keys(payload, ["role"])
            
            role = payload["role"]
            limit = payload.get("limit")
            pagination_token = payload.get("pagination_token")
            
            result = self.helper.list_users_by_role(role, limit, pagination_token)
            
            # Rename items field to users for API consistency
            response = {
                "users": result.get("items", []),
                "count": result.get("count", 0),
                "total_scanned": result.get("scanned_count", 0),
            }
            
            # Add pagination info if present
            if "pagination_token" in result:
                response["pagination"] = {
                    "next_token": result["pagination_token"],
                    "has_more": result.get("has_more", False)
                }
            
            return response
        except UserValidationError as e:
            logger.warning(f"Invalid role in list users request: {str(e)}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            return {"error": f"Failed to list users: {str(e)}"}
    
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
            
            # Rename items field to users for API consistency
            response = {
                "users": result.get("items", []),
                "count": result.get("count", 0),
                "total_scanned": result.get("scanned_count", 0),
            }
            
            # Add pagination info if present
            if "pagination_token" in result:
                response["pagination"] = {
                    "next_token": result["pagination_token"],
                    "has_more": result.get("has_more", False)
                }
            
            return response
        except Exception as e:
            logger.error(f"Error searching users: {str(e)}")
            return {"error": f"Failed to search users: {str(e)}"}
    
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
            
            updated_user = self.helper.admin_update_user(user_id, field, value)
            return updated_user
        except UserValidationError as e:
            logger.warning(f"User update validation error: {str(e)}")
            return {"error": str(e)}
        except AuthorizationError as e:
            logger.warning(f"Authorization failed for admin_update_user: {str(e)}")
            return {"error": "Not authorized to perform this action", "status_code": 403}
        except Exception as e:
            logger.error(f"Error in admin_update_user: {str(e)}")
            return {"error": f"Failed to update user: {str(e)}"}

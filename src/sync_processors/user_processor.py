from typing import Dict, Any, List
from datetime import datetime

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
            "update_ai_consents": self._update_ai_consents,
            "update_user_agreement": self._update_user_agreement, 
            "search_users": self._search_users,
            "admin_update_user": self._admin_update_user,
            "get_ai_consent_attributes": self._get_ai_consent_attributes,
            "get_user_agreement_attributes": self._get_user_agreement_attributes,
        })
    
    def _get_authenticated_user_id(self, payload: Dict) -> tuple:
        """
        Extract user_id from authentication context.
        
        Args:
            payload: Processor method payload
            
        Returns:
            Tuple of (user_id, error_response). If authenticated, returns (user_id, None).
            If not authenticated, returns (None, error_response).
        """
        auth_context = AuthContext.from_payload(payload)
        if not auth_context.is_authenticated():
            error_response = ResponseFormatter.format_error(
                "Authentication required", 
                ResponseFormatter.ERROR_CODES["UNAUTHORIZED"]
            )
            return None, error_response
        return auth_context.user_id, None

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
        Get authenticated user's profile.
        No payload keys required - uses authentication context.
        """
        try:
            user_id, error = self._get_authenticated_user_id(payload)
            if error:
                return error
            
            user_profile = self.helper.get_user_profile(user_id)
            
            if not user_profile:
                return ResponseFormatter.format_error(
                    f"User not found with ID: {user_id}", 
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
        Update authenticated user's profile.
        
        Required payload keys:
        - updates: Dictionary of fields to update
        
        Possible updates:
        - name: Update display name
        - organization: Update organization name
        - email: Update email (with validation)
        - metadata: Update metadata (with role-specific validation)
        """
        try:
            # Support both authenticated self-update and internal calls with user_id
            if "user_id" in payload:
                # Internal call from other methods
                user_id = payload["user_id"]
                auth_context = AuthContext.from_payload(payload)
            else:
                # Direct API call - use authenticated user
                user_id, error = self._get_authenticated_user_id(payload)
                if error:
                    return error
                auth_context = AuthContext.from_payload(payload)
            
            require_keys(payload, ["updates"])
            
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
            
            updated_user = self.helper.update_user_profile(user_id, updates)
            
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

    def _update_ai_consents(self, payload: Dict) -> Dict:
        """
        Update authenticated user's AI consent attributes.
        Automatically sets current UTC timestamp for corresponding date fields.
        
        Optional payload keys (at least one required):
        - ai_training_consent: Boolean consent for AI training
        - ai_reference_consent: Boolean consent for AI reference
        - ai_marketplace_consent: Boolean consent for AI marketplace
        """
        try:
            user_id, error = self._get_authenticated_user_id(payload)
            if error:
                return error
            
            # Extract consent data - check if nested in 'payload' key first
            consent_data = payload
            if "payload" in payload and isinstance(payload["payload"], dict):
                # Handle case where consent fields are nested
                consent_data = payload["payload"]
            
            # Build updates dictionary with automatic timestamp handling
            updates = {}
            current_utc_time = datetime.utcnow().isoformat() + "Z"
            
            # Handle AI training consent
            if "ai_training_consent" in consent_data:
                updates["ai_training_consent"] = consent_data["ai_training_consent"]
                updates["ai_training_consent_date"] = current_utc_time
                
            # Handle AI reference consent  
            if "ai_reference_consent" in consent_data:
                updates["ai_reference_consent"] = consent_data["ai_reference_consent"]
                updates["ai_reference_consent_date"] = current_utc_time
                
            # Handle AI marketplace consent
            if "ai_marketplace_consent" in consent_data:
                updates["ai_marketplace_consent"] = consent_data["ai_marketplace_consent"]
                updates["ai_marketplace_consent_date"] = current_utc_time
            
            # Validate that at least one consent field was provided
            consent_fields = ["ai_training_consent", "ai_reference_consent", "ai_marketplace_consent"]
            if not any(field in consent_data for field in consent_fields):
                return ResponseFormatter.format_error(
                    "At least one AI consent field must be provided",
                    ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"]
                )
            
            logger.info(f"User {user_id} updating AI consents: {list(updates.keys())}")
            
            # Call the existing update_user_profile method internally
            update_payload = {
                "user_id": user_id,
                "updates": updates,
                "auth_context": payload.get("auth_context")
            }
            
            return self._update_user_profile(update_payload)
            
        except Exception as e:
            logger.error(f"Error updating AI consents: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to update AI consents: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

    def _update_user_agreement(self, payload: Dict) -> Dict:
        """
        Update authenticated user's AI user agreement consent.
        Automatically sets current UTC timestamp for the consent date.
        
        Required payload keys:
        - ai_user_agreement_consent: Boolean consent for user agreement
        - ai_user_agreement_version: Version of the agreement being signed
        """
        try:
            user_id, error = self._get_authenticated_user_id(payload)
            if error:
                return error
            
            # Extract agreement data - check if nested in 'payload' key first
            agreement_data = payload
            if "payload" in payload and isinstance(payload["payload"], dict):
                # Handle case where agreement fields are nested
                agreement_data = payload["payload"]
                
            require_keys(agreement_data, ["ai_user_agreement_consent", "ai_user_agreement_version"])
            
            consent = agreement_data["ai_user_agreement_consent"]
            version = agreement_data["ai_user_agreement_version"]
            
            # Build updates with automatic timestamp
            current_utc_time = datetime.utcnow().isoformat() + "Z"
            updates = {
                "ai_user_agreement_consent": consent,
                "ai_user_agreement_consent_date": current_utc_time,
                "ai_user_agreement_version": version
            }
            
            logger.info(f"User {user_id} signing user agreement version {version} with consent: {consent}")
            
            # Call the existing update_user_profile method internally
            update_payload = {
                "user_id": user_id,
                "updates": updates,
                "auth_context": payload.get("auth_context")
            }
            
            return self._update_user_profile(update_payload)
            
        except Exception as e:
            logger.error(f"Error updating user agreement: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to update user agreement: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

    def _get_ai_consent_attributes(self, payload: Dict) -> Dict:
        """
        Get authenticated user's AI consent attributes (training, reference, marketplace).
        No payload keys required - uses authentication context.
        """
        try:
            user_id, error = self._get_authenticated_user_id(payload)
            if error:
                return error
            
            logger.info(f"Fetching AI consent attributes for user_id: {user_id}")
            
            consent_attributes = self.helper.get_ai_consent_attributes(user_id)
            
            # Handle error response from helper
            if "error" in consent_attributes:
                message, code = ResponseFormatter.extract_error_info(consent_attributes)
                return ResponseFormatter.format_error(message, ResponseFormatter.ERROR_CODES["NOT_FOUND"])
            
            # Format successful response with consent data
            return ResponseFormatter.format_success(consent_attributes)
            
        except Exception as e:
            logger.error(f"Error fetching AI consent attributes: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to fetch AI consent attributes: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

    def _get_user_agreement_attributes(self, payload: Dict) -> Dict:
        """
        Get authenticated user's agreement consent attributes.
        No payload keys required - uses authentication context.
        """
        try:
            user_id, error = self._get_authenticated_user_id(payload)
            if error:
                return error
            
            logger.info(f"Fetching user agreement attributes for user_id: {user_id}")
            
            agreement_attributes = self.helper.get_user_agreement_attributes(user_id)
            
            # Handle error response from helper
            if "error" in agreement_attributes:
                message, code = ResponseFormatter.extract_error_info(agreement_attributes)
                return ResponseFormatter.format_error(message, ResponseFormatter.ERROR_CODES["NOT_FOUND"])
            
            # Format successful response with agreement data
            return ResponseFormatter.format_success(agreement_attributes)
            
        except Exception as e:
            logger.error(f"Error fetching user agreement attributes: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to fetch user agreement attributes: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

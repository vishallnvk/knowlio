from typing import Dict

from helpers.common_helper.common_helper import require_keys, Retry
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.auth_helper import require_role, get_authenticated_user_id
from helpers.common_helper.auth_context import AuthContext
from helpers.app_logic_helpers.license_helper import LicenseHelper
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor

logger = LoggerHelper(__name__).get_logger()


@ProcessorRegistry.register("license")
class LicenseProcessor(BaseProcessor):
    def __init__(self):
        self.helper = LicenseHelper()
        super().__init__({
            "create_license": self._create_license,
            "get_license": self._get_license,
            "search_licenses": self._search_licenses,
            "revoke_license": self._revoke_license,
        })

    def _create_license(self, payload: Dict) -> Dict:
        try:
            require_keys(payload, ["content_id", "publisher_id", "consumer_id", "license_terms"])
            
            # Add authenticated user info for audit trail
            auth_context = AuthContext.from_payload(payload)
            if auth_context.is_authenticated():
                # Add creator information to license metadata
                if "metadata" not in payload:
                    payload["metadata"] = {}
                
                payload["metadata"]["created_by"] = auth_context.user_id
                payload["metadata"]["created_at"] = Retry.get_iso_timestamp()
                logger.info(f"User {auth_context.user_id} ({auth_context.role}) creating license for consumer {payload['consumer_id']}")
            
            return self.helper.create_license(payload)
        except Exception as e:
            logger.error(f"Error creating license: {str(e)}")
            return {"error": f"Failed to create license: {str(e)}"}

    def _get_license(self, payload: Dict) -> Dict:
        try:
            require_keys(payload, ["license_id"])
            
            # Get user context for potential authorization checks
            auth_context = AuthContext.from_payload(payload)
            license_data = self.helper.get_license(payload["license_id"])
            
            # If no data found or error occurred
            if not license_data or "error" in license_data:
                return license_data or {"error": f"License not found with ID: {payload['license_id']}"}
            
            # If user is a consumer, verify they can access this license
            if auth_context.is_authenticated() and auth_context.role == "CONSUMER":
                if license_data.get("consumer_id") != auth_context.user_id:
                    logger.warning(f"User {auth_context.user_id} attempted to access license {payload['license_id']} belonging to another consumer")
                    return {"error": "You do not have permission to access this license"}
            
            return license_data
        except Exception as e:
            logger.error(f"Error retrieving license: {str(e)}")
            return {"error": f"Failed to retrieve license: {str(e)}"}

    def _search_licenses(self, payload: Dict) -> Dict:
        """
        Unified search method for licenses with flexible parameters and pagination.
        
        Args:
            payload: Dictionary with search parameters and pagination options:
                - Any license field for filtering (consumer_id, content_id, publisher_id, status, etc.)
                - limit: Maximum number of items to return
                - pagination_token: Token for retrieving the next page of results
                - attributes: Optional dictionary with search parameters (alternative format)
                
        Returns:
            Dictionary with search results and pagination information
        """
        try:
            # Extract pagination parameters
            limit = payload.get("limit")
            pagination_token = payload.get("pagination_token")
            
            # Create search parameters from payload (remove pagination parameters)
            search_params = payload.copy()
            search_params.pop("limit", None)
            search_params.pop("pagination_token", None)
            search_params.pop("__action__", None)
            
            # Check for attributes format (for consistency with content search)
            if "attributes" in payload:
                attributes = payload.get("attributes")
                if not isinstance(attributes, dict):
                    return {"error": "The 'attributes' field must be a dictionary of attribute-value pairs"}
                search_params = attributes.copy()
            
            # Get authenticated user from context
            auth_context = AuthContext.from_payload(payload)
            
            # Apply role-based filtering
            if auth_context.is_authenticated():
                # If consumer role, restrict to only their licenses
                if auth_context.role == "CONSUMER":
                    # Override any consumer_id in search to ensure they only see their own licenses
                    search_params["consumer_id"] = auth_context.user_id
                    logger.info(f"Restricting license search for consumer {auth_context.user_id}")
            
            # Execute search with the provided parameters
            search_result = self.helper.search_licenses(
                search_params=search_params,
                limit=limit,
                pagination_token=pagination_token
            )
            
            # Handle error case
            if "error" in search_result:
                return {"error": search_result["error"]}
            
            # Convert result structure to standardized format including pagination
            response = {
                "licenses": search_result.get("items", []),
                "count": search_result.get("count", 0),
                "total_scanned": search_result.get("total_scanned", 0)
            }
            
            # Include pagination information directly in response
            if "pagination" in search_result:
                response["pagination"] = search_result["pagination"]
                
            return response
        except Exception as e:
            logger.error(f"Error searching licenses: {str(e)}")
            return {"error": f"Failed to search licenses: {str(e)}"}

    @require_role(["ADMIN", "PUBLISHER"])
    def _revoke_license(self, payload: Dict) -> Dict:
        try:
            require_keys(payload, ["license_id"])
            
            # Add authenticated user info for audit trail
            user_id = get_authenticated_user_id(payload)
            revocation_data = {}
            
            if user_id:
                revocation_data["revoked_by"] = user_id
                revocation_data["revoked_at"] = Retry.get_iso_timestamp()
                logger.info(f"User {user_id} revoking license {payload['license_id']}")
            
            # Pass revocation data to helper
            return self.helper.revoke_license(payload["license_id"], revocation_data)
        except Exception as e:
            logger.error(f"Error revoking license: {str(e)}")
            return {"error": f"Failed to revoke license: {str(e)}"}

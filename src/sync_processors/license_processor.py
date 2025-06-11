from typing import Dict

from helpers.common_helper.common_helper import require_keys
from helpers.common_helper.logger_helper import LoggerHelper
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
        require_keys(payload, ["content_id", "publisher_id", "consumer_id", "license_terms"])
        return self.helper.create_license(payload)

    def _get_license(self, payload: Dict) -> Dict:
        require_keys(payload, ["license_id"])
        return self.helper.get_license(payload["license_id"])

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

    def _revoke_license(self, payload: Dict) -> Dict:
        require_keys(payload, ["license_id"])
        return self.helper.revoke_license(payload["license_id"])

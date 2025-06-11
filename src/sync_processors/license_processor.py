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
            "list_licenses_by_consumer": self._list_licenses_by_consumer,
            "list_licenses_by_content": self._list_licenses_by_content,
            "revoke_license": self._revoke_license,
        })

    def _create_license(self, payload: Dict) -> Dict:
        require_keys(payload, ["content_id", "publisher_id", "consumer_id", "license_terms"])
        return self.helper.create_license(payload)

    def _get_license(self, payload: Dict) -> Dict:
        require_keys(payload, ["license_id"])
        return self.helper.get_license(payload["license_id"])

    def _list_licenses_by_consumer(self, payload: Dict) -> Dict:
        require_keys(payload, ["consumer_id"])
        
        # Extract pagination parameters
        limit = payload.get("limit")
        pagination_token = payload.get("pagination_token")
        
        # Call helper with pagination parameters
        result = self.helper.list_licenses_by_consumer(
            consumer_id=payload["consumer_id"],
            limit=limit,
            pagination_token=pagination_token
        )
        
        # Format response with consistent structure
        response = {
            "licenses": result.get("items", []),
            "count": result.get("count", 0)
        }
        
        # Include pagination information 
        if "pagination" in result:
            response["pagination"] = result["pagination"]
            
        return response

    def _list_licenses_by_content(self, payload: Dict) -> Dict:
        require_keys(payload, ["content_id"])
        
        # Extract pagination parameters
        limit = payload.get("limit")
        pagination_token = payload.get("pagination_token")
        
        # Call helper with pagination parameters
        result = self.helper.list_licenses_by_content(
            content_id=payload["content_id"],
            limit=limit,
            pagination_token=pagination_token
        )
        
        # Format response with consistent structure
        response = {
            "licenses": result.get("items", []),
            "count": result.get("count", 0)
        }
        
        # Include pagination information
        if "pagination" in result:
            response["pagination"] = result["pagination"]
            
        return response

    def _revoke_license(self, payload: Dict) -> Dict:
        require_keys(payload, ["license_id"])
        return self.helper.revoke_license(payload["license_id"])

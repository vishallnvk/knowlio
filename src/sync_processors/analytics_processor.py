from typing import Dict

from helpers.app_logic_helpers.analytics_helper import AnalyticsHelper
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.auth_helper import require_role, get_authenticated_user_id
from helpers.common_helper.auth_context import AuthContext
from helpers.common_helper.common_helper import Retry
from helpers.common_helper.response_formatter import ResponseFormatter
from sync_processor_registry.processor_registry import ProcessorRegistry
from sync_processors.base_processor import BaseProcessor

logger = LoggerHelper(__name__).get_logger()

@ProcessorRegistry.register("analytics")
class AnalyticsProcessor(BaseProcessor):
    def __init__(self):
        self.helper = AnalyticsHelper()
        super().__init__({
            "log_content_access": self._log_content_access,
            "get_usage_report_by_content": self._get_usage_report_by_content,
            "get_usage_report_by_consumer": self._get_usage_report_by_consumer,
            "export_usage_logs": self._export_usage_logs,
        })

    def _log_content_access(self, payload: Dict) -> Dict:
        """Log content access by a consumer"""
        logger.info("Processing log_content_access request")
        
        try:
            # Add authenticated user info for audit trail
            auth_context = AuthContext.from_payload(payload)
            if auth_context.is_authenticated():
                # Add user information to analytics log
                if "metadata" not in payload:
                    payload["metadata"] = {}
                
                payload["metadata"]["logged_by"] = auth_context.user_id
                payload["metadata"]["logged_at"] = Retry.get_iso_timestamp()
                
                # If consumer_id is not provided, use the authenticated user ID
                if "consumer_id" not in payload and auth_context.role == "CONSUMER":
                    payload["consumer_id"] = auth_context.user_id
                    logger.info(f"Using authenticated user {auth_context.user_id} as consumer_id for analytics")
            
            result = self.helper.log_content_access(payload)
            
            # Handle error response from helper
            if "error" in result:
                message, code = ResponseFormatter.extract_error_info(result)
                return ResponseFormatter.format_error(message, code)
            
            # Format successful create response
            return ResponseFormatter.format_create_response(
                resource_type="usage_log",
                resource_id=result.get("log_id"),
                resource_data=result
            )
        except Exception as e:
            logger.error(f"Error logging content access: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to log content access: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

    @require_role(["ADMIN", "PUBLISHER"])
    def _get_usage_report_by_content(self, payload: Dict) -> Dict:
        """
        Get usage report for a specific content item
        Requires ADMIN or PUBLISHER role
        """
        logger.info("Processing get_usage_report_by_content request")
        try:
            content_id = payload.get("content_id")
            if not content_id:
                return ResponseFormatter.format_error(
                    "content_id is required for usage report",
                    ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"],
                    field="content_id"
                )
            
            # Log who accessed the report
            user_id = get_authenticated_user_id(payload)
            logger.info(f"User {user_id} accessing content usage report for {content_id}")
            
            result = self.helper.get_usage_report_by_content(content_id)
            
            # Handle error response from helper
            if "error" in result:
                message, code = ResponseFormatter.extract_error_info(result)
                return ResponseFormatter.format_error(message, code)
            
            # Format successful response with report data
            return ResponseFormatter.format_success(result)
        except Exception as e:
            logger.error(f"Error getting usage report by content: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to get usage report: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

    def _get_usage_report_by_consumer(self, payload: Dict) -> Dict:
        """Get usage report for a specific consumer"""
        logger.info("Processing get_usage_report_by_consumer request")
        try:
            consumer_id = payload.get("consumer_id")
            if not consumer_id:
                return ResponseFormatter.format_error(
                    "consumer_id is required for usage report",
                    ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"],
                    field="consumer_id"
                )
            
            # Get authenticated user context
            auth_context = AuthContext.from_payload(payload)
            
            # Verify authorization - admin can access any report, consumers can only access their own
            if auth_context.is_authenticated():
                if auth_context.role == "CONSUMER" and consumer_id != auth_context.user_id:
                    logger.warning(f"User {auth_context.user_id} attempted to access usage report for another consumer: {consumer_id}")
                    return ResponseFormatter.format_error(
                        "You do not have permission to access this consumer's usage report",
                        ResponseFormatter.ERROR_CODES["FORBIDDEN"]
                    )
                
                logger.info(f"User {auth_context.user_id} ({auth_context.role}) accessing consumer usage report for {consumer_id}")
            
            result = self.helper.get_usage_report_by_consumer(consumer_id)
            
            # Handle error response from helper
            if "error" in result:
                message, code = ResponseFormatter.extract_error_info(result)
                return ResponseFormatter.format_error(message, code)
            
            # Format successful response with report data
            return ResponseFormatter.format_success(result)
        except Exception as e:
            logger.error(f"Error getting usage report by consumer: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to get usage report: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

    @require_role("ADMIN")
    def _export_usage_logs(self, payload: Dict) -> Dict:
        """
        Export usage logs to S3
        Requires ADMIN role
        """
        logger.info("Processing export_usage_logs request")
        try:
            # Add audit information
            user_id = get_authenticated_user_id(payload)
            if user_id:
                if "metadata" not in payload:
                    payload["metadata"] = {}
                
                payload["metadata"]["exported_by"] = user_id
                payload["metadata"]["exported_at"] = Retry.get_iso_timestamp()
                logger.info(f"User {user_id} exporting usage logs")
            
            result = self.helper.export_usage_logs(payload)
            
            # Handle error response from helper
            if "error" in result:
                message, code = ResponseFormatter.extract_error_info(result)
                return ResponseFormatter.format_error(message, code)
            
            # Format successful response
            return ResponseFormatter.format_success(result)
        except Exception as e:
            logger.error(f"Error exporting usage logs: {str(e)}")
            return ResponseFormatter.format_error(f"Failed to export usage logs: {str(e)}", 
                                               ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])

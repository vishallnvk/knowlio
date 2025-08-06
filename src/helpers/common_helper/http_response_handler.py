"""
Reusable HTTP Response Handler for API Gateway.
Provides standardized HTTP status code mapping and error detection.
Built with Google-level engineering standards for modularity and reusability.
"""

from typing import Dict, Any, Optional
from enum import Enum
import logging

from .response_formatter import ResponseFormatter


class HttpStatusCode(Enum):
    """HTTP status codes for API responses."""
    OK = 200
    CREATED = 201
    NO_CONTENT = 204
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    INTERNAL_SERVER_ERROR = 500
    BAD_GATEWAY = 502
    SERVICE_UNAVAILABLE = 503


class HttpResponseHandler:
    """
    Centralized HTTP response handler with error detection and status code mapping.
    
    This class provides a standardized way to:
    1. Detect processor error responses
    2. Map error codes to appropriate HTTP status codes
    3. Create consistent HTTP responses with proper headers
    4. Log response details for debugging
    """
    
    # Mapping of error codes to HTTP status codes
    ERROR_CODE_TO_HTTP_STATUS = {
        ResponseFormatter.ERROR_CODES["VALIDATION_ERROR"]: HttpStatusCode.BAD_REQUEST,
        ResponseFormatter.ERROR_CODES["BAD_REQUEST"]: HttpStatusCode.BAD_REQUEST,
        ResponseFormatter.ERROR_CODES["UNAUTHORIZED"]: HttpStatusCode.UNAUTHORIZED,
        ResponseFormatter.ERROR_CODES["FORBIDDEN"]: HttpStatusCode.FORBIDDEN,
        ResponseFormatter.ERROR_CODES["NOT_FOUND"]: HttpStatusCode.NOT_FOUND,
        ResponseFormatter.ERROR_CODES["CONFLICT"]: HttpStatusCode.CONFLICT,
        ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"]: HttpStatusCode.INTERNAL_SERVER_ERROR,
    }
    
    # Default HTTP status for unknown error codes
    DEFAULT_ERROR_STATUS = HttpStatusCode.INTERNAL_SERVER_ERROR
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the HTTP response handler.
        
        Args:
            logger: Optional logger instance for request/response logging
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def is_processor_error_response(self, processor_result: Dict[str, Any]) -> bool:
        """
        Detect if a processor result represents an error response.
        
        Args:
            processor_result: The result returned by a processor
            
        Returns:
            True if the result represents an error, False otherwise
        """
        # Check for standardized error format
        if isinstance(processor_result, dict):
            # Standard format: {"success": false, "error": {...}}
            if processor_result.get("success") is False:
                return True
            
            # Legacy format: {"error": "..."}
            if "error" in processor_result:
                return True
            
            # Check for error indicators in nested responses
            if "data" in processor_result:
                data = processor_result["data"]
                if isinstance(data, dict) and data.get("success") is False:
                    return True
        
        return False
    
    def extract_error_details(self, processor_result: Dict[str, Any]) -> tuple[str, str, Optional[str]]:
        """
        Extract error details from a processor error response.
        
        Args:
            processor_result: The error response from a processor
            
        Returns:
            Tuple of (error_message, error_code, optional_field)
        """
        # Handle standardized error format
        if "error" in processor_result and isinstance(processor_result["error"], dict):
            error_dict = processor_result["error"]
            message = error_dict.get("message", "Unknown error occurred")
            code = error_dict.get("code", ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"])
            field = error_dict.get("field")
            return message, code, field
        
        # Handle legacy error format
        if "error" in processor_result:
            error_msg = str(processor_result["error"])
            return error_msg, ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"], None
        
        # Handle nested data errors
        if "data" in processor_result:
            data = processor_result["data"]
            if isinstance(data, dict) and "error" in data:
                return self.extract_error_details(data)
        
        # Default error
        return "An unknown error occurred", ResponseFormatter.ERROR_CODES["INTERNAL_ERROR"], None
    
    def get_http_status_for_error_code(self, error_code: str) -> HttpStatusCode:
        """
        Map an error code to the appropriate HTTP status code.
        
        Args:
            error_code: The error code from the processor
            
        Returns:
            The corresponding HTTP status code
        """
        return self.ERROR_CODE_TO_HTTP_STATUS.get(error_code, self.DEFAULT_ERROR_STATUS)
    
    def create_http_response(self, processor_result: Dict[str, Any], 
                           request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a standardized HTTP response from a processor result.
        
        Args:
            processor_result: The result returned by a processor
            request_id: Optional request ID for tracking
            
        Returns:
            HTTP response dictionary with proper status code and headers
        """
        # Check if this is an error response
        if self.is_processor_error_response(processor_result):
            return self._create_error_response(processor_result, request_id)
        else:
            return self._create_success_response(processor_result, request_id)
    
    def _create_success_response(self, processor_result: Dict[str, Any], 
                               request_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a successful HTTP response."""
        # Determine the appropriate success status code
        # For create operations, return 201; otherwise 200
        status_code = HttpStatusCode.CREATED.value if self._is_create_operation(processor_result) else HttpStatusCode.OK.value
        
        response = {
            "statusCode": status_code,
            "headers": self._get_cors_headers(),
            "body": self._serialize_response_body(processor_result)
        }
        
        self.logger.info(f"Success response: {status_code} - Request ID: {request_id}")
        return response
    
    def _create_error_response(self, processor_result: Dict[str, Any], 
                             request_id: Optional[str] = None) -> Dict[str, Any]:
        """Create an error HTTP response."""
        error_message, error_code, field = self.extract_error_details(processor_result)
        http_status = self.get_http_status_for_error_code(error_code)
        
        # Create a standardized error response body
        error_response = ResponseFormatter.format_error(
            message=error_message,
            code=error_code,
            field=field,
            request_id=request_id
        )
        
        response = {
            "statusCode": http_status.value,
            "headers": self._get_cors_headers(),
            "body": self._serialize_response_body(error_response)
        }
        
        self.logger.error(f"Error response: {http_status.value} - {error_code}: {error_message} - Request ID: {request_id}")
        return response
    
    def _is_create_operation(self, processor_result: Dict[str, Any]) -> bool:
        """Check if the processor result represents a create operation."""
        if isinstance(processor_result, dict):
            data = processor_result.get("data", {})
            if isinstance(data, dict):
                # Check for create response indicators
                return "created successfully" in data.get("message", "").lower()
        return False
    
    def _get_cors_headers(self) -> Dict[str, str]:
        """Get standard CORS headers for API responses."""
        return {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS,PATCH"
        }
    
    def _serialize_response_body(self, response_data: Any) -> str:
        """Serialize response data to JSON string."""
        import json
        return json.dumps(response_data, default=str)


class HttpResponseHandlerFactory:
    """
    Factory class for creating HTTP response handlers.
    Provides singleton pattern for efficient reuse.
    """
    
    _instance: Optional[HttpResponseHandler] = None
    
    @classmethod
    def get_instance(cls, logger: Optional[logging.Logger] = None) -> HttpResponseHandler:
        """
        Get a singleton instance of HttpResponseHandler.
        
        Args:
            logger: Optional logger instance
            
        Returns:
            HttpResponseHandler instance
        """
        if cls._instance is None:
            cls._instance = HttpResponseHandler(logger)
        return cls._instance
    
    @classmethod
    def create_response(cls, processor_result: Dict[str, Any], 
                       request_id: Optional[str] = None,
                       logger: Optional[logging.Logger] = None) -> Dict[str, Any]:
        """
        Convenience method to create HTTP response.
        
        Args:
            processor_result: The result returned by a processor
            request_id: Optional request ID for tracking
            logger: Optional logger instance
            
        Returns:
            HTTP response dictionary
        """
        handler = cls.get_instance(logger)
        return handler.create_http_response(processor_result, request_id)

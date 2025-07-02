"""
Standardized response formatter for API responses.
Ensures consistent response structure across all processors.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class ResponseFormatter:
    """
    Utility class for formatting standardized API responses.
    
    Success Response Structure:
    {
        "success": true,
        "data": {...},
        "metadata": {
            "timestamp": "ISO-8601 timestamp",
            "request_id": "unique request id"
        }
    }
    
    Error Response Structure:
    {
        "success": false,
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable error message",
            "field": "field_name"  # Optional
        },
        "metadata": {
            "timestamp": "ISO-8601 timestamp",
            "request_id": "unique request id"
        }
    }
    """
    
    # Standard error codes
    ERROR_CODES = {
        "VALIDATION_ERROR": "VALIDATION_ERROR",
        "NOT_FOUND": "NOT_FOUND",
        "UNAUTHORIZED": "UNAUTHORIZED",
        "FORBIDDEN": "FORBIDDEN",
        "CONFLICT": "CONFLICT",
        "INTERNAL_ERROR": "INTERNAL_ERROR",
        "BAD_REQUEST": "BAD_REQUEST"
    }
    
    @staticmethod
    def format_success(data: Any, pagination: Optional[Dict] = None, 
                      request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Format a successful response.
        
        Args:
            data: The response data (can be dict, list, or primitive)
            pagination: Optional pagination metadata for list operations
            request_id: Optional request ID for tracking
            
        Returns:
            Standardized success response dictionary
        """
        metadata = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": request_id or str(uuid.uuid4())
        }
        
        if pagination:
            metadata["pagination"] = pagination
            
        return {
            "success": True,
            "data": data,
            "metadata": metadata
        }
    
    @staticmethod
    def format_error(message: str, code: str = "INTERNAL_ERROR", 
                    field: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Format an error response.
        
        Args:
            message: Human-readable error message
            code: Error code (should use ERROR_CODES constants)
            field: Optional field name for field-specific errors
            request_id: Optional request ID for tracking
            
        Returns:
            Standardized error response dictionary
        """
        error_data = {
            "code": code,
            "message": message
        }
        
        if field:
            error_data["field"] = field
            
        return {
            "success": False,
            "error": error_data,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "request_id": request_id or str(uuid.uuid4())
            }
        }
    
    @staticmethod
    def format_list_response(items: List[Any], count: int, total_scanned: int = None,
                           pagination_token: Optional[str] = None, has_more: bool = False,
                           request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Format a list/search response with standardized structure.
        
        Args:
            items: List of items
            count: Number of items returned
            total_scanned: Total number of items scanned (optional)
            pagination_token: Token for next page (optional)
            has_more: Whether more results are available
            request_id: Optional request ID for tracking
            
        Returns:
            Standardized list response dictionary
        """
        data = {
            "items": items,
            "count": count
        }
        
        if total_scanned is not None:
            data["total_scanned"] = total_scanned
            
        pagination = None
        if pagination_token or has_more:
            pagination = {
                "has_more": has_more
            }
            if pagination_token:
                pagination["next_token"] = pagination_token
                
        return ResponseFormatter.format_success(data, pagination, request_id)
    
    @staticmethod
    def format_create_response(resource_type: str, resource_id: str, 
                             resource_data: Optional[Dict] = None,
                             request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Format a create operation response.
        
        Args:
            resource_type: Type of resource created (e.g., "content", "user", "license")
            resource_id: ID of the created resource
            resource_data: Optional full resource data
            request_id: Optional request ID for tracking
            
        Returns:
            Standardized create response dictionary
        """
        data = {
            "id": resource_id,
            "type": resource_type,
            "message": f"{resource_type.capitalize()} created successfully"
        }
        
        if resource_data:
            data["resource"] = resource_data
            
        return ResponseFormatter.format_success(data, request_id=request_id)
    
    @staticmethod
    def format_update_response(resource_type: str, resource_id: str,
                             updated_resource: Dict,
                             request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Format an update operation response.
        
        Args:
            resource_type: Type of resource updated
            resource_id: ID of the updated resource
            updated_resource: Full updated resource data
            request_id: Optional request ID for tracking
            
        Returns:
            Standardized update response dictionary
        """
        data = {
            "id": resource_id,
            "type": resource_type,
            "message": f"{resource_type.capitalize()} updated successfully",
            "resource": updated_resource
        }
        
        return ResponseFormatter.format_success(data, request_id=request_id)
    
    @staticmethod
    def format_delete_response(resource_type: str, resource_id: str,
                             request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Format a delete/archive operation response.
        
        Args:
            resource_type: Type of resource deleted/archived
            resource_id: ID of the deleted/archived resource
            request_id: Optional request ID for tracking
            
        Returns:
            Standardized delete response dictionary
        """
        data = {
            "id": resource_id,
            "type": resource_type,
            "message": f"{resource_type.capitalize()} deleted successfully"
        }
        
        return ResponseFormatter.format_success(data, request_id=request_id)
    
    @staticmethod
    def extract_error_info(error_response: Dict) -> tuple[str, str]:
        """
        Extract error message and code from various error response formats.
        
        Args:
            error_response: Error response dictionary
            
        Returns:
            Tuple of (error_message, error_code)
        """
        # Handle already formatted errors
        if "error" in error_response and isinstance(error_response["error"], dict):
            error_dict = error_response["error"]
            return error_dict.get("message", "Unknown error"), error_dict.get("code", "INTERNAL_ERROR")
            
        # Handle simple error format
        if "error" in error_response:
            return str(error_response["error"]), "INTERNAL_ERROR"
            
        # Handle message format
        if "message" in error_response:
            return error_response["message"], "INTERNAL_ERROR"
            
        # Default
        return "An unknown error occurred", "INTERNAL_ERROR"

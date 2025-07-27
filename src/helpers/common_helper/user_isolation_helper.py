"""
Reusable user isolation helper for ensuring data access is properly scoped to users.
This module provides a unified approach to user isolation across all processors.
"""

from typing import Dict, Any, Optional, List
from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.auth_context import AuthContext
from helpers.common_helper.response_formatter import ResponseFormatter

logger = LoggerHelper(__name__).get_logger()


class UserIsolationHelper:
    """
    Centralized helper for implementing user isolation across all processors.
    Provides reusable methods for applying user-specific filters and validations.
    """
    
    @staticmethod
    def apply_user_isolation(search_params: Dict[str, Any], auth_context: AuthContext) -> Dict[str, Any]:
        """
        Apply user isolation filters to search parameters based on user role.
        
        Args:
            search_params: Dictionary of search parameters to filter
            auth_context: User authentication context
            
        Returns:
            Modified search parameters with user isolation applied
        """
        if not auth_context.is_authenticated():
            return search_params
        
        user_id = auth_context.user_id
        role = auth_context.role
        
        # Apply role-based isolation
        if role == "CONSUMER":
            # Consumers can only see their own data
            search_params["consumer_id"] = user_id
            logger.info(f"Applied consumer isolation for user {user_id}")
            
        elif role == "PUBLISHER":
            # Publishers can only see data they own or created
            search_params["publisher_id"] = user_id
            logger.info(f"Applied publisher isolation for user {user_id}")
            
        elif role == "ADMIN":
            # Admins can see all data - no isolation needed
            logger.info(f"Admin user {user_id} - no isolation applied")
            
        return search_params
    
    @staticmethod
    def validate_ownership(resource_data: Dict[str, Any], auth_context: AuthContext, 
                          resource_type: str = "resource") -> Optional[Dict[str, Any]]:
        """
        Validate that the authenticated user has permission to access the resource.
        
        Args:
            resource_data: The resource data to validate
            auth_context: User authentication context
            resource_type: Type of resource for error messages
            
        Returns:
            None if validation passes, error response if validation fails
        """
        if not auth_context.is_authenticated():
            return ResponseFormatter.format_error(
                "Authentication required", 
                ResponseFormatter.ERROR_CODES["UNAUTHORIZED"]
            )
        
        user_id = auth_context.user_id
        role = auth_context.role
        
        # Admin can access everything
        if role == "ADMIN":
            return None
        
        # Check ownership based on role
        if role == "CONSUMER":
            if resource_data.get("consumer_id") != user_id:
                logger.warning(f"Consumer {user_id} attempted to access {resource_type} belonging to another user")
                return ResponseFormatter.format_error(
                    f"You do not have permission to access this {resource_type}",
                    ResponseFormatter.ERROR_CODES["FORBIDDEN"]
                )
                
        elif role == "PUBLISHER":
            # Publishers can access resources they own or created
            if (resource_data.get("publisher_id") != user_id and 
                resource_data.get("created_by") != user_id):
                logger.warning(f"Publisher {user_id} attempted to access {resource_type} belonging to another user")
                return ResponseFormatter.format_error(
                    f"You do not have permission to access this {resource_type}",
                    ResponseFormatter.ERROR_CODES["FORBIDDEN"]
                )
        
        return None
    
    @staticmethod
    def validate_creation_permission(payload: Dict[str, Any], auth_context: AuthContext) -> Optional[Dict[str, Any]]:
        """
        Validate that the authenticated user has permission to create the resource.
        
        Args:
            payload: The creation payload
            auth_context: User authentication context
            
        Returns:
            None if validation passes, error response if validation fails
        """
        if not auth_context.is_authenticated():
            return ResponseFormatter.format_error(
                "Authentication required", 
                ResponseFormatter.ERROR_CODES["UNAUTHORIZED"]
            )
        
        user_id = auth_context.user_id
        role = auth_context.role
        
        # Admin can create anything
        if role == "ADMIN":
            return None
        
        # Publishers can only create resources for themselves
        if role == "PUBLISHER":
            if payload.get("publisher_id") and payload.get("publisher_id") != user_id:
                logger.warning(f"Publisher {user_id} attempted to create resource for another publisher")
                return ResponseFormatter.format_error(
                    "You can only create resources for yourself",
                    ResponseFormatter.ERROR_CODES["FORBIDDEN"]
                )
        
        # Consumers typically can't create resources (except licenses they purchase)
        elif role == "CONSUMER":
            if payload.get("consumer_id") and payload.get("consumer_id") != user_id:
                logger.warning(f"Consumer {user_id} attempted to create resource for another consumer")
                return ResponseFormatter.format_error(
                    "You can only create resources for yourself",
                    ResponseFormatter.ERROR_CODES["FORBIDDEN"]
                )
        
        return None
    
    @staticmethod
    def add_user_metadata(payload: Dict[str, Any], auth_context: AuthContext) -> Dict[str, Any]:
        """
        Add user metadata to creation/update payloads for audit trails.
        
        Args:
            payload: The payload to enhance
            auth_context: User authentication context
            
        Returns:
            Enhanced payload with user metadata
        """
        if not auth_context.is_authenticated():
            return payload
        
        user_id = auth_context.user_id
        role = auth_context.role
        
        # Initialize metadata if not present
        if "metadata" not in payload:
            payload["metadata"] = {}
        
        # Add user information
        payload["metadata"]["user_id"] = user_id
        payload["metadata"]["user_role"] = role
        
        return payload
    
    @staticmethod
    def filter_sensitive_data(data: Dict[str, Any], auth_context: AuthContext) -> Dict[str, Any]:
        """
        Filter sensitive data based on user role and permissions.
        
        Args:
            data: The data to filter
            auth_context: User authentication context
            
        Returns:
            Filtered data with sensitive information removed if necessary
        """
        if not auth_context.is_authenticated():
            return data
        
        # Admin can see everything
        if auth_context.role == "ADMIN":
            return data
        
        # Remove sensitive fields for non-admin users
        filtered_data = data.copy()
        
        # Remove internal system fields
        sensitive_fields = ["internal_notes", "system_metadata", "admin_comments"]
        for field in sensitive_fields:
            filtered_data.pop(field, None)
        
        return filtered_data
    
    @staticmethod
    def get_user_specific_index_name(base_index: str, user_id: str) -> str:
        """
        Generate user-specific index name for data isolation.
        
        Args:
            base_index: Base index name
            user_id: User identifier
            
        Returns:
            User-specific index name
        """
        return f"{base_index}_{user_id}"
    
    @staticmethod
    def validate_bulk_operation_permissions(items: List[Dict[str, Any]], auth_context: AuthContext, 
                                          resource_type: str = "resource") -> Optional[Dict[str, Any]]:
        """
        Validate permissions for bulk operations.
        
        Args:
            items: List of items to validate
            auth_context: User authentication context
            resource_type: Type of resource for error messages
            
        Returns:
            None if validation passes, error response if validation fails
        """
        for item in items:
            error = UserIsolationHelper.validate_ownership(item, auth_context, resource_type)
            if error:
                return error
        
        return None

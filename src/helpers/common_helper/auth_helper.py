"""
Authorization helper for role-based access control and other security features.
Can be used across different modules to enforce consistent access control policies.
"""

import functools
from typing import Dict, List, Callable, Any, Optional, Union, Set

from helpers.common_helper.logger_helper import LoggerHelper
from helpers.common_helper.auth_context import AuthContext, AuthContextService

logger = LoggerHelper(__name__).get_logger()

class AuthorizationError(Exception):
    """Exception raised for authorization failures."""
    pass

class RoleBasedAuth:
    """
    Decoupled role-based authorization system that can be used across different features.
    Provides decorators and utilities for enforcing role-based access control.
    """
    
    # Role hierarchy (higher roles include permissions of lower roles)
    ROLE_HIERARCHY = {
        "ADMIN": {"PUBLISHER", "CONSUMER"},
        "PUBLISHER": set(),
        "CONSUMER": set(),
    }
    
    # Standard role definitions
    VALID_ROLES = {"ADMIN", "PUBLISHER", "CONSUMER"}
    
    @classmethod
    def validate_role(cls, role: str) -> bool:
        """
        Validates if a role is recognized by the system.
        
        Args:
            role: Role name to validate
            
        Returns:
            Boolean indicating if role is valid
        """
        return role in cls.VALID_ROLES
    
    @classmethod
    def has_permission(cls, user_role: str, required_role: str) -> bool:
        """
        Check if a user with the given role has permissions of the required role.
        
        Args:
            user_role: The role of the user
            required_role: The role required for the operation
            
        Returns:
            Boolean indicating if the user has necessary permission
        """
        # Same role always has permission
        if user_role == required_role:
            return True
            
        # Check role hierarchy
        if user_role in cls.ROLE_HIERARCHY:
            if required_role in cls.ROLE_HIERARCHY[user_role]:
                return True
                
        return False
    
    @classmethod
    def get_user_permissions(cls, role: str) -> Set[str]:
        """
        Get all permissions/roles a user with the given role has.
        
        Args:
            role: The role of the user
            
        Returns:
            Set of all roles the user inherits permissions from
        """
        permissions = {role}  # User always has their own role
        
        # Add inherited permissions
        if role in cls.ROLE_HIERARCHY:
            permissions.update(cls.ROLE_HIERARCHY[role])
            
        return permissions
    
    @staticmethod
    def require_role(required_roles: Union[str, List[str]]):
        """
        Decorator to enforce role-based access control on functions.
        Works with the new AuthContext POJO.
        
        Args:
            required_roles: Single role or list of roles that are allowed to access
            
        Returns:
            Decorated function that checks role before execution
        
        Example:
        ```
        @RoleBasedAuth.require_role("ADMIN")
        def admin_operation(payload):
            # Only users with ADMIN role will reach this code
            pass
        ```
        """
        # Convert single role to list for unified handling
        if isinstance(required_roles, str):
            required_roles = [required_roles]
            
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Get auth context from payload
                auth_context = None
                
                # Check kwargs for auth_context or payload with auth_context
                if 'auth_context' in kwargs:
                    auth_context = kwargs['auth_context']
                elif 'payload' in kwargs and isinstance(kwargs['payload'], dict):
                    auth_context = AuthContext.from_payload(kwargs['payload'])
                
                # If not found in kwargs, try to find in args
                if auth_context is None:
                    for arg in args:
                        if isinstance(arg, AuthContext):
                            auth_context = arg
                            break
                        elif isinstance(arg, dict):
                            extracted = AuthContext.from_payload(arg)
                            if extracted:
                                auth_context = extracted
                                break
                
                # If we couldn't find a context or role, we can't authorize
                if auth_context is None or auth_context.role is None:
                    logger.error("Authorization failed: No user role found in arguments")
                    raise AuthorizationError("No user role provided for authorization")
                
                # Check if the user's role is in the list of required roles
                for role in required_roles:
                    if auth_context.has_permission(role):
                        return func(*args, **kwargs)
                        
                logger.warning(f"Authorization failed: User with role {auth_context.role} attempted to access function requiring roles {required_roles}")
                raise AuthorizationError(f"User with role {auth_context.role} does not have required permissions")
                
            return wrapper
        return decorator

# Convenience aliases
require_role = RoleBasedAuth.require_role
validate_role = RoleBasedAuth.validate_role

# Expose helper functions from AuthContextService for convenience
get_authenticated_user = AuthContextService.get_authenticated_user
get_authenticated_user_id = AuthContextService.get_authenticated_user_id
get_authenticated_user_role = AuthContextService.get_authenticated_user_role
ensure_authenticated = AuthContextService.ensure_authenticated
ensure_role = AuthContextService.ensure_role

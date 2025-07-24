"""
Authentication context module providing standardized access to user identity information.
This module serves as a centralized way to manage authentication across processors.
"""

from typing import Dict, List, Optional, Any, Union, Set
from helpers.common_helper.logger_helper import LoggerHelper

logger = LoggerHelper(__name__).get_logger()

class AuthContext:
    """
    Object-oriented container for authentication context passed to all processor methods.
    This class encapsulates user identity information and role details from authentication.
    """
    
    def __init__(self, user_id=None, email=None, role=None, groups=None, claims=None, 
                 first_name=None, last_name=None, name=None):
        """
        Initialize authentication context with user details.
        
        Args:
            user_id: Unique identifier for the user (from Cognito sub claim)
            email: User's email address
            role: User's primary role in the system
            groups: List of groups/roles the user belongs to
            claims: Raw claims from the JWT token (for advanced use cases)
            first_name: User's first name
            last_name: User's last name
            name: User's full display name
        """
        self.user_id = user_id
        self.email = email
        self.role = role
        self.groups = groups or []
        self.claims = claims or {}
        self.first_name = first_name
        self.last_name = last_name
        self.name = name
        self.authenticated = bool(user_id)
    
    @classmethod
    def from_cognito_claims(cls, claims):
        """
        Create AuthContext from Cognito claims dictionary.
        
        Args:
            claims: Dictionary of claims from Cognito JWT token
        
        Returns:
            AuthContext instance with populated fields
        """
        from helpers.common_helper.auth_helper import RoleBasedAuth
        
        if not claims:
            return cls()
            
        # Extract groups - could be a string or list
        groups = claims.get('cognito:groups', '')
        if isinstance(groups, str) and groups:
            groups = [g.strip() for g in groups.split(',')]
        elif not isinstance(groups, list):
            groups = []
            
        # Map primary role from groups (first group is primary role)
        role = None
        for group in groups:
            if RoleBasedAuth.validate_role(group):
                role = group
                break
            
        return cls(
            user_id=claims.get('sub'),
            email=claims.get('email'),
            role=role,
            groups=groups,
            claims=claims
        )
    
    @classmethod
    def from_user_data(cls, user_data):
        """
        Create AuthContext from userData dictionary (from api_gateway_handler).
        
        Args:
            user_data: Dictionary with user details from event['userData']
        
        Returns:
            AuthContext instance with populated fields
        """
        if not user_data:
            return cls()
            
        return cls(
            user_id=user_data.get('user_id'),
            email=user_data.get('email'),
            role=user_data.get('role') or (user_data.get('groups', [None])[0]),
            groups=user_data.get('groups', []),
            claims=user_data.get('claims', {}),
            first_name=user_data.get('first_name'),
            last_name=user_data.get('last_name'),
            name=user_data.get('name')
        )
    
    @classmethod
    def from_event(cls, event):
        """
        Create AuthContext from API Gateway event.
        
        Args:
            event: API Gateway Lambda proxy event
            
        Returns:
            AuthContext instance
        """
        from helpers.common_helper.cognito_helper import get_user_details_from_event
        
        user_details = get_user_details_from_event(event)
        return cls.from_user_data(user_details)
    
    @classmethod
    def from_payload(cls, payload):
        """
        Extract AuthContext from processor payload.
        
        Args:
            payload: Processor method payload
            
        Returns:
            AuthContext instance
        """
        # Try standard location
        if 'auth_context' in payload:
            if isinstance(payload['auth_context'], cls):
                return payload['auth_context']
            elif isinstance(payload['auth_context'], dict):
                return cls.from_user_data(payload['auth_context'])
        
        # Try legacy location
        if 'userData' in payload:
            return cls.from_user_data(payload['userData'])
            
        # Try direct user_id/role in payload (backwards compatibility)
        if 'user_id' in payload and 'role' in payload:
            return cls(
                user_id=payload['user_id'],
                role=payload['role']
            )
            
        return cls()  # Empty context if no auth info found
    
    def has_permission(self, required_role):
        """
        Check if the user has the required role.
        
        Args:
            required_role: Role to check for
            
        Returns:
            Boolean indicating if the user has the role
        """
        from helpers.common_helper.auth_helper import RoleBasedAuth
        return RoleBasedAuth.has_permission(self.role, required_role) if self.role else False
    
    def is_authenticated(self):
        """
        Check if the user is authenticated.
        
        Returns:
            Boolean indicating if the user is authenticated
        """
        return self.authenticated
        
    def to_dict(self):
        """
        Convert AuthContext to a dictionary.
        
        Returns:
            Dictionary representation of AuthContext
        """
        return {
            'user_id': self.user_id,
            'email': self.email,
            'role': self.role,
            'groups': self.groups,
            'authenticated': self.authenticated,
            'claims': self.claims
        }


class AuthContextService:
    """
    Service class providing authentication utilities for processors.
    These utilities help with extracting user information from payloads
    and enforcing access control.
    """
    
    @staticmethod
    def get_authenticated_user(payload):
        """
        Get authenticated user context from payload.
        
        Args:
            payload: Processor method payload
            
        Returns:
            AuthContext object
        """
        return AuthContext.from_payload(payload)
    
    @staticmethod
    def get_authenticated_user_id(payload):
        """
        Extract authenticated user ID from payload.
        
        Args:
            payload: Processor method payload
            
        Returns:
            User ID or None if not authenticated
        """
        auth_context = AuthContext.from_payload(payload)
        return auth_context.user_id if auth_context and auth_context.is_authenticated() else None
    
    @staticmethod
    def get_authenticated_user_role(payload):
        """
        Extract authenticated user role from payload.
        
        Args:
            payload: Processor method payload
            
        Returns:
            User role or None if not authenticated
        """
        auth_context = AuthContext.from_payload(payload)
        return auth_context.role if auth_context and auth_context.is_authenticated() else None
        
    @staticmethod
    def ensure_authenticated(payload):
        """
        Ensure the request comes from an authenticated user.
        
        Args:
            payload: Processor method payload
            
        Raises:
            AuthorizationError: If user is not authenticated
        """
        from helpers.common_helper.auth_helper import AuthorizationError
        
        auth_context = AuthContext.from_payload(payload)
        if not auth_context.is_authenticated():
            raise AuthorizationError("This operation requires authentication")
    
    @staticmethod
    def ensure_role(payload, required_role):
        """
        Ensure the user has the required role.
        
        Args:
            payload: Processor method payload
            required_role: Role required for the operation
            
        Raises:
            AuthorizationError: If user doesn't have the required role
        """
        from helpers.common_helper.auth_helper import AuthorizationError
        
        auth_context = AuthContext.from_payload(payload)
        if not auth_context.is_authenticated():
            raise AuthorizationError("This operation requires authentication")
            
        if not auth_context.has_permission(required_role):
            raise AuthorizationError(f"This operation requires {required_role} role")

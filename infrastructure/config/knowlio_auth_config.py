"""Configuration for Knowlio Authentication Stack"""

class AuthConfig:
    """Configuration constants for Cognito authentication"""
    
    # Cognito User Pool Configuration
    USER_POOL = {
        "pool_name": "knowlio-user-pool",
        "self_sign_up_enabled": True,
        "sign_in_aliases": {
            "email": True,
            "username": False,
            "phone": False
        },
        "auto_verify": {
            "email": True
        },
        "standard_attributes": {
            "email": {
                "required": True,
                "mutable": True
            }
        },
        "password_policy": {
            "min_length": 8,
            "require_lowercase": True,
            "require_uppercase": True,
            "require_digits": True,
            "require_symbols": False
        }
    }
    
    # Google Identity Provider Configuration
    GOOGLE_IDP = {
        "provider_name": "Google",
        # These will be populated from environment variables
        "client_id_env_var": "GOOGLE_OAUTH_CLIENT_ID",
        "client_secret_env_var": "GOOGLE_OAUTH_CLIENT_SECRET",
        "scopes": ["openid", "email", "profile"],
        "attribute_mapping": {
            "email": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
            "given_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/givenname",
            "family_name": "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/surname",
            "profile_picture": "picture"
        }
    }
    
    # App Client Configuration
    APP_CLIENT = {
        "client_name": "knowlio-web-app-client",
        "generate_secret": False,  # For frontend usage
        "auth_flows": {
            "user_password": True,
            "user_srp": True
        },
        "oauth": {
            "flows": {
                "authorization_code_grant": True,
                "implicit_code_grant": False
            },
            "scopes": ["openid", "email", "profile"],
            "callback_urls": ["http://localhost:3000/"],
            "logout_urls": ["http://localhost:3000/"]
        }
    }
    
    # Cognito Domain Configuration
    COGNITO_DOMAIN = {
        "domain_prefix": "knowlio-auth"
    }

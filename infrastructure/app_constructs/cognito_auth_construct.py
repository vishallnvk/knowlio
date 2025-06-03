"""Cognito Authentication Construct for Knowlio"""

import os
from constructs import Construct
from aws_cdk import (
    aws_cognito as cognito,
    RemovalPolicy,
    Stack,
    SecretValue
)
from infrastructure.config.knowlio_auth_config import AuthConfig


class CognitoAuthConstruct(Construct):
    """Construct for creating Cognito authentication resources"""
    
    def __init__(self, scope: Construct, id: str, resource_prefix: str = "", 
                 google_client_id: str = None, google_client_secret: str = None):
        super().__init__(scope, id)
        
        self.resource_prefix = resource_prefix
        
        # Create Cognito User Pool
        self.user_pool = cognito.UserPool(
            self, "UserPool",
            user_pool_name=f"{resource_prefix}{AuthConfig.USER_POOL['pool_name']}",
            self_sign_up_enabled=AuthConfig.USER_POOL["self_sign_up_enabled"],
            sign_in_aliases=cognito.SignInAliases(
                email=AuthConfig.USER_POOL["sign_in_aliases"]["email"],
                username=AuthConfig.USER_POOL["sign_in_aliases"]["username"],
                phone=AuthConfig.USER_POOL["sign_in_aliases"]["phone"]
            ),
            auto_verify=cognito.AutoVerifiedAttrs(
                email=AuthConfig.USER_POOL["auto_verify"]["email"]
            ),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=AuthConfig.USER_POOL["standard_attributes"]["email"]["required"],
                    mutable=AuthConfig.USER_POOL["standard_attributes"]["email"]["mutable"]
                )
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=AuthConfig.USER_POOL["password_policy"]["min_length"],
                require_lowercase=AuthConfig.USER_POOL["password_policy"]["require_lowercase"],
                require_uppercase=AuthConfig.USER_POOL["password_policy"]["require_uppercase"],
                require_digits=AuthConfig.USER_POOL["password_policy"]["require_digits"],
                require_symbols=AuthConfig.USER_POOL["password_policy"]["require_symbols"]
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY  # For development - change for production
        )
        
        # Get Google OAuth credentials from environment variables or parameters
        client_id = google_client_id or os.environ.get(AuthConfig.GOOGLE_IDP["client_id_env_var"])
        client_secret = google_client_secret or os.environ.get(AuthConfig.GOOGLE_IDP["client_secret_env_var"])
        
        if not client_id or not client_secret:
            raise ValueError(
                f"Google OAuth credentials not found. Please set {AuthConfig.GOOGLE_IDP['client_id_env_var']} "
                f"and {AuthConfig.GOOGLE_IDP['client_secret_env_var']} environment variables."
            )
        
        # Create Google Identity Provider
        self.google_provider = cognito.UserPoolIdentityProviderGoogle(
            self, "GoogleProvider",
            client_id=client_id,
            client_secret_value=SecretValue.unsafe_plain_text(client_secret),  # Wrap in SecretValue
            user_pool=self.user_pool,
            scopes=AuthConfig.GOOGLE_IDP["scopes"],
            attribute_mapping=cognito.AttributeMapping(
                email=cognito.ProviderAttribute.GOOGLE_EMAIL,
                given_name=cognito.ProviderAttribute.GOOGLE_GIVEN_NAME,
                family_name=cognito.ProviderAttribute.GOOGLE_FAMILY_NAME
                # Removed profile_picture mapping as it's not a standard attribute
            )
        )
        
        # Create Cognito Domain
        # Ensure domain prefix is lowercase and only contains valid characters
        domain_prefix = f"{resource_prefix}{AuthConfig.COGNITO_DOMAIN['domain_prefix']}"
        # Replace underscores with hyphens and convert to lowercase
        domain_prefix = domain_prefix.replace('_', '-').lower()
        
        self.cognito_domain = self.user_pool.add_domain(
            "CognitoDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=domain_prefix
            )
        )
        
        # Create User Pool App Client
        self.user_pool_client = self.user_pool.add_client(
            "UserPoolClient",
            user_pool_client_name=f"{resource_prefix}{AuthConfig.APP_CLIENT['client_name']}",
            generate_secret=AuthConfig.APP_CLIENT["generate_secret"],
            auth_flows=cognito.AuthFlow(
                user_password=AuthConfig.APP_CLIENT["auth_flows"]["user_password"],
                user_srp=AuthConfig.APP_CLIENT["auth_flows"]["user_srp"]
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=AuthConfig.APP_CLIENT["oauth"]["flows"]["authorization_code_grant"],
                    implicit_code_grant=AuthConfig.APP_CLIENT["oauth"]["flows"]["implicit_code_grant"]
                ),
                scopes=[
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.PROFILE
                ],
                callback_urls=AuthConfig.APP_CLIENT["oauth"]["callback_urls"],
                logout_urls=AuthConfig.APP_CLIENT["oauth"]["logout_urls"]
            ),
            supported_identity_providers=[
                cognito.UserPoolClientIdentityProvider.GOOGLE,
                cognito.UserPoolClientIdentityProvider.COGNITO
            ]
        )
        
        # Ensure the Google provider is created before the app client
        self.user_pool_client.node.add_dependency(self.google_provider)
        
    def get_login_url(self) -> str:
        """Get the full OAuth login URL for the Cognito hosted UI"""
        region = Stack.of(self).region
        domain = f"{self.cognito_domain.domain_name}.auth.{region}.amazoncognito.com"
        client_id = self.user_pool_client.user_pool_client_id
        redirect_uri = AuthConfig.APP_CLIENT["oauth"]["callback_urls"][0]
        
        return (f"https://{domain}/oauth2/authorize?"
                f"client_id={client_id}&response_type=code&"
                f"scope=openid+email+profile&redirect_uri={redirect_uri}")
    
    def get_logout_url(self) -> str:
        """Get the logout URL for the Cognito hosted UI"""
        region = Stack.of(self).region
        domain = f"{self.cognito_domain.domain_name}.auth.{region}.amazoncognito.com"
        client_id = self.user_pool_client.user_pool_client_id
        logout_uri = AuthConfig.APP_CLIENT["oauth"]["logout_urls"][0]
        
        return f"https://{domain}/logout?client_id={client_id}&logout_uri={logout_uri}"

"""Authentication Stack for Knowlio using AWS Cognito"""

from aws_cdk import Stack, CfnOutput
from constructs import Construct
from infrastructure.app_constructs.cognito_auth_construct import CognitoAuthConstruct


class AuthStack(Stack):
    """CDK Stack for Cognito authentication resources"""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # Create the Cognito authentication resources
        auth_construct = CognitoAuthConstruct(
            self, "KnowlioAuth",
            resource_prefix=f"{self.stack_name}-"
        )
        
        # Store values for potential cross-stack usage
        self.user_pool = auth_construct.user_pool
        self.user_pool_client = auth_construct.user_pool_client
        self.cognito_domain = auth_construct.cognito_domain
        self.google_provider = auth_construct.google_provider
        
        # Stack outputs
        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="The ID of the Cognito User Pool",
            export_name=f"{self.stack_name}-UserPoolId"
        )
        
        CfnOutput(
            self, "UserPoolClientId",
            value=self.user_pool_client.user_pool_client_id,
            description="The ID of the Cognito User Pool Client",
            export_name=f"{self.stack_name}-UserPoolClientId"
        )
        
        CfnOutput(
            self, "CognitoDomain",
            value=self.cognito_domain.domain_name,
            description="The Cognito domain for the hosted UI",
            export_name=f"{self.stack_name}-CognitoDomain"
        )
        
        # Import the config to access the URLs
        from infrastructure.config.knowlio_auth_config import AuthConfig
        
        CfnOutput(
            self, "CallbackUrls",
            value=",".join(AuthConfig.APP_CLIENT["oauth"]["callback_urls"]),
            description="The callback URLs for OAuth flows",
            export_name=f"{self.stack_name}-CallbackUrls"
        )
        
        CfnOutput(
            self, "LogoutUrls",
            value=",".join(AuthConfig.APP_CLIENT["oauth"]["logout_urls"]),
            description="The logout URLs for OAuth flows",
            export_name=f"{self.stack_name}-LogoutUrls"
        )
        
        CfnOutput(
            self, "AuthDomainUrl",
            value=f"https://{self.cognito_domain.domain_name}.auth.{self.region}.amazoncognito.com",
            description="The full URL for the Cognito hosted UI",
            export_name=f"{self.stack_name}-AuthDomainUrl"
        )
        
        CfnOutput(
            self, "GoogleIdpName",
            value=self.google_provider.provider_name,
            description="The name of the Google identity provider",
            export_name=f"{self.stack_name}-GoogleIdpName"
        )
        
        # Output the login and logout URLs
        CfnOutput(
            self, "LoginUrl",
            value=auth_construct.get_login_url(),
            description="The OAuth login URL for the Cognito hosted UI",
            export_name=f"{self.stack_name}-LoginUrl"
        )
        
        CfnOutput(
            self, "LogoutUrl",
            value=auth_construct.get_logout_url(),
            description="The logout URL for the Cognito hosted UI",
            export_name=f"{self.stack_name}-LogoutUrl"
        )

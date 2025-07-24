"""Authentication Stack for Knowlio using AWS Cognito"""

from aws_cdk import (
    Stack, 
    CfnOutput,
    aws_lambda as lambda_,
    aws_iam as iam,
    Duration
)
from constructs import Construct
from infrastructure.app_constructs.cognito_auth_construct import CognitoAuthConstruct


class AuthStack(Stack):
    """CDK Stack for Cognito authentication resources"""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # Create IAM role for the post-authentication trigger Lambda
        post_auth_trigger_role = iam.Role(
            self, "PostAuthTriggerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "CognitoGroupManagement": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "cognito-idp:AdminListGroupsForUser",
                                "cognito-idp:AdminAddUserToGroup",
                                "cognito-idp:AdminGetUser"
                            ],
                            resources=["*"]  # Will be scoped to user pool after creation
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:UpdateItem"
                            ],
                            resources=["*"]  # Will be scoped to users table after creation
                        )
                    ]
                )
            }
        )
        
        # Create the post-authentication trigger Lambda function
        post_auth_trigger_lambda = lambda_.Function(
            self, "PostAuthTrigger",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="cognito_post_auth_trigger.lambda_handler",
            code=lambda_.Code.from_asset("src/handlers"),
            role=post_auth_trigger_role,
            timeout=Duration.seconds(30),
            environment={
                "COGNITO_REGION": self.region,
                "DEFAULT_USER_GROUP": "Publisher",
                "DEFAULT_USER_ROLE": "PUBLISHER",
                "USERS_TABLE_NAME": "users"  # Will be updated with actual table name
            }
        )
        
        # Create IAM role for the pre-token generation trigger Lambda
        pre_token_generation_trigger_role = iam.Role(
            self, "PreTokenGenerationTriggerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "CognitoGroupManagement": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "cognito-idp:AdminListGroupsForUser",
                                "cognito-idp:AdminAddUserToGroup",
                                "cognito-idp:AdminGetUser"
                            ],
                            resources=["*"]  # Will be scoped to user pool after creation
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:UpdateItem"
                            ],
                            resources=["*"]  # Will be scoped to users table after creation
                        )
                    ]
                )
            }
        )
        
        # Create the pre-token generation trigger Lambda function
        pre_token_generation_trigger_lambda = lambda_.Function(
            self, "PreTokenGenerationTrigger",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="cognito_pre_token_generation_trigger.lambda_handler",
            code=lambda_.Code.from_asset("src/handlers"),
            role=pre_token_generation_trigger_role,
            timeout=Duration.seconds(30),
            environment={
                "COGNITO_REGION": self.region,
                "DEFAULT_USER_GROUP": "Publisher",
                "USERS_TABLE_NAME": "users"  # Will be updated with actual table name
            }
        )
        
        # Create the Cognito authentication resources with the triggers
        auth_construct = CognitoAuthConstruct(
            self, "KnowlioAuth",
            resource_prefix=f"{self.stack_name}-",
            post_auth_trigger_lambda=post_auth_trigger_lambda,
            pre_token_generation_trigger_lambda=pre_token_generation_trigger_lambda
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

#!/usr/bin/env python3

import aws_cdk as cdk

from infrastructure.stacks.knowlio_stack import KnowlioStack
from infrastructure.stacks.knowlio_dynamodb_tables_stack import DynamoDBStack
from infrastructure.stacks.auth_stack import AuthStack
from infrastructure.stacks.opensearch_serverless_stack import OpenSearchServerlessStack

app = cdk.App()

# Common environment for all stacks
env = cdk.Environment(account='916863633553', region='us-west-2')

# Deploy DynamoDBStack
DynamoDBStack(app, "DynamoDBStack", env=env)

# Deploy OpenSearchServerlessStack
opensearch_serverless_stack = OpenSearchServerlessStack(app, "OpenSearchServerlessStack", env=env)

# Deploy AuthStack
# Note: Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET environment variables before deployment
auth_stack = AuthStack(app, "AuthStack", env=env)

# Deploy KnowlioStack with reference to AuthStack for Cognito integration
# and OpenSearchServerlessStack for search capabilities
KnowlioStack(app, "KnowlioStack",
    auth_stack=auth_stack,  # Pass auth_stack for Cognito integration
    opensearch_stack=opensearch_serverless_stack,  # Pass opensearch_stack for search capabilities
    env=env)

app.synth()

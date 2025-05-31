#!/usr/bin/env python3

import aws_cdk as cdk

from infrastructure.stacks.knowlio_stack import KnowlioStack
from infrastructure.stacks.knowlio_dynamodb_tables_stack import DynamoDBStack

app = cdk.App()

# Deploy DynamoDBStack
DynamoDBStack(app, "DynamoDBStack",
    env=cdk.Environment(account='916863633553', region='us-west-2'))

# Deploy KnowlioStack
KnowlioStack(app, "KnowlioStack",
    env=cdk.Environment(account='916863633553', region='us-west-2'))

app.synth()

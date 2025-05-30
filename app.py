#!/usr/bin/env python3

import aws_cdk as cdk

from infrastructure.stacks.knowlio_stack import KnowlioStack

app = cdk.App()
KnowlioStack(app, "KnowlioStack",
    env=cdk.Environment(account='916863633553', region='us-west-2'))

app.synth()

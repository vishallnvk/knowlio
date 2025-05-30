from aws_cdk import Stack, aws_lambda as _lambda
from constructs import Construct

class KnowlioStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        lambda_fn = _lambda.Function(
            self, "SyncHandler",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handlers.synchronous_lambda_handler.lambda_handler",
            code=_lambda.Code.from_asset("src")
        )

from constructs import Construct
from aws_cdk import aws_lambda as _lambda, Duration
from aws_cdk import aws_iam as iam
from typing import Optional, Dict

class LambdaFunctionConstructProps:
    def __init__(
        self,
        id: str,
        handler: str,
        code_path: str,
        function_name: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        timeout_seconds: Optional[int] = 900,  # 15 minutes default
        memory_size_mb: Optional[int] = 128,
        runtime: Optional[_lambda.Runtime] = None,
        lambda_role: Optional[iam.IRole] = None,
    ):
        self.id = id
        self.handler = handler
        self.code_path = code_path
        self.function_name = function_name
        self.environment = environment or {}
        self.timeout_seconds = timeout_seconds
        self.memory_size_mb = memory_size_mb
        self.runtime = runtime or _lambda.Runtime.PYTHON_3_11
        self.lambda_role = lambda_role

class LambdaConstruct(Construct):
    def __init__(self, scope: Construct, id: str, props: LambdaFunctionConstructProps):
        super().__init__(scope, id)

        self.lambda_function = _lambda.Function(
            self, props.id,
            runtime=props.runtime,
            handler=props.handler,
            code=_lambda.Code.from_asset(props.code_path),
            timeout=Duration.seconds(props.timeout_seconds),
            memory_size=props.memory_size_mb,
            environment=props.environment,
            role=props.lambda_role,
            function_name=props.function_name,
        )
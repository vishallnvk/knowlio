from constructs import Construct
from aws_cdk import aws_iam as iam

class IamRole(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        role_name: str = None,
        assumed_by: iam.IPrincipal,
        managed_policies: list[iam.IManagedPolicy] = None,
        inline_policies: dict[str, iam.PolicyDocument] = None,
        description: str = None
    ):
        super().__init__(scope, id)

        self.role = iam.Role(
            self, "IamRole",
            assumed_by=assumed_by,
            role_name=role_name,
            managed_policies=managed_policies or [],
            inline_policies=inline_policies or {},
            description=description,
        )
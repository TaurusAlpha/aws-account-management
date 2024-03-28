from dataclasses import dataclass, field
from typing import Literal


@dataclass
class PSConfigPayload:
    InstanceArn: str
    TargetId: str
    PermissionSetArn: str
    PrincipalId: str
    PrincipalType: Literal["USER", "GROUP"] = field(default="GROUP")
    TargetType: str = field(default="AWS_ACCOUNT", init=False)

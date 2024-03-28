from dataclasses import dataclass
from typing import Callable
from core.commons.enums import OperationType
from core.schemas.ps_requests import PSConfigPayload


@dataclass
class UpdatePSConfig:
    account_id: str
    ps_arns: list[str]
    operation: Callable[[PSConfigPayload], str]
    operation_type: OperationType

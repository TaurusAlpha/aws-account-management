from enum import Enum
from typing import Any, Mapping
from pydantic import BaseModel, Field


class OperationStatus(Enum):
    FAIL = 0
    SUCCESS = 1
    WAITING = 2

    @classmethod
    def from_str(cls, value: str):
        return cls.SUCCESS if value == "SUCCEEDED" else cls.FAIL

class OperationType(Enum):
    CREATE = 0
    TERMINATE = 1
    DELETE = 2
    UPDATE = 3


class ChangedResource(BaseModel):
    resource_type: str
    id_type: str
    id_value: str


class AWSHandlerResponse(BaseModel):
    operation_command: str
    operation_status: OperationStatus
    operation_type: OperationType
    service_name: str
    changed_resources: ChangedResource
    response_payload: Mapping[str, Any]
    stack_summary: Mapping[str, Any]
    stack_trace: list[Mapping[str, Any]]
    message: str
    generated_message: str = Field(init=False)

    def __post_init__(self):
        self.generated_message = f"{self.operation_command} {self.operation_status.name} for {self.service_name}"

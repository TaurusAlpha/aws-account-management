from enum import Enum


class OperationType(Enum):
    CREATE = 0
    TERMINATE = 1
    DELETE = 2
    UPDATE = 3


class OperationStatus(Enum):
    FAILED = 0
    SUCCEEDED = 1
    WAITING = 2
    IN_PROGRESS = 3

    @classmethod
    def from_str(cls, value: str):
        return cls.SUCCEEDED if value == "SUCCES" else cls.FAILED

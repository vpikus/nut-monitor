from enum import Enum

class VarTypeEnum(Enum):
    """NUT (Network UPS Tools) variable types."""
    RW = "RW" # this variable may be set to another value with SET
    ENUM = "ENUM" # an enumerated type, which supports a few specific values
    STRING = "STRING" # this is a string of maximum length n
    NUMBER = "NUMBER" # this is an numeric, either integer or float, comprised in the range
    RANGE = "RANGE" # this is a simple numeric value, either integer or float

class BaseType:
    """NUT (Network UPS Tools) variable base type."""

    def __init__(self, type: VarTypeEnum):
        self.type = type

    def serialize(self):
        return {"type": self.type.value}

class StringType(BaseType):
    """NUT (Network UPS Tools) variable string type."""
    max_length: int
    def __init__(self, max_length: int):
        super().__init__(type=VarTypeEnum.STRING)
        self.max_length = max_length

    def serialize(self):
        return {**super().serialize(), "max_length": self.max_length}


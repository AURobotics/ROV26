from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict

"""
    Supported data types for schema validation
"""
class DataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    CUSTOM = "custom" # field object or a custom class -> must inherit from CustomDataType or its childeren

    def __str__(self):
        return self.value


"""
    Base class for custom data types
"""
@dataclass
class CustomDataType(ABC):
    def __post_init__(self):
        """Validate after all fields are initialized"""
        is_valid, error = self.validate()
        if not is_valid:
            raise ValueError(f"Validation failed for {self.__class__.__name__}: {error}")
    
    @classmethod
    @abstractmethod
    def create_from_config(cls, config: Dict[str, Any]) -> 'CustomDataType':
        """Create an instance of the custom data type from a configuration dictionary instead of init parameters"""
        pass

    @abstractmethod
    def to_config(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def validate(self) -> tuple[bool, str]:
        pass

@dataclass
class ComparableCustomDataType(CustomDataType):
    @abstractmethod
    def __eq__(self, value: object) -> bool: pass

    @abstractmethod
    def __ne__(self, value: object) -> bool: pass

    @abstractmethod
    def __le__(self, value: object) -> bool: pass

    @abstractmethod
    def __lt__(self, value: object) -> bool: pass

    @abstractmethod
    def __ge__(self, value: object) -> bool: pass

    @abstractmethod
    def __gt__(self, value: object) -> bool: pass

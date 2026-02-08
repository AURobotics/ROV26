from abc import ABC, abstractmethod
import re
from threading import Thread
# import yaml
import json
import time
from typing import Any, Dict, List, Optional, Union, Callable, get_type_hints
from dataclasses import dataclass, field, asdict, is_dataclass
from enum import Enum

from paho.mqtt.client import Client as pahoMC
from paho.mqtt.enums import CallbackAPIVersion

"""
    Schema configuration classes:

    MainSchema:
        MainFieldSchema:
            FieldSchema 1 
            FieldSchema 2
            ...
        MainFieldSchema 2:
            FieldSchema 1
            FieldSchema 2
            ...
        ...
"""


"""
    Supported data types for schema validation
"""
class DataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    CUSTOM = "custom"


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
    
    @abstractmethod
    def validate(self) -> tuple[bool, str]:
        pass

"""
    Schema definition for a single field
"""
@dataclass
class FieldSchema(CustomDataType): # it is a dataclass to make nested objects
    name: str
    data_type: DataType
    value: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None  # For regex pattern matching on strings
    allowed_values: Optional[List[Any]] = None
    description: Optional[str] = ""

    def validate(self) -> tuple[bool, str]: # tuple of (is_valid, error_message)
        """Validate a single field value"""
        value = self.value


        # Check if value is there
        if value is None:
            return False, f"Field '{self.name}' is empty and no default value is set"
        
        # Type checking
        try:
            if self.data_type == DataType.STRING:
                if not isinstance(value, str):
                    value = str(value)
            elif self.data_type == DataType.INTEGER:
                if not isinstance(value, int):
                    value = int(float(value))  # Try to convert
            elif self.data_type == DataType.FLOAT:
                if not isinstance(value, (int, float)):
                    value = float(value)
            elif self.data_type == DataType.BOOLEAN:
                if isinstance(value, str):
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif isinstance(value, int):
                    value = bool(value)
                else:
                    value = bool(value)
            elif self.data_type == DataType.CUSTOM:
                if isinstance(value, CustomDataType):
                    is_valid, error_msg = value.validate()
                    if not is_valid:
                        return False, f"Field '{self.name}' custom validation failed: {error_msg}"
                else:
                    return False, f"Field '{self.name}' must be an instance of CustomDataType"
            elif self.data_type == DataType.JSON:
                if isinstance(value, str):
                    try:
                        json.loads(value)
                    except json.JSONDecodeError:
                        return False, f"Field '{self.name}' must be valid JSON"
                # If it's already a dict/list, it's fine
            
        except (ValueError, TypeError) as e:
            return False, f"Field '{self.name}' type error: {str(e)}"
        
        # Value range validation
        if value is not None and isinstance(value, (int, float)):
            if self.min_value is not None and value < self.min_value:
                return False, f"Field '{self.name}' must be >= {self.min_value}"
            if self.max_value is not None and value > self.max_value:
                return False, f"Field '{self.name}' must be <= {self.max_value}"
            
        # Pattern regex validation for strings
        if self.data_type == DataType.STRING and self.pattern:
            if not re.match(self.pattern, str(value)):
                return False, f"Field '{self.name}' doesn't match pattern '{self.pattern}'"
        
        # Allowed values validation
        if self.allowed_values and value not in self.allowed_values:
            return False, f"Field '{self.name}' must be one of {self.allowed_values}"
        
        return True, ""
    
    def set_value(self, value: Any):
        """Set default value if not provided"""
        if value is not None and self.validate():
            self.value = value
        else:
            raise ValueError(f"Default value for field '{self.name}' is invalid: {value}")
    
"""
    Main schema objects (3 main ones: MqttBrker Config, TopicSchema, MessageSchema - datatypes for custom types)
"""
@dataclass
class MainFieldSchema: # not a custom datatype because it shouldn't be nested
    name: str
    value: list[FieldSchema]
    description: Optional[str] = ""

    def __init__(self, name: str, value: list[FieldSchema], description: Optional[str] = ""): 
        """ Validate and add fields to the main schema object """
        if name is None:
            raise ValueError("Field name cannot be None")
        if len(value) == 0:
            raise ValueError(f"Field '{name}' must have a value")
        
        self.name = name
        self.value = value 
        self.description = description

"""
    Complete schema definition
"""
@dataclass
class MainSchema:    
    name: str
    value: list[MainFieldSchema]
    description: Optional[str] = ""

    def __init__(self, name: str, value: list[MainFieldSchema], description: Optional[str] = ""): 
        """ Validate and add fields to the main schema object """
        if name is None:
            raise ValueError("Field name cannot be None")
        if len(value) == 0:
            raise ValueError(f"Field '{name}' must have a value")
        
        self.name = name
        self.value = value 
        self.description = description




if __name__ == "__main__":
    ...
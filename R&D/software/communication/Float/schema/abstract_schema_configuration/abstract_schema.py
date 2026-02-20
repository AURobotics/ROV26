import re
import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from schema.abstract_schema_configuration.abstract_schema_data_types import DataType, CustomDataType

"""
    Schema configuration classes:

    FieldSchemaList:
        FieldSchema 1 
        FieldSchema 2
        ...
    ...

    OR

    FieldSchemaList:
        FieldSchemaList 1:
            FieldSchema 1
            FieldSchema 2
            ...
        FieldSchemaList 2:
            FieldSchema 1
            FieldSchema 2
    ...

    and so on for nested schemas
"""


"""
    Schema definition for a single field (holds data)
"""
@dataclass
class FieldSchema(CustomDataType): # it is a CustomDataType to make nested objects
    name: str
    data_type: DataType
    value: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None  # For regex pattern matching on strings
    allowed_values: Optional[List[Any]] = None
    description: Optional[str] = ""

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> 'FieldSchema':
        res = cls(
            name=config["name"],
            data_type=DataType(config["type"]),
            value=config.get("value"),
            min_value=config.get("min_value"),
            max_value=config.get("max_value"),
            pattern=config.get("pattern"),
            allowed_values=config.get("allowed_values"),
            description=config.get("description", "")
        ) 
        state, error = res.validate()
        if not state:
            raise ValueError(f"Invalid configuration for field '{res.name}': {error}")
        return res
        
         # this method return the FieldSchema object created from the config dictionary -> validation will occur

    def to_config(self):
        config = {
            "name": self.name,
            "type": str(self.data_type),
            "description": self.description,
            "value": self.value.to_config() if isinstance(self.value, CustomDataType) else self.value
        }
        
        # Define optional fields and their keys
        optional_fields = [
            ("min_value", self.min_value),
            ("max_value", self.max_value),
            ("pattern", self.pattern),
            ("allowed_values", [v.to_config() if isinstance(v, CustomDataType) else v for v in self.allowed_values] if isinstance(self.allowed_values, list) else self.allowed_values)
        ]
        
        # Add non-None optional fields
        for key, value in optional_fields:
            if value is not None:
                config[key] = value
                
        return config

    def validate(self) -> tuple[bool, str]: # tuple of (is_valid, error_message)
        """Validate a single field value"""
        # Check if value is there
        if self.value is None:
            return False, f"Field '{self.name}' is empty and no default value is set"
        
        # Type checking
        try:
            if self.data_type == DataType.STRING:
                if not isinstance(self.value, str):
                    self.value = str(self.value)
            elif self.data_type == DataType.INTEGER:
                if not isinstance(self.value, int):
                    self.value = int(float(self.value))  # Try to convert
            elif self.data_type == DataType.FLOAT:
                if not isinstance(self.value, (int, float)):
                    self.value = float(self.value)
            elif self.data_type == DataType.BOOLEAN:
                if isinstance(self.value, str):
                    self.value = self.value.lower() in ('true', '1', 'yes', 'on')
                elif isinstance(self.value, int):
                    self.value = bool(self.value)
                else:
                    self.value = bool(self.value)
            elif self.data_type == DataType.CUSTOM:
                if isinstance(self.value, CustomDataType):
                    is_valid, error_msg = self.value.validate()
                    if not is_valid:
                        return False, f"Field '{self.name}' custom validation failed: {error_msg}"
                else:
                    return False, f"Field '{self.name}' must be an instance of CustomDataType"
            elif self.data_type == DataType.JSON:
                if isinstance(self.value, str):
                    try:
                        json.loads(self.value)
                    except json.JSONDecodeError:
                        return False, f"Field '{self.name}' must be valid JSON"
                # If it's already a dict/list, it's fine
            
        except (ValueError, TypeError) as e:
            return False, f"Field '{self.name}' type error: {str(e)}"
        
        # Value range validation
        if self.value is not None and isinstance(self.value, (int, float)):
            if self.min_value is not None and self.value < self.min_value:
                return False, f"Field '{self.name}' must be >= {self.min_value}"
            if self.max_value is not None and self.value > self.max_value:
                return False, f"Field '{self.name}' must be <= {self.max_value}"
            
        # Pattern regex validation for strings
        if self.data_type == DataType.STRING and self.pattern:
            if not re.match(self.pattern, str(self.value)):
                return False, f"Value '{str(self.value)}' in Field '{self.name}' doesn't match pattern '{self.pattern}'"
        
        # Allowed values validation
        if self.allowed_values and self.value not in self.allowed_values:
            return False, f"Field '{self.name}' must be one of {self.allowed_values}"
        
        return True, ""
    
    def set_value(self, value: Any):
        """Set default value if not provided"""
        if value is not None:
            old_value = self.value
            self.value = value
            state, error= self.validate()
            if not state:
                self.value = old_value # revert to old value if validation fails
                raise ValueError(f"Invalid value for field '{self.name}': {error}")
        else:
            raise ValueError(f"Default value for field '{self.name}' is invalid: {value}")
    
    # Factory methods for easier construction
    @classmethod
    def string(cls, 
               name: str, 
               value: Any = None, 
               pattern: Optional[str] = None,
               allowed_values: Optional[List[str]] = None,
               description: str = "") -> 'FieldSchema':
        """Create a string field"""
        return cls(
            name=name,
            data_type=DataType.STRING,
            value=value,
            pattern=pattern,
            allowed_values=allowed_values,
            description=description
        )
    
    @classmethod
    def integer(cls,
                name: str,
                value: Any = None,
                min_value: Optional[int] = None,
                max_value: Optional[int] = None,
                allowed_values: Optional[List[int]] = None,
                description: str = "") -> 'FieldSchema':
        """Create an integer field"""
        return cls(
            name=name,
            data_type=DataType.INTEGER,
            value=value,
            min_value=min_value,
            max_value=max_value,
            allowed_values=allowed_values,
            description=description
        )
    
    @classmethod
    def float_field(cls,
                    name: str,
                    value: Any = None,
                    min_value: Optional[float] = None,
                    max_value: Optional[float] = None,
                    description: str = "") -> 'FieldSchema':
        """Create a float field"""
        return cls(
            name=name,
            data_type=DataType.FLOAT,
            value=value,
            min_value=min_value,
            max_value=max_value,
            description=description
        )
    
    @classmethod
    def boolean(cls,
                name: str,
                value: Any = None,
                description: str = "") -> 'FieldSchema':
        """Create a boolean field"""
        return cls(
            name=name,
            data_type=DataType.BOOLEAN,
            value=value,
            description=description
        )
    
    @classmethod
    def json_field(cls,
                   name: str,
                   value: Any = None,
                   description: str = "") -> 'FieldSchema':
        """Create a JSON field"""
        return cls(
            name=name,
            data_type=DataType.JSON,
            value=value,
            description=description
        )
    
    @classmethod
    def custom(cls,
               name: str,
               value: Optional[CustomDataType] = None,
               description: str = "") -> 'FieldSchema':
        """Create a custom data type field"""
        return cls(
            name=name,
            data_type=DataType.CUSTOM,
            value=value,
            description=description
        )
    
"""
    FieldSchemaList objects (holds a List of normal Fields)
"""
class FieldSchemaList(CustomDataType): # not a custom datatype because it shouldn't be nested
    name: str
    data_type = DataType.CUSTOM
    description: Optional[str] = ""
    fields: list[Union['FieldSchemaList', FieldSchema]] # list of fields or main field schemas for nesting

    def __init__(self, name: str, fields: list[Union['FieldSchemaList', FieldSchema]], description: Optional[str] = ""): 
        """ Validate and add fields to the main schema object """
        if name is None:
            raise ValueError("Field name cannot be None")
                
        self.name = name
        self.fields = fields 
        self.description = description

        """Validate after all fields are initialized"""
        is_valid, error = self.validate()
        if not is_valid:
            raise ValueError(f"Validation failed for {self.__class__.__name__}: {error}")

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> 'FieldSchemaList':
        fields_list = []

        """
            name: field name
            type: custom
            description: optional description
            fields: 
                - name: field name
                  type: string/integer/float/boolean/json/custom
                  value: default value (optional)
                  min_value: minimum value for number fields (optional)
                  max_value: maximum value for number fields (optional)
                  pattern: regex pattern for string fields (optional)
                  allowed_values: list of allowed values (optional)
                  description: optional description
                - name: field name
                  type: custom
                  value:
                    name: nested field name
                    type: string/integer/float/boolean/json/custom
                    value: default value (optional)
                    min_value: minimum value for number fields (optional)
                    max_value: maximum value for number fields (optional)
                    pattern: regex pattern for string fields (optional)
                    allowed_values: list of allowed values (optional)
                    description: optional description
                ...

        """

        for field_config in config["value"]:
            # Check if it's a nested schema or a simple field
            if "value" in field_config and isinstance(field_config.get("value"), list):
                # It's a FieldSchemaList
                fields_list.append(FieldSchemaList.create_from_config(field_config))
            else:
                # It's a FieldSchema
                fields_list.append(FieldSchema.create_from_config(field_config))
    
        res = cls(
            name=config["name"],
            fields=fields_list,
            description=config.get("description", "")
        )
        
        state, error = res.validate()
        if not state:
            raise ValueError(f"Invalid configuration for field '{res.name}': {error}")
        return res
    
    def to_config(self) -> Dict[str, Any]:
        config = {
            "name": self.name,
            "type": str(self.data_type),
            "description": self.description,
            "value": [field.to_config() for field in self.fields]
        }
        
        return config
        
    def validate(self) -> tuple[bool, str]:
        for field in self.fields:
            is_valid, error = field.validate()
            if not is_valid:
                return False, f"Validation failed for field '{field.name}': {error}"
        return True, ""
    
    @classmethod
    def group(cls,
              name: str,
              fields: list[Union['FieldSchemaList', FieldSchema]],
              description: str = "") -> 'FieldSchemaList':
        """Factory method to create a FieldSchemaList group"""
        return cls(name=name, fields=fields, description=description)


if __name__ == "__main__":
    ...
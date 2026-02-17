from .abstract_schema_configuration.abstract_schema import DataType, FieldSchemaList, FieldSchema

from typing import Any, Dict, Optional, Union, cast
from dataclasses import dataclass, field, asdict, is_dataclass

"""
    mqtt broker:
        address: localhost
        port: 1883
    topics:
        - name: topic1                                                      # FieldSchema
          type: custom
          description: Schema for topic1
          value:
            - name: message1                                                # FieldSchemaList
              type: custom
              description: Schema for message1
              fields:
                    - name: field1
                      type: string
                      description: Field1 in message1
                      value: "example string"
                    - name: field2
                      type: integer
                      description: Field2 in message1
                      value: 42
                    ...
            - name: meessage2
              type: custom
              description: Schema for message2
              fields:
                - name: field1
                  type: float
                  description: Field1 in message2
                  value: 3.14
                ...
        - name: topic2
          type: custom
          description: Schema for topic2
          value:
                - name: message1
                  type: custom
                  description: Schema for message1
                  fields:
                        - name: field1
                          type: boolean
                          description: Field1 in message1
                          value: true
                        - name: field2
                          type: json
                          description: Field2 in message1
                          value: {"key": "value"}
                        ...
                ...
        ...
                    
        ...
"""



"""=============================================(3) Field Schemas==============================================="""

class MessageSchema(FieldSchemaList): # FieldSchemaList since it can hold multiple fields representing the message structure
    """Schema for an MQTT message payload"""
    def __init__(self, name: str, fields: Optional[list[FieldSchema]] = None, description: Optional[str] = None):
        # NOTE: yoy can't set default value for fields as [] in the function signature because it will be shared across all instances of MessageSchema, which can lead to unexpected behavior. Hence, we set it to None and then initialize it to an empty list inside the function.
        if fields is None:
            fields = []

        if description is None:
            description = f"Schema for MQTT message '{name}'"
            
        super().__init__(name=name, fields=cast(list[Union[FieldSchema, FieldSchemaList]], fields), description=description)

    @classmethod
    def create_from_config(cls, config: Any) -> 'MessageSchema':
        return cast(MessageSchema, super().create_from_config(config))

    def add_field(self, field_schema: FieldSchema):
        self.fields.append(field_schema)

    def remove_field(self, field_name: str):
        self.fields = [field for field in self.fields if field.name != field_name]

    def update_field(self, field_schema: FieldSchema):
        existing = next((field for field in self.fields if field.name == field_schema.name), None)
        if existing is None:
            raise KeyError(f"Field '{field_schema.name}' not found in message schema.")
        
        self.fields.remove(existing)
        self.fields.append(field_schema)
        
        # Re-validate after mutation
        is_valid, error = self.validate()
        if not is_valid:
            # Rollback
            self.fields.remove(field_schema)
            self.fields.append(existing)
            raise ValueError(f"Update failed: {error}")

    def to_config(self) -> Dict[str, Any]:
        return super().to_config()


class TopicSchema(FieldSchema):
    """Schema definition for a topic field"""

    def __init__(self, name: str, message_schema: MessageSchema):
        super().__init__(name=name, data_type=DataType.CUSTOM, value=message_schema, description=f"Schema for topic '{name}'")

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> 'TopicSchema':
        message_schema = MessageSchema.create_from_config(config["value"])
        return cls(name=config["name"], message_schema=message_schema)
    
    def to_config(self) -> Dict[str, Any]:
        return super().to_config()


"""=============================================(2) Main Field Schemas==============================================="""

class MQTTBrokerConfig(FieldSchemaList):
    """MQTT broker connection configuration"""
    
    def __init__(self, address: str = "localhost", port: int = 1883):
        addressField: FieldSchema = FieldSchema.string(name="address", value="localhost", description="MQTT broker address")
        portField: FieldSchema = FieldSchema.integer(name="port", value=1883, description="MQTT broker port")

        addressField.set_value(address)
        portField.set_value(port)

        super().__init__(name="mqtt_broker_config", fields=[addressField, portField], description="MQTT broker connection configuration")

    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> 'MQTTBrokerConfig':
        address = config.get("address", "localhost")
        port = config.get("port", 1883)
        return cls(address=address, port=port)
    
    def to_config(self) -> Dict[str, Any]:
        addressField: FieldSchema = cast(FieldSchema, self.fields[0]) # address field is always the first field in the list
        portField: FieldSchema = cast(FieldSchema, self.fields[1]) # port field
        return {
            "address": addressField.value,
            "port": portField.value
        }


    def set_address(self, address: str):
        """Set MQTT broker address"""
        addressField: FieldSchema = cast(FieldSchema, self.fields[0]) # address field is always the first field in the list
        addressField.set_value(address) # address field is always the first field in the list

    def set_port(self, port: int):
        """Set MQTT broker port"""
        portField: FieldSchema = cast(FieldSchema, self.fields[1]) # port field is always the second field in the list
        portField.set_value(port) # port field is always the second field in the list

class AllTopicsSchema(FieldSchemaList):
    """Topic configuration schema"""
    def __init__(self):
        temp = []
        super().__init__(name="all_topics_schema", fields=temp, description="Schema for all MQTT topics")

    def add_topic(self, topic: TopicSchema, description: str = "") -> AllTopicsSchema:
        self.fields.append(topic) # TopicSchema is a FieldSchema; hence, already validated 
        return self
    
    def get_topic(self, name: str) -> Optional[TopicSchema]:
        """Get a topic schema by name"""
        for topic in self.fields:
            if topic.name == name:
                return cast(TopicSchema, topic)
        return None
    
    def remove_topic(self, name: str) -> AllTopicsSchema:
        """Remove a topic schema by name"""
        if self.get_topic(name) is None:
            raise KeyError(f"Topic '{name}' not found in configuration.")
        self.fields = [topic for topic in self.fields if topic.name != name]
        return self
    
    def update_topic(self, topic_schema: TopicSchema) -> 'AllTopicsSchema':
        existing = self.get_topic(topic_schema.name)
        if existing is None:
            raise KeyError(f"Topic '{topic_schema.name}' not found")
        
        self.fields.remove(existing)
        self.fields.append(topic_schema)
        
        # Re-validate after mutation
        is_valid, error = self.validate()
        if not is_valid:
            # Rollback
            self.fields.remove(topic_schema)
            self.fields.append(existing)
            raise ValueError(f"Update failed: {error}")
        
        return self
    @classmethod
    def create_from_config(cls, config: Dict[str, Any]) -> 'AllTopicsSchema':
        """Create an AllTopicsSchema instance from a configuration dictionary"""
        instance = cls()
        for topic_config in config.get("topics", []):
            topic_schema = TopicSchema.create_from_config(topic_config)
            instance.add_topic(topic_schema)
        return instance

    def to_config(self) -> Dict[str, Any]:
        """Convert AllTopicsSchema to a dictionary for YAML serialization"""
        return {"topics": [cast(TopicSchema, topic).to_config() for topic in self.fields]} # cast is needed to access the to_config method of TopicSchema

"""=============================================(1) Main Schema==============================================="""
#class ConfigManager:
"""
    Main configuration manager schema for MQTT communication
    Holds 2 main fields:
        - mqtt_broker_config: MqttBrokerConfig 
        - all_topics_schema: AllTopicsSchema 
"""

"""=============================================TopicSchema to ==============================================="""


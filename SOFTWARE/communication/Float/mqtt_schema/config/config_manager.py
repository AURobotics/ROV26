from schema_classes import CustomDataType, DataType, MainSchema, MainFieldSchema, FieldSchema

from typing import Any, Dict, List, Optional, Union, Callable, get_type_hints
from dataclasses import dataclass, field, asdict, is_dataclass

"""
    Configuration manager for MQTT schema:
        MqttBrokerConfig:
            FieldSchemas: address, port
        AllTopicsSchema:
            TopicSchemas: 
                topic1
                    name = topic1
                    value = a message
                topic2 
                    name = topic2
                    value = a message
                ...
        MessagesTypesSchema:
            MessageSchemas: 
                message1:
                    DatatTypes: field1, field2, ...
                message2:
                    DataTypes: field1, field2, ...
                ...

"""


"""=============================================Main Schema==============================================="""
class ConfigManager(MainSchema):
    ...

"""=============================================Main Field Schemas==============================================="""

class MQTTBrokerConfig(MainFieldSchema):
    """MQTT broker connection configuration"""
    
    def __init__(self, address: str = "localhost", port: int = 1883):
        addressField: FieldSchema = FieldSchema(name="address", data_type=DataType.STRING, value="localhost", description="MQTT broker address")
        portField: FieldSchema = FieldSchema(name="port", data_type=DataType.INTEGER, value=1883, description="MQTT broker port")

        addressField.set_value(address)
        portField.set_value(port)

        super().__init__(name="mqtt_broker_config", value=[addressField, portField], description="MQTT broker connection configuration")


class AllTopicsSchema(MainFieldSchema):
    """Topic configuration schema"""
    def add_topic(self, name: str, topic: TopicSchema, description: str = "") -> AllTopicsSchema:
        self.value.append(topic) # TopicSchema is a FieldSchema; hence, already validated 
        return self

class MessagesTypesSchema(MainFieldSchema):
    """Message types schema for defining custom message payloads"""
    def add_message_type(self, name: str, field: MessageSchema, description: str = "") -> MessagesTypesSchema:
        self.value.append(field) # MessageSchema is a FieldSchema; hence, already validated
        return self

"""=============================================Field Schemas==============================================="""

class TopicSchema(FieldSchema):
    """Schema definition for a topic field"""

    def __init__(self, name: str, message_schema: MessageSchema):
        if(name == None):
            raise ValueError("Topic name cannot be None")
        if(len(message_schema.fields) == 0):
            raise ValueError("Message schema must have at least one field")
        
        self.name = name
        self.data_type = DataType.CUSTOM
        self.value: MessageSchema = message_schema
        self.description = f"Topic '{name}' schema"


class MessageSchema(FieldSchema):
    """Schema for an MQTT message payload"""
    fields: list[CustomDataType] = []

    def add_field(self, field_schema: FieldSchema):
        self.fields.append(field_schema)

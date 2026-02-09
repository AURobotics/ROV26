from SOFTWARE.communication.Float.mqtt_schema.config.abstract_schema import CustomDataType, DataType, MainSchema, MainFieldSchema, FieldSchema

from typing import Any, Dict, Sequence, Optional, Union, Callable, get_type_hints
from dataclasses import dataclass, field, asdict, is_dataclass

"""
    Configuration manager for MQTT schema:
        MqttBrokerConfig:
            FieldSchemas: address, port
        AllTopicsSchema:
            TopicSchemas: 
                topic1
                    name = topic1
                    value = message1
                topic2 
                    name = topic2
                    value = message2
                ...
        # MessagesTypesSchema:
        #     MessageSchemas: 
        #         message1:
        #             DatatTypes: field1, field2, ...
        #         message2:
        #             DataTypes: field1, field2, ...
        #         ...
"""


"""=============================================Main Schema==============================================="""
class ConfigManager(MainSchema):
    """Main configuration manager schema for MQTT communication"""

    def __init__(self, mqtt_broker_config: MQTTBrokerConfig, all_topics_schema: AllTopicsSchema):
        super().__init__(name="mqtt_broker_config", value=[mqtt_broker_config, all_topics_schema], description="Configuration manager for MQTT communication")
        
        # taking refrences to named variables for easiness
        self.mqtt_broker_config = self.value[0] 
        self.all_topics_schema = self.value[1]
        # self.messages_types_schema = self.value[2]

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
    def __init__(self):
        self.name = "all_topics_schema"
        self.value = [] # list of TopicSchemas
        self.description = "Schema for all MQTT topics"

    def add_topic(self, name: str, topic: TopicSchema, description: str = "") -> AllTopicsSchema:
        self.value.append(topic) # TopicSchema is a FieldSchema; hence, already validated 
        return self

# class MessagesTypesSchema(MainFieldSchema):
#     """Message types schema for defining custom message payloads"""
#     def add_message_type(self, name: str, field: MessageSchema, description: str = "") -> MessagesTypesSchema:
#         self.value.append(field) # MessageSchema is a FieldSchema; hence, already validated
#         return self

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

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'TopicSchema':
        return cls(name=config["name"], message_schema=MessageSchema.from_config(config["value"]))


class MessageSchema(FieldSchema):
    """Schema for an MQTT message payload"""
    fields: list[FieldSchema] = []

    def __init__(self, name: str, fields: list[FieldSchema]):
        if(name == None):
            raise ValueError("Message name cannot be None")
        if(len(fields) == 0):
            raise ValueError("Message schema must have at least one field")
        
        self.name = name
        self.data_type = DataType.CUSTOM
        self.value = fields
        self.description = f"Message '{name}' schema"

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'MessageSchema':
        fields = [FieldSchema.from_config(field) for field in config["value"]]
        return cls(name=config["name"], fields=fields)

    def add_field(self, field_schema: FieldSchema):
        self.value.append(field_schema)

import json
from SOFTWARE.communication.Float.base_types import MqttMessage

from typing import Any, Dict, cast
from SOFTWARE.communication.Float.schema.abstract_schema_configuration.abstract_schema import FieldSchema
from SOFTWARE.communication.Float.schema.mqtt_schema_types import MQTTBrokerConfig, AllTopicsSchema, MessageSchema


class MessageSchema_to_MqttMessage_Adapter(MqttMessage):
    """Adapter to convert MessageSchema to MqttMessage"""

    def __init__(self, message_schema: MessageSchema):
        super().__init__()
        self.message_schema = message_schema
        # Initialize args with default values from the message schema
        for field in message_schema.fields:
            castedField = cast(FieldSchema, field)
            self.args[field.name] = castedField.value

    def add_variable(self, name: str, value: Any):
        return super().add_variable(name, value)
    
    def set_variable(self, name: str, value: Any):
        return super().set_variable(name, value)

    def encode(self):
        """Encode topic data to a dictionary for MQTT payload"""
        return json.dumps(self.args)
    
    def decode(self, payload: str):
        """Decode MQTT payload to topic data"""
        # we assume the payload is a string representation of a dictionary because that's how we encode it
        try:
            self.args = json.loads(payload)       
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {e}")
        
    
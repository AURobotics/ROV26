import json
from SOFTWARE.communication.Float.base_types import MqttMessage

from typing import Any, Dict
from SOFTWARE.communication.Float.schema.mqtt_schema_types import MQTTBrokerConfig, AllTopicsSchema, MessageSchema


class MessageSchema_to_MqttMessage_Adapter(MqttMessage):
    """Adapter to convert MessageSchema to MqttMessage"""

    args: Dict[str, Any] = {}
    def __init__(self, topic: str):
        self.topic = topic

    def add_variable(self, name: str, value: Any):
        self.args[name] = value

    def set_variable(self, name: str, value: Any):
        if name in self.args:
            self.args[name] = value
        else:
            raise KeyError(f"Variable '{name}' not found in message arguments.")


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
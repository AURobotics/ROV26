from abc import ABC, abstractmethod
import json
from typing import Any, Dict, List, Optional, Union, Callable, get_type_hints

class MqttMessage(ABC):
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
        return json.dumps(self.args)  # SAFE - only encodes JSON serializable data
    
    def decode(self, payload: str):
        """Decode MQTT payload to topic data"""
        # we assume the payload is a string representation of a dictionary because that's how we encode it
        try:
            self.args = json.loads(payload)  # SAFE - only parses JSON
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {e}")


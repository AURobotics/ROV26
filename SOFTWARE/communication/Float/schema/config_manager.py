from dataclasses import asdict
import json
from SOFTWARE.communication.Float.base_types import MqttMessage
from SOFTWARE.communication.Float.schema.config_schema.abstract_schema import DataType, FieldSchema
from SOFTWARE.communication.Float.schema.config_schema.mqtt_schema import AllTopicsSchema, MessageSchema, TopicSchema

from typing import Any, Dict, List, Optional, Union, Callable, cast, get_type_hints
import yaml
from pathlib import Path

from paho.mqtt.client import Client as pahoMC
from paho.mqtt.enums import CallbackAPIVersion
from threading import Thread
import time

class MQTTConfigManager:
    """Manages MQTT configuration from YAML file"""
    
    def __init__(self, config_path: str):
        self.config_data = self._load_config(Path(config_path))
        self._mqtt_settings: Dict[str, Any] = {} # dictionary holding MQTT broker settings
        self._topics: AllTopicsSchema = AllTopicsSchema() # dictionary holding topics
        # self._data_formats: Dict[str, MessageSchema] = {} # dictionary holding data formats
        self._load_all()
        # print(f"MQTTConfigManager initialized with config: {self.config_data}")

    @classmethod
    def manual_init(cls, mqtt_settings: Dict[str, Any], topics: AllTopicsSchema) -> 'MQTTConfigManager':
        """Manual initialization of MQTTConfigManager"""
        instance = cls.__new__(cls)  # Create an uninitialized instance
        instance._mqtt_settings = mqtt_settings
        instance._topics = topics
        # instance._data_formats = data_formats
        return instance

    # def _topic_to_config(self, topic: AllTopicsSchema) -> Dict:
    #     """Convert TopicSchema to dictionary with serializable values"""
    #     result = asdict(topic)
        
    #     # Convert any DataType objects to strings/dicts
    #     def convert_value(obj):
    #         if isinstance(obj, DataType):
    #             # Return a string representation or a dict
    #             return str(obj)  # or obj.value if DataType has a value attribute
    #         return obj
        
    #     # Recursively convert all values
    #     def recursive_convert(d):
    #         if isinstance(d, dict):
    #             return {k: recursive_convert(v) for k, v in d.items()}
    #         # elif isinstance(d, list):
    #         #     return [recursive_convert(v) for v in d]
    #         else:
    #             return convert_value(d)
        
    #     return recursive_convert(result) # no worries, last return will be a dict

    def update_config(self, config_path: str):
        """Write updated configuration to YAML file"""
        with open(config_path, 'w') as f:
            # Create a dictionary where keys are topic names
            topics_dict = {}
            for topic in self._topics.value:
                topics_dict[topic.name] = {
                    "name": topic.name,
                    "type": "custom",
                    "value": topic.value.to_config() if hasattr(topic.value, 'to_config') else topic.value,
                    "description": topic.description
                }
            
            config_data = {
                "mqtt_broker_config": self._mqtt_settings,
                "all_topics_schema": topics_dict,
            }
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

    def _load_all(self):
        """Load all configurations"""
        # Load MQTT broker settings
        self._mqtt_settings = self.config_data.get("mqtt_broker_config", {})
        
        # Load topics - topics_config should be a dict where keys are topic names
        topics_config = self.config_data.get("all_topics_schema", {})
        
        # Clear existing topics
        self._topics.value = []
        
        for name, config in topics_config.items():
            try:
                # The config should already have "name" key matching the topic name
                if "name" not in config:
                    config["name"] = name
                
                # Create TopicSchema from config
                topic_schema = TopicSchema.from_config(config)
                self._topics.add_topic(name, topic_schema)
                # print(f"Loaded topic '{name}': {self._topics.get_topic(name)}")
            except Exception as e:
                print(f"Error loading topic '{name}': {e}")
    
    def _load_config(self, config_path) -> Dict[str, Any]:
        """Load YAML configuration file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    # def _load_all(self):
    #     """Load all configurations"""
    #     # Load MQTT broker settings
    #     self._mqtt_settings = self.config_data.get("mqtt_broker_config", {})
    #     # Load topics
    #     topics_config = self.config_data.get("all_topics_schema", {})
    #     for name, config in topics_config.items():
    #         # print(f"Loading topic '{name}' from config: {config}")
    #         self._topics.add_topic(name, TopicSchema.from_config({'name': name, 'value': config}))
    #         print(f"Loaded topic '{name}': {self._topics.get_topic(name)}")
        
    #     # Load data formats
    #     # self._data_formats = self.config_data.get("data_formats", {})
    
    def add_topic(self, name: str, topic_schema: TopicSchema):
        """Add a new topic configuration"""
        self._topics.add_topic(name, topic_schema)

    def create_topic(self, name: str, message_schema: MessageSchema) -> TopicSchema:
        """Create a new TopicSchema and add it to the configuration"""
        new_topic = TopicSchema(name=name, message_schema=message_schema)
        self.add_topic(name, new_topic)
        return new_topic

    def remove_topic(self, name: str):
        """Remove a topic configuration"""
        self._topics.remove_topic(name)
        
    def update_topic(self, name: str, topic_schema: TopicSchema):
        """Update an existing topic configuration"""
        self._topics.update_topic(name, topic_schema)
        
    def change_topic_message(self, topic_name: str, new_message_schema: MessageSchema):
        """Change the message schema of an existing topic"""
        topic = self._topics.get_topic(topic_name)
        if topic is not None:
            topic.value = new_message_schema
        else:
            raise KeyError(f"Topic '{topic_name}' not found in configuration.")
        
    def change_topic_name(self, old_name: str, new_name: str):
        """Change the name of an existing topic"""
        topic = self._topics.get_topic(old_name)
        if topic is not None:
            topic.name = new_name
            self._topics.update_topic(old_name, topic)
        else:
            raise KeyError(f"Topic '{old_name}' not found in configuration.")
        
    def create_message_schema(self, fields: list[FieldSchema]) -> MessageSchema:
        """Create a new MessageSchema from a list of FieldSchema objects"""
        return MessageSchema(name="NewMessage", fields=fields)
    
    def create_message_variable(self, name: str, data_type: DataType) -> FieldSchema:
        """Create a new FieldSchema for a message field"""
        return FieldSchema(name=name, data_type=data_type, value=None)
    
    def change_mqtt_address(self, new_address: str):
        """Change MQTT broker address"""
        self._mqtt_settings["address"] = new_address
    def change_mqtt_port(self, new_port: int):
        """Change MQTT broker port"""
        self._mqtt_settings["port"] = new_port

    @property
    def mqtt_settings(self) -> Dict[str, Any]:
        """Get MQTT broker settings"""
        return self.config_data.get("mqtt_broker_config", {})
    
    @property
    def topics(self) -> Dict[str, TopicSchema]:
        """Get all topic configurations"""
        return {topic.name: cast(TopicSchema, topic) for topic in self._topics.value}
    
    def get_topic(self, name: str) -> Optional[TopicSchema]:
        """Get specific topic configuration"""
        return self._topics.get_topic(name)
    
    # def get_data_format(self, name: str) -> Optional[Dict[str, Any]]:
    #     """Get data format definition"""
    #     return self._data_formats.get(name)

class TopicDataType(MqttMessage):
    """Defines the data type of a topic field"""
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



if __name__ == "__main__":
    ...
from dataclasses import asdict
import json
from ..base_types import MqttMessage
from .abstract_schema_configuration.abstract_schema import FieldSchema
from .abstract_schema_configuration.abstract_schema_data_types import DataType
from .mqtt_schema_adapter import MessageSchema_to_MqttMessage_Adapter
from .mqtt_schema_types import MQTTBrokerConfig, AllTopicsSchema, MessageSchema, TopicSchema
from ..mqtt import Mqtt, Topic

from typing import Any, Dict, List, Optional, Union, Callable, cast, get_type_hints
import yaml
from pathlib import Path

from paho.mqtt.client import Client as pahoMC
from paho.mqtt.enums import CallbackAPIVersion
from threading import Thread
import time

class MQTTConfigManager:
    """Manages MQTT configuration from YAML file"""

    def __init__(self, 
                 config_path: str|None = None,
                 mqtt_settings: MQTTBrokerConfig | None = None,
                 topics: AllTopicsSchema | None = None):
        
        if mqtt_settings is not None:
            self._mqtt_settings = mqtt_settings
        else:
            self._mqtt_settings: MQTTBrokerConfig = MQTTBrokerConfig() 

        if topics is not None:
            self._topics = topics
        else:
            self._topics: AllTopicsSchema = AllTopicsSchema()
        
        self.mqtt = Mqtt(address=self._mqtt_settings.to_config()["address"], port=self._mqtt_settings.to_config()["port"])
        
        if config_path is not None:
            self.config_data = self._load_config(Path(config_path))
            self._load_all()


    def save_config(self, config_path: str):
        """Write updated configuration to YAML file"""
        with open(config_path, 'w') as f:
            config_data = {
                "mqtt_broker": self._mqtt_settings.to_config(),
                "topics": [field.to_config() for field in self._topics.fields]
            }
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

    def _load_all(self):
        """Load all configurations"""
        
        self._mqtt_settings = MQTTBrokerConfig.create_from_config(
            self.config_data["mqtt_broker"]
        ) if "mqtt_broker" in self.config_data else MQTTBrokerConfig()
        
        # Wrap topics list in expected format
        self._topics = AllTopicsSchema.create_from_config(
            {"topics": self.config_data["topics"]}  # Wrap in dict with "topics" key
        ) if "topics" in self.config_data else AllTopicsSchema()

    def _load_config(self, config_path) -> Dict[str, Any]:
        """Load YAML configuration file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
        
    def add_topic(self, topic_schema: TopicSchema):
        """Add a new topic configuration"""
        self._topics.add_topic(topic_schema)

    def remove_topic(self, name: str):
        """Remove a topic configuration"""
        self._topics.remove_topic(name)

    def update_topic(self, topic_schema: TopicSchema):
        """Update an existing topic configuration"""
        self._topics.update_topic(topic_schema)
        
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
            self._topics.remove_topic(old_name)
            self._topics.add_topic(topic)
        else:
            raise KeyError(f"Topic '{old_name}' not found in configuration.")
        
    def create_message_schema(self, fields: list[FieldSchema]) -> MessageSchema:
        """Create a new MessageSchema from a list of FieldSchema objects"""
        return MessageSchema(name="NewMessage", fields=fields)
    
    def update_message_schema(self, topic_name: str, message_schema: MessageSchema):
        """Update the message schema of an existing topic with new fields"""
        topic = self._topics.get_topic(topic_name)
        if topic is not None:
            topic.value.fields = message_schema.fields
        else:
            raise KeyError(f"Topic '{topic_name}' not found in configuration.")
    
    def create_field(self, name: str, data_type: DataType, value: Any) -> FieldSchema:
        """Create a validated field"""
        factory_map = {
            DataType.STRING: FieldSchema.string,
            DataType.INTEGER: FieldSchema.integer,
            DataType.FLOAT: FieldSchema.float_field,
            DataType.BOOLEAN: FieldSchema.boolean,
            DataType.JSON: FieldSchema.json_field,
        }
        factory = factory_map.get(data_type)
        if factory:
            return factory(name, value=value)
        raise ValueError(f"Unsupported data type: {data_type}")
    
    def change_mqtt_address(self, new_address: str):
        """Change MQTT broker address"""
        self._mqtt_settings.set_address(new_address)

    def change_mqtt_port(self, new_port: int):
        """Change MQTT broker port"""
        self._mqtt_settings.set_port(new_port)

    @property
    def mqtt_settings(self) -> Dict[str, Any]:
        """Get MQTT broker settings"""
        return self._mqtt_settings.to_config()
    
    @property
    def topic_names(self) -> list[str]:
        """Get all topic configurations"""
        return [field.name for field in self._topics.fields]
    
    def get_topic_schema(self, name: str) -> Optional[TopicSchema]:
        """Get specific topic configuration"""
        return self._topics.get_topic(name)
    
    def get_message_schema(self, topic_name: str) -> Optional[MessageSchema]:
        """Get message schema for a specific topic"""
        topic = self._topics.get_topic(topic_name)
        return topic.value if topic else None
    
    # return topics and their message schemas if schema is used for reading only
    def get_all_topics_messages(self) -> Dict[Topic, MqttMessage]:
        res = {}
        for topic_schema in self._topics.fields:
            casted_topic_schema = cast(TopicSchema, topic_schema)
            topic = Topic(casted_topic_schema.name, self.mqtt)
            message = MessageSchema_to_MqttMessage_Adapter(casted_topic_schema.value)
            res[topic] = message

        return res

if __name__ == "__main__":
    # Example usage
    config_manager = MQTTConfigManager()
    
    # Add a new topic
    new_message_schema = MessageSchema(name="NewMessage", fields=[
        FieldSchema.string(name="field1", value="example", description="A string field"),
        FieldSchema.integer(name="field2", value=42, description="An integer field")
    ])
    new_topic = TopicSchema(name="new/topic", message_schema=new_message_schema)
    config_manager.add_topic(new_topic)
    
    # Save updated configuration
    config_manager.save_config("./SOFTWARE/communication/Float/schema/testing/mqtt_config1.yaml")
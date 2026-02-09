from dataclasses import asdict
from mqtt_schema import TopicSchema

from typing import Any, Dict, List, Optional, Union, Callable, get_type_hints
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
        self._topics: Dict[str, TopicSchema] = {} # dictionary holding topics
        # self._data_formats: Dict[str, MessageSchema] = {} # dictionary holding data formats
        self._load_all()

    @classmethod
    def manual_init(cls, mqtt_settings: Dict[str, Any], topics: Dict[str, TopicSchema]) -> 'MQTTConfigManager':
        """Manual initialization of MQTTConfigManager"""
        instance = cls.__new__(cls)  # Create an uninitialized instance
        instance._mqtt_settings = mqtt_settings
        instance._topics = topics
        # instance._data_formats = data_formats
        return instance

    def update_config(self, config_path: str):
        """Write updated configuration to YAML file"""
        with open(config_path, 'w') as f:
            config_data = {
                "mqtt_broker_config": self._mqtt_settings,
                "all_topics_schema": {name: asdict(topic) for name, topic in self._topics.items()},
                # "data_formats": {name: asdict(format) for name, format in self._data_formats.items()
            }
            yaml.dump(config_data, f)
    
    def _load_config(self, config_path) -> Dict[str, Any]:
        """Load YAML configuration file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _load_all(self):
        """Load all configurations"""
        # Load MQTT broker settings
        self._mqtt_settings = self.config_data.get("mqtt_broker_config", {})
        # Load topics
        topics_config = self.config_data.get("all_topics_schema", {})
        for name, config in topics_config.items():
            self._topics[name] = TopicSchema.from_config(config)
        
        # Load data formats
        # self._data_formats = self.config_data.get("data_formats", {})
    
    @property
    def mqtt_settings(self) -> Dict[str, Any]:
        """Get MQTT broker settings"""
        return self.config_data.get("mqtt_broker_config", {})
    
    @property
    def topics(self) -> Dict[str, TopicSchema]:
        """Get all topic configurations"""
        return self._topics
    
    def get_topic(self, name: str) -> Optional[TopicSchema]:
        """Get specific topic configuration"""
        return self._topics.get(name)
    
    # def get_data_format(self, name: str) -> Optional[Dict[str, Any]]:
    #     """Get data format definition"""
    #     return self._data_formats.get(name)
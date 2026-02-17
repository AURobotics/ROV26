# test schema initialization -> No File
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from SOFTWARE.communication.Float.schema.config_schema.abstract_schema import (
    DataType, FieldSchema, MainFieldSchema, MainSchema
)
from SOFTWARE.communication.Float.schema.config_schema.mqtt_schema import (
    MQTTBrokerConfig, AllTopicsSchema, TopicSchema, MessageSchema, ConfigManager
)
from config_manager import (
    MQTTConfigManager, TopicDataType
)

import json
from dataclasses import asdict

def test_field_schema_creation():
    """Test basic FieldSchema creation and validation"""
    print("=== Testing FieldSchema Creation ===")
    
    # Test string field
    string_field = FieldSchema(
        name="username",
        data_type=DataType.STRING,
        value="john_doe",
        pattern=r"^[a-zA-Z0-9_]+$",
        description="User name field"
    )
    print(f"String Field: {string_field.name} = {string_field.value}")
    print(f"Validation: {string_field.validate()}")
    
    # Test integer field with range
    int_field = FieldSchema(
        name="age",
        data_type=DataType.INTEGER,
        value=25,
        min_value=0,
        max_value=150,
        description="Age field"
    )
    print(f"Integer Field: {int_field.name} = {int_field.value}")
    print(f"Validation: {int_field.validate()}")
    
    # Test float field
    float_field = FieldSchema(
        name="temperature",
        data_type=DataType.FLOAT,
        value=36.6,
        min_value=-50.0,
        max_value=100.0,
        description="Temperature in Celsius"
    )
    print(f"Float Field: {float_field.name} = {float_field.value}")
    print(f"Validation: {float_field.validate()}")
    
    # Test boolean field
    bool_field = FieldSchema(
        name="is_active",
        data_type=DataType.BOOLEAN,
        value=True,
        description="Active status"
    )
    print(f"Boolean Field: {bool_field.name} = {bool_field.value}")
    print(f"Validation: {bool_field.validate()}")
    
    # Test JSON field
    json_data = {"key": "value", "nested": {"array": [1, 2, 3]}}
    json_field = FieldSchema(
        name="config",
        data_type=DataType.JSON,
        value=json.dumps(json_data),
        description="JSON configuration"
    )
    print(f"JSON Field: {json_field.name} = {json_field.value}")
    print(f"Validation: {json_field.validate()}")
    
    return [string_field, int_field, float_field, bool_field, json_field]

def test_message_schema_creation():
    """Test MessageSchema creation"""
    print("\n=== Testing MessageSchema Creation ===")
    
    # Create fields for a sensor message
    timestamp_field = FieldSchema(
        name="timestamp",
        data_type=DataType.STRING,
        value="2024-01-15T10:30:00Z",
        description="Event timestamp"
    )
    
    sensor_id_field = FieldSchema(
        name="sensor_id",
        data_type=DataType.STRING,
        value="sensor_001",
        description="Sensor identifier"
    )
    
    value_field = FieldSchema(
        name="value",
        data_type=DataType.FLOAT,
        value=23.5,
        min_value=-100.0,
        max_value=100.0,
        description="Sensor reading"
    )
    
    unit_field = FieldSchema(
        name="unit",
        data_type=DataType.STRING,
        value="°C",
        allowed_values=["°C", "°F", "K", "Pa", "V"],
        description="Measurement unit"
    )
    
    # Create message schema
    sensor_message = MessageSchema(
        name="sensor_data",
        fields=[timestamp_field, sensor_id_field, value_field, unit_field]
    )
    
    print(f"Message Schema: {sensor_message.name}")
    print(f"Number of fields: {len(sensor_message.value)}")
    print(f"Validation: {sensor_message.validate()}")
    
    # Add another field dynamically
    status_field = FieldSchema(
        name="status",
        data_type=DataType.STRING,
        value="OK",
        allowed_values=["OK", "ERROR", "WARNING"],
        description="Sensor status"
    )
    sensor_message.add_field(status_field)
    
    print(f"After adding field - Number of fields: {len(sensor_message.value)}")
    
    return sensor_message

def test_topic_schema_creation():
    """Test TopicSchema creation"""
    print("\n=== Testing TopicSchema Creation ===")
    
    # Create a message schema first
    message_fields = [
        FieldSchema(
            name="device_id",
            data_type=DataType.STRING,
            value="device_001",
            description="Device identifier"
        ),
        FieldSchema(
            name="command",
            data_type=DataType.STRING,
            value="START",
            allowed_values=["START", "STOP", "PAUSE", "RESET"],
            description="Command to execute"
        ),
        FieldSchema(
            name="parameters",
            data_type=DataType.JSON,
            value=json.dumps({"speed": 100, "mode": "auto"}),
            description="Command parameters"
        )
    ]
    
    command_message = MessageSchema(
        name="device_command",
        fields=message_fields
    )
    
    # Create topic schema with the message schema
    command_topic = TopicSchema(
        name="devices/001/commands",
        message_schema=command_message
    )
    
    print(f"Topic Schema: {command_topic.name}")
    print(f"Topic Message Schema: {command_topic.value.name}")
    print(f"Topic Validation: {command_topic.validate()}")
    
    return command_topic

def test_mqtt_broker_config():
    """Test MQTTBrokerConfig creation"""
    print("\n=== Testing MQTTBrokerConfig ===")
    
    # Test with default values
    default_config = MQTTBrokerConfig()
    print(f"Default Config: address={default_config.value[0].value}, port={default_config.value[1].value}")
    print(f"Config Validation: {all(field.validate()[0] for field in default_config.value)}")
    
    # Test with custom values
    custom_config = MQTTBrokerConfig(address="192.168.1.100", port=8883)
    print(f"Custom Config: address={custom_config.value[0].value}, port={custom_config.value[1].value}")
    
    return custom_config

def test_all_topics_schema():
    """Test AllTopicsSchema creation"""
    print("\n=== Testing AllTopicsSchema ===")
    
    # Create AllTopicsSchema
    all_topics = AllTopicsSchema()
    
    # Create some topics
    # Topic 1: Temperature sensor
    temp_fields = [
        FieldSchema(name="timestamp", data_type=DataType.STRING, value="2024-01-15T10:30:00Z"),
        FieldSchema(name="value", data_type=DataType.FLOAT, value=22.5),
        FieldSchema(name="unit", data_type=DataType.STRING, value="°C")
    ]
    temp_message = MessageSchema(name="temperature_data", fields=temp_fields)
    temp_topic = TopicSchema(name="sensors/temperature/room1", message_schema=temp_message)
    
    # Topic 2: Status updates
    status_fields = [
        FieldSchema(name="device", data_type=DataType.STRING, value="server_001"),
        FieldSchema(name="status", data_type=DataType.STRING, value="online"),
        FieldSchema(name="cpu_usage", data_type=DataType.FLOAT, value=45.2)
    ]
    status_message = MessageSchema(name="status_update", fields=status_fields)
    status_topic = TopicSchema(name="status/server_001", message_schema=status_message)
    
    # Add topics to AllTopicsSchema
    all_topics.add_topic("temperature_topic", temp_topic)
    all_topics.add_topic("status_topic", status_topic)
    
    print(f"AllTopicsSchema has {len(all_topics.value)} topics")
    for topic in all_topics.value:
        print(f"  - {topic.name}: {topic.value.name}")
    
    return all_topics

def test_config_manager_creation():
    """Test ConfigManager creation"""
    print("\n=== Testing ConfigManager ===")
    
    # Create broker config
    broker_config = MQTTBrokerConfig(address="mqtt.example.com", port=1883)
    
    # Create topics schema
    all_topics = AllTopicsSchema()
    
    # Add a topic
    simple_fields = [
        FieldSchema(name="message", data_type=DataType.STRING, value="Hello MQTT"),
        FieldSchema(name="counter", data_type=DataType.INTEGER, value=1)
    ]
    simple_message = MessageSchema(name="simple_message", fields=simple_fields)
    simple_topic = TopicSchema(name="test/topic", message_schema=simple_message)
    all_topics.add_topic("test_topic", simple_topic)
    
    # Create ConfigManager
    config_manager = ConfigManager(broker_config, all_topics)
    
    print(f"ConfigManager name: {config_manager.name}")
    print(f"Number of main fields: {len(config_manager.value)}")
    print(f"Broker config address: {config_manager.mqtt_broker_config.value[0].value}")
    print(f"Number of topics: {len(config_manager.all_topics_schema.value)}")
    
    return config_manager

def test_topic_data_type():
    """Test TopicDataType functionality"""
    print("\n=== Testing TopicDataType ===")
    
    # Create TopicDataType
    topic_data = TopicDataType(topic="sensors/temperature")
    
    # Add variables
    topic_data.add_variable("timestamp", "2024-01-15T10:30:00Z")
    topic_data.add_variable("temperature", 22.5)
    topic_data.add_variable("unit", "°C")
    topic_data.add_variable("sensor_id", "temp_sensor_001")
    
    print(f"Topic: {topic_data.topic}")
    print(f"Variables: {topic_data.args}")
    
    # Test encoding
    encoded = topic_data.encode()
    print(f"Encoded: {encoded}")
    
    # Test decoding
    new_topic_data = TopicDataType(topic="sensors/temperature")
    new_topic_data.decode(encoded)
    print(f"Decoded variables: {new_topic_data.args}")
    
    # Test setting variable
    new_topic_data.set_variable("temperature", 23.1)
    print(f"After update - temperature: {new_topic_data.args['temperature']}")
    
    return topic_data

def test_manual_mqtt_config_manager():
    """Test manual initialization of MQTTConfigManager"""
    print("\n=== Testing Manual MQTTConfigManager ===")
    
    # Create manual configuration
    mqtt_settings = {
        "address": "manual.broker.com",
        "port": 1883,
        "username": "admin",
        "password": "secret"
    }
    
    # Create topics manually
    manual_topic_fields = [
        FieldSchema(
            name="manual_field",
            data_type=DataType.STRING,
            value="manual_value",
            description="Manually created field"
        )
    ]
    
    manual_message = MessageSchema(
        name="manual_message",
        fields=manual_topic_fields
    )
    
    manual_topic = TopicSchema(
        name="manual/topic",
        message_schema=manual_message
    )
    
    topics_dict = {
        "manual_topic": manual_topic
    }
    
    # Create manual config manager
    manual_manager = MQTTConfigManager.manual_init(mqtt_settings, topics_dict)
    
    print(f"Manual Manager MQTT Settings: {manual_manager._mqtt_settings}")
    print(f"Manual Manager Topics: {list(manual_manager._topics.keys())}")
    
    return manual_manager

def run_all_tests():
    """Run all initialization tests"""
    print("=" * 60)
    print("SCHEMA INITIALIZATION TESTS")
    print("=" * 60)
    
    # Run all tests
    test_results = {}
    
    try:
        test_results["field_schema"] = test_field_schema_creation()
        print("✓ FieldSchema creation passed")
    except Exception as e:
        print(f"✗ FieldSchema creation failed: {e}")
    
    try:
        test_results["message_schema"] = test_message_schema_creation()
        print("✓ MessageSchema creation passed")
    except Exception as e:
        print(f"✗ MessageSchema creation failed: {e}")
    
    try:
        test_results["topic_schema"] = test_topic_schema_creation()
        print("✓ TopicSchema creation passed")
    except Exception as e:
        print(f"✗ TopicSchema creation failed: {e}")
    
    try:
        test_results["broker_config"] = test_mqtt_broker_config()
        print("✓ MQTTBrokerConfig creation passed")
    except Exception as e:
        print(f"✗ MQTTBrokerConfig creation failed: {e}")
    
    try:
        test_results["all_topics"] = test_all_topics_schema()
        print("✓ AllTopicsSchema creation passed")
    except Exception as e:
        print(f"✗ AllTopicsSchema creation failed: {e}")
    
    try:
        test_results["config_manager"] = test_config_manager_creation()
        print("✓ ConfigManager creation passed")
    except Exception as e:
        print(f"✗ ConfigManager creation failed: {e}")
    
    try:
        test_results["topic_data_type"] = test_topic_data_type()
        print("✓ TopicDataType creation passed")
    except Exception as e:
        print(f"✗ TopicDataType creation failed: {e}")
    
    try:
        test_results["manual_manager"] = test_manual_mqtt_config_manager()
        print("✓ Manual MQTTConfigManager creation passed")
    except Exception as e:
        print(f"✗ Manual MQTTConfigManager creation failed: {e}")
    
    print("\n" + "=" * 60)
    print("ALL INITIALIZATION TESTS COMPLETED")
    print("=" * 60)
    
    return test_results

if __name__ == "__main__":
    run_all_tests()
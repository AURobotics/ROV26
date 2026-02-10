# test schema from config File
import sys
import os
import tempfile
import yaml
import json
from pathlib import Path

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

def create_sample_yaml_config():
    """Create a sample YAML configuration file for testing"""
    config_data = {
        "mqtt_broker_config": {
            "address": "test.broker.com",
            "port": 1883,
        },
        "all_topics_schema": {
            "sensors/temperature": {
                "name": "sensors/temperature",
                "type": "custom",
                "value": {
                    "name": "temperature_message",
                    "type": "custom",
                    "value": [
                        {
                            "name": "timestamp",
                            "type": "string",
                            "value": "2024-01-15T10:30:00Z",
                            "description": "Measurement timestamp"
                        },
                        {
                            "name": "value",
                            "type": "float",
                            "value": 22.5,
                            "min_value": -50.0,
                            "max_value": 100.0,
                            "description": "Temperature value"
                        },
                        {
                            "name": "unit",
                            "type": "string",
                            "value": "°C",
                            "allowed_values": ["°C", "°F", "K"],
                            "description": "Temperature unit"
                        },
                        {
                            "name": "sensor_id",
                            "type": "string",
                            "value": "sensor_001",
                            "pattern": "^sensor_[0-9]{3}$",
                            "description": "Sensor identifier"
                        }
                    ],
                    "description": "Temperature sensor message format"
                },
                "description": "Temperature sensor topic"
            },
            "devices/commands": {
                "name": "devices/commands",
                "type": "custom",
                "value": {
                    "name": "device_command",
                    "type": "custom",
                    "value": [
                        {
                            "name": "command",
                            "type": "string",
                            "value": "START",
                            "allowed_values": ["START", "STOP", "PAUSE", "RESET"],
                            "description": "Command type"
                        },
                        {
                            "name": "device_id",
                            "type": "string",
                            "value": "device_001",
                            "description": "Target device ID"
                        },
                        {
                            "name": "parameters",
                            "type": "json",
                            "value": json.dumps({"speed": 100, "mode": "auto"}),
                            "description": "Command parameters"
                        },
                        {
                            "name": "timestamp",
                            "type": "string",
                            "value": "2024-01-15T10:30:00Z",
                            "description": "Command timestamp"
                        }
                    ],
                    "description": "Device command message format"
                },
                "description": "Device commands topic"
            }
        }
    }
    
    # Create a YAML file with the sample configuration
    file = open("sample_config.yaml", "w")
    yaml.dump(config_data, file)
    file.close()
    
    return Path(file.name), config_data

def test_field_schema_from_config():
    """Test FieldSchema.from_config method"""
    print("=== Testing FieldSchema.from_config ===")
    
    # Test different field types from config
    test_configs = [
        {
            "name": "string_field",
            "type": "string",
            "value": "test_value",
            "pattern": "^[a-z_]+$",
            "description": "Test string field"
        },
        {
            "name": "integer_field",
            "type": "integer",
            "value": 42,
            "min_value": 0,
            "max_value": 100,
            "description": "Test integer field"
        },
        {
            "name": "float_field",
            "type": "float",
            "value": 3.14159,
            "description": "Test float field"
        },
        {
            "name": "boolean_field",
            "type": "boolean",
            "value": True,
            "description": "Test boolean field"
        },
        {
            "name": "json_field",
            "type": "json",
            "value": json.dumps({"key": "value", "array": [1, 2, 3]}),
            "description": "Test JSON field"
        }
    ]
    
    results = []
    for config in test_configs:
        try:
            field = FieldSchema.from_config(config)
            is_valid, error = field.validate()
            print(f"✓ {field.name}: type={field.data_type}, value={field.value}, valid={is_valid}")
            results.append((field, is_valid))
        except Exception as e:
            print(f"✗ {config.get('name', 'unknown')}: {e}")
            results.append((None, False))
    
    return results

def test_message_schema_from_config():
    """Test MessageSchema.from_config method"""
    print("\n=== Testing MessageSchema.from_config ===")
    
    message_config = {
        "name": "sensor_data",
        "type": "custom",
        "value": [
            {
                "name": "sensor_id",
                "type": "string",
                "value": "sensor_001",
                "description": "Sensor identifier"
            },
            {
                "name": "reading",
                "type": "float",
                "value": 25.5,
                "min_value": -50.0,
                "max_value": 150.0,
                "description": "Sensor reading"
            },
            {
                "name": "timestamp",
                "type": "string",
                "value": "2024-01-15T10:30:00Z",
                "description": "Reading timestamp"
            },
            {
                "name": "status",
                "type": "string",
                "value": "OK",
                "allowed_values": ["OK", "ERROR", "WARNING"],
                "description": "Sensor status"
            }
        ],
        "description": "Sensor data message format"
    }
    
    try:
        message_schema = MessageSchema.from_config(message_config)
        is_valid, error = message_schema.validate()
        
        print(f"Message Schema: {message_schema.name}")
        print(f"Number of fields: {len(message_schema.value)}")
        print(f"Validation result: valid={is_valid}")
        
        if not is_valid:
            print(f"Validation error: {error}")
        
        # Display field details
        for field in message_schema.value:
            print(f"  - {field.name}: {field.value} ({field.data_type})")
        
        return message_schema, is_valid
    except Exception as e:
        print(f"✗ Failed to create MessageSchema from config: {e}")
        return None, False

def test_topic_schema_from_config():
    """Test TopicSchema.from_config method"""
    print("\n=== Testing TopicSchema.from_config ===")
    
    topic_config = {
        "name": "sensors/temperature/room1",
        "type": "custom",
        "value": {
            "name": "temperature_message",
            "type": "custom",
            "value": [
                {
                    "name": "value",
                    "type": "float",
                    "value": 22.5,
                    "description": "Temperature value"
                },
                {
                    "name": "unit",
                    "type": "string",
                    "value": "°C",
                    "description": "Temperature unit"
                }
            ],
            "description": "Temperature message format"
        },
        "description": "Room temperature sensor topic"
    }
    
    try:
        topic_schema = TopicSchema.from_config(topic_config)
        is_valid, error = topic_schema.validate()
        
        print(f"Topic Schema: {topic_schema.name}")
        print(f"Message Schema: {topic_schema.value.name}")
        print(f"Number of message fields: {len(topic_schema.value.value)}")
        print(f"Validation result: valid={is_valid}")
        
        return topic_schema, is_valid
    except Exception as e:
        print(f"✗ Failed to create TopicSchema from config: {e}")
        return None, False

def test_main_field_schema_from_config():
    """Test MainFieldSchema.from_config method"""
    print("\n=== Testing MainFieldSchema.from_config ===")
    
    main_field_config = {
        "name": "mqtt_configuration",
        "value": [
            {
                "name": "broker_address",
                "type": "string",
                "value": "mqtt.example.com",
                "description": "MQTT broker address"
            },
            {
                "name": "broker_port",
                "type": "integer",
                "value": 1883,
                "min_value": 1,
                "max_value": 65535,
                "description": "MQTT broker port"
            },
            {
                "name": "timeout",
                "type": "integer",
                "value": 30,
                "min_value": 1,
                "max_value": 300,
                "description": "Connection timeout in seconds"
            }
        ],
        "description": "MQTT broker configuration"
    }
    
    try:
        main_field_schema = MainFieldSchema.from_config(main_field_config)
        
        print(f"MainFieldSchema: {main_field_schema.name}")
        print(f"Number of fields: {len(main_field_schema.value)}")
        print(f"Description: {main_field_schema.description}")
        
        # Validate all fields
        all_valid = True
        for field in main_field_schema.value:
            is_valid, error = field.validate()
            if not is_valid:
                print(f"  ✗ {field.name}: {error}")
                all_valid = False
            else:
                print(f"  ✓ {field.name}: {field.value}")
        
        return main_field_schema, all_valid
    except Exception as e:
        print(f"✗ Failed to create MainFieldSchema from config: {e}")
        return None, False

def test_mqtt_config_manager_from_yaml():
    """Test MQTTConfigManager loading from YAML file"""
    print("\n=== Testing MQTTConfigManager from YAML ===")
    
    # Create a temporary YAML config file
    config_path, config_data = create_sample_yaml_config()
    
    try:
        # Load configuration using MQTTConfigManager
        config_manager = MQTTConfigManager(str(config_path))
        
        print(f"Config loaded from: {config_path}")
        
        # Test MQTT settings
        mqtt_settings = config_manager.mqtt_settings
        print(f"\nMQTT Settings:")
        print(f"  Address: {mqtt_settings.get('address')}")
        print(f"  Port: {mqtt_settings.get('port')}")
        print(f"  Username: {mqtt_settings.get('username')}")
        
        # Test topics
        topics = config_manager.topics
        print(f"\nTopics loaded: {len(topics)}")
        
        for topic_name, topic_schema in topics.items():
            print(f"\n  Topic: {topic_name}")
            print(f"    Description: {topic_schema.description}")
            print(f"    Message Schema: {topic_schema.value.name}")
            print(f"    Message Fields: {len(topic_schema.value.value)}")
            
            # Validate the topic
            is_valid, error = topic_schema.validate()
            print(f"    Valid: {is_valid}")
            if not is_valid:
                print(f"    Error: {error}")
        
        return config_manager, len(topics) > 0
        
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return None, False

def test_config_update_workflow():
    """Test the complete workflow: load -> modify -> save"""
    print("\n=== Testing Config Update Workflow ===")
    
    # Create initial config
    config_path, original_config = create_sample_yaml_config()
    
    try:
        # 1. Load configuration
        config_manager = MQTTConfigManager(str(config_path))
        print("1. ✓ Configuration loaded successfully")
        
        # 2. Get existing topic and modify it
        topic_name = "sensors/temperature"
        topic_schema = config_manager.get_topic(topic_name)
        
        if topic_schema:
            print(f"2. ✓ Retrieved topic: {topic_name}")
            
            # Modify a field value
            message_schema = topic_schema.value
            for field in message_schema.value:
                if field.name == "value":
                    original_value = field.value
                    field.value = 24.8  # Update temperature value
                    print(f"3. ✓ Updated field '{field.name}' from {original_value} to {field.value}")
                    break
        
        # 3. Add a new topic dynamically
        new_fields = [
            FieldSchema(
                name="humidity",
                data_type=DataType.FLOAT,
                value=65.2,
                min_value=0.0,
                max_value=100.0,
                description="Humidity percentage"
            ),
            FieldSchema(
                name="timestamp",
                data_type=DataType.STRING,
                value="2024-01-15T11:00:00Z",
                description="Measurement time"
            )
        ]
        
        new_message = MessageSchema(
            name="humidity_message",
            fields=new_fields
        )
        
        new_topic = TopicSchema(
            name="sensors/humidity/room1",
            message_schema=new_message
        )
        
        config_manager.add_topic(new_topic.name, new_topic)
        print("4. ✓ Added new topic: sensors/humidity/room1")
        
        # 4. Update MQTT settings
        config_manager.change_mqtt_address("new_address")
        config_manager.change_mqtt_port(1884)
        print("5. ✓ Updated MQTT settings: address and port")
        
        # 5. Save updated configuration to a new file
        new_config_path = config_path.with_name(f"updated_{config_path.name}")
        config_manager.update_config(str(new_config_path))
        print(f"6. ✓ Saved updated configuration to: {new_config_path}")
        
        # 6. Verify the saved configuration
        new_conf_manager = MQTTConfigManager(str(new_config_path))
        saved_config = new_conf_manager.config_data
            
        print("7. ✓ Verified saved configuration structure:")
        print(f"   - MQTT settings keys: {list(saved_config.get('mqtt_broker_config', {}).keys())}")
        print(f"   - Number of topics: {len(saved_config.get('all_topics_schema', {}))}")
        
        return True
        
    except Exception as e:
        print(f"✗ Workflow failed: {e}")
        return False

def test_validation_errors():
    """Test validation error scenarios"""
    print("\n=== Testing Validation Errors ===")
    
    test_cases = [
        {
            "name": "invalid_type_conversion",
            "config": {
                "name": "age",
                "type": "integer",
                "value": "not_a_number",
                "description": "Should fail type conversion"
            },
            "expected_error": "type error"
        },
        {
            "name": "out_of_range",
            "config": {
                "name": "percentage",
                "type": "float",
                "value": 150.0,
                "min_value": 0.0,
                "max_value": 100.0,
                "description": "Should fail range check"
            },
            "expected_error": "must be <="
        },
        {
            "name": "pattern_mismatch",
            "config": {
                "name": "id",
                "type": "string",
                "value": "invalid id",
                "pattern": "^[a-z0-9_]+$",
                "description": "Should fail pattern match"
            },
            "expected_error": "doesn't match pattern"
        },
        {
            "name": "invalid_allowed_value",
            "config": {
                "name": "status",
                "type": "string",
                "value": "UNKNOWN",
                "allowed_values": ["OK", "ERROR", "WARNING"],
                "description": "Should fail allowed values check"
            },
            "expected_error": "must be one of"
        },
        {
            "name": "invalid_json",
            "config": {
                "name": "config",
                "type": "json",
                "value": "{invalid json",
                "description": "Should fail JSON parsing"
            },
            "expected_error": "must be valid JSON"
        }
    ]
    
    for test_case in test_cases:
        try:
            field = FieldSchema.from_config(test_case["config"])
            is_valid, error = field.validate()
            
            if not is_valid and test_case["expected_error"] in error:
                print(f"✓ {test_case['name']}: Correctly rejected with error: {error}")
            elif is_valid:
                print(f"✗ {test_case['name']}: Should have failed but passed")
            else:
                print(f"✗ {test_case['name']}: Failed with unexpected error: {error}")
                
        except Exception as e:
            if test_case["expected_error"] in str(e):
                print(f"✓ {test_case['name']}: Correctly raised exception: {e}")
            else:
                print(f"✗ {test_case['name']}: Unexpected exception: {e}")
    
    return len(test_cases)

def run_all_from_config_tests():
    """Run all from_config tests"""
    print("=" * 60)
    print("SCHEMA from_config TESTS")
    print("=" * 60)
    
    results = {}
    
    # Run tests
    tests = [
        ("FieldSchema.from_config", test_field_schema_from_config),
        ("MessageSchema.from_config", test_message_schema_from_config),
        ("TopicSchema.from_config", test_topic_schema_from_config),
        ("MainFieldSchema.from_config", test_main_field_schema_from_config),
        ("MQTTConfigManager from YAML", test_mqtt_config_manager_from_yaml),
        ("Config Update Workflow", test_config_update_workflow),
        ("Validation Errors", test_validation_errors)
    ]
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = test_func()
            results[test_name] = result
            print(f"  Result: {result}")
        except Exception as e:
            print(f"  ✗ Test failed: {e}")
            results[test_name] = None
    
    print("\n" + "=" * 60)
    print("ALL from_config TESTS COMPLETED")
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    run_all_from_config_tests()
"""
Comprehensive Test Suite for MQTT Schema System

This test suite validates:
1. Schema creation and validation (using public API)
2. Config manager operations
3. YAML save/load functionality
4. Message publishing with schema validation
5. Message subscription with schema decoding
6. Multi-topic communication
7. Error handling and edge cases

Note: Uses only public-facing APIs - abstract_schema modules are internal implementation details
"""

import time
import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import only public modules
try:
    from ..mqtt import Mqtt, Topic
    from ..schema.config_manager import MQTTConfigManager
    from ..schema.mqtt_schema_adapter import MessageSchema_to_MqttMessage_Adapter
    from ..schema.mqtt_schema_types import MQTTBrokerConfig, AllTopicsSchema, MessageSchema, TopicSchema
    from ..schema.abstract_schema_configuration.abstract_schema_data_types import DataType

except ImportError as e:
    raise


class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def record(self, test_name: str, passed: bool, message: str = ""):
        self.tests.append({
            "name": test_name,
            "passed": passed,
            "message": message
        })
        if passed:
            self.passed += 1
            print(f"✓ {test_name}")
        else:
            self.failed += 1
            print(f"✗ {test_name}: {message}")
    
    def summary(self):
        total = self.passed + self.failed
        print("\n" + "=" * 70)
        print(f"Test Summary: {self.passed}/{total} passed, {self.failed}/{total} failed")
        print("=" * 70)
        return self.failed == 0


def test_1_config_manager_basic(results: TestResults):
    """Test 1: Basic Config Manager operations"""
    print("\n" + "=" * 70)
    print("TEST 1: Config Manager Basic Operations")
    print("=" * 70)
    
    try:
        # Create config manager
        config_manager = MQTTConfigManager()
        results.record("1.1: Create MQTTConfigManager", True)
        
        # Create fields using the config manager's helper
        
        string_field = config_manager.create_field("device_name", DataType.STRING, "sensor_001")
        results.record("1.2: Create string field via config manager", True)
        
        int_field = config_manager.create_field("battery_level", DataType.INTEGER, 85)
        results.record("1.3: Create integer field via config manager", True)
        
        float_field = config_manager.create_field("temperature", DataType.FLOAT, 22.5)
        results.record("1.4: Create float field via config manager", True)
        
        bool_field = config_manager.create_field("is_active", DataType.BOOLEAN, True)
        results.record("1.5: Create boolean field via config manager", True)
        
        # Create a message schema
        message_schema = config_manager.create_message_schema([
            string_field, int_field, float_field, bool_field
        ])
        results.record("1.6: Create message schema", True)
        
        # Validate the schema
        is_valid, error = message_schema.validate()
        results.record("1.7: Validate message schema", is_valid, error if not is_valid else "")
        
    except Exception as e:
        print(f"Test 1 failed with exception: {e}")
        results.record("1.x: Config manager basic operations", False, str(e))


def test_2_topic_management(results: TestResults):
    """Test 2: Topic management through Config Manager"""
    print("\n" + "=" * 70)
    print("TEST 2: Topic Management")
    print("=" * 70)
    
    try:
        config_manager = MQTTConfigManager()
        
        # Create a sensor data topic
        sensor_fields = [
            config_manager.create_field("sensor_id", DataType.STRING, "SENS_001"),
            config_manager.create_field("temperature", DataType.FLOAT, 22.5),
            config_manager.create_field("humidity", DataType.FLOAT, 45.0),
            config_manager.create_field("timestamp", DataType.INTEGER, int(time.time()))
        ]
        
        sensor_message = config_manager.create_message_schema(sensor_fields)
        sensor_topic = TopicSchema(name="sensors/living_room", message_schema=sensor_message)
        
        # Add topic
        config_manager.add_topic(sensor_topic)
        results.record("2.1: Add topic to config manager", True)
        
        # Get topic names
        topic_names = config_manager.topic_names
        results.record("2.2: Get topic names", "sensors/living_room" in topic_names)
        
        # Get topic schema
        retrieved_topic = config_manager.get_topic_schema("sensors/living_room")
        results.record("2.3: Get topic schema", retrieved_topic is not None)
        
        # Get message schema
        message_schema = config_manager.get_message_schema("sensors/living_room")
        results.record("2.4: Get message schema", message_schema is not None)
        
        # Add another topic
        device_fields = [
            config_manager.create_field("device_id", DataType.STRING, "DEV_001"),
            config_manager.create_field("status", DataType.STRING, "online")
        ]
        device_message = config_manager.create_message_schema(device_fields)
        device_topic = TopicSchema(name="devices/status", message_schema=device_message)
        config_manager.add_topic(device_topic)
        
        # Update topic
        updated_fields = device_fields + [config_manager.create_field("battery", DataType.INTEGER, 85)]
        updated_message = config_manager.create_message_schema(updated_fields)
        updated_topic = TopicSchema(name="devices/status", message_schema=updated_message)
        config_manager.update_topic(updated_topic)
        results.record("2.5: Update topic", True)
        
        # Change MQTT settings
        config_manager.change_mqtt_address("192.168.1.100")
        config_manager.change_mqtt_port(1884)
        mqtt_settings = config_manager.mqtt_settings
        results.record("2.6: Change MQTT settings", 
                      mqtt_settings["address"] == "192.168.1.100" and mqtt_settings["port"] == 1884)
        
        # Reset to localhost for testing
        config_manager.change_mqtt_address("localhost")
        config_manager.change_mqtt_port(1883)
        
    except Exception as e:
        print(f"Test 2 failed with exception: {e}")
        results.record("2.x: Topic management", False, str(e))


def test_3_yaml_persistence(results: TestResults):
    """Test 3: YAML save and load"""
    print("\n" + "=" * 70)
    print("TEST 3: YAML Persistence")
    print("=" * 70)
    
    yaml_file = "./R&D/software/communication/Float/test/tmp/test_mqtt_config.yaml"
    
    try:
        # Create config manager with topics
        config_manager = MQTTConfigManager()
        
        # Add multiple topics
        topics_data = [
            {
                "name": "sensors/temperature",
                "fields": [
                    ("value", DataType.FLOAT, 22.5),
                    ("unit", DataType.STRING, "celsius")
                ]
            },
            {
                "name": "sensors/humidity",
                "fields": [
                    ("value", DataType.FLOAT, 45.0),
                    ("unit", DataType.STRING, "percent")
                ]
            }
        ]
        
        for topic_data in topics_data:
            fields = [config_manager.create_field(name, dtype, value) 
                     for name, dtype, value in topic_data["fields"]]
            message_schema = config_manager.create_message_schema(fields)
            topic_schema = TopicSchema(name=topic_data["name"], message_schema=message_schema)
            config_manager.add_topic(topic_schema)
        
        # Save to YAML
        config_manager.save_config(yaml_file)
        results.record("3.1: Save config to YAML", Path(yaml_file).exists())
        
        # Load from YAML
        loaded_manager = MQTTConfigManager(config_path=yaml_file)
        results.record("3.2: Load config from YAML", True)
        
        # Verify loaded topics
        loaded_topics = loaded_manager.topic_names
        results.record("3.3: Verify loaded topics", 
                      "sensors/temperature" in loaded_topics and "sensors/humidity" in loaded_topics)
        
        # Verify loaded message schema
        temp_schema = loaded_manager.get_message_schema("sensors/temperature")
        results.record("3.4: Verify loaded message schema", temp_schema is not None)
        
        
    except Exception as e:
        print(f"Test 3 failed with exception: {e}")
        results.record("3.x: YAML persistence", False, str(e))


def test_4_schema_adapter(results: TestResults):
    """Test 4: MessageSchema to MqttMessage adapter"""
    print("\n" + "=" * 70)
    print("TEST 4: Schema Adapter")
    print("=" * 70)
    
    try:
        config_manager = MQTTConfigManager()
        
        # Create message schema
        fields = [
            config_manager.create_field("message_id", DataType.STRING, "MSG_001"),
            config_manager.create_field("count", DataType.INTEGER, 42),
            config_manager.create_field("is_valid", DataType.BOOLEAN, True)
        ]
        message_schema = config_manager.create_message_schema(fields)
        
        # Create adapter
        adapter = MessageSchema_to_MqttMessage_Adapter(message_schema)
        results.record("4.1: Create adapter from schema", True)
        
        # Verify initial values from schema
        results.record("4.2: Adapter initialized with schema values",
                      adapter.args["message_id"] == "MSG_001" and 
                      adapter.args["count"] == 42 and
                      adapter.args["is_valid"] == True)
        
        # Test set_variable
        adapter.set_variable("count", 100)
        results.record("4.3: Set variable in adapter", adapter.args["count"] == 100)
        
        # Test encode
        encoded = adapter.encode()
        results.record("4.4: Encode adapter to JSON", isinstance(encoded, str))
        
        # Test decode
        new_adapter = MessageSchema_to_MqttMessage_Adapter(message_schema)
        new_adapter.decode(encoded)
        results.record("4.5: Decode JSON to adapter", new_adapter.args["count"] == 100)
        
    except Exception as e:
        print(f"Test 4 failed with exception: {e}")
        results.record("4.x: Schema adapter", False, str(e))


def test_5_publish_subscribe(results: TestResults):
    """Test 5: Publish and Subscribe with schema"""
    print("\n" + "=" * 70)
    print("TEST 5: Publish and Subscribe with Schema")
    print("=" * 70)
    
    try:
        # Create MQTT connection
        mqtt_conn = Mqtt(address='localhost', port=1883)
        results.record("5.1: Create MQTT connection", True)
        
        # Create config manager and schema
        config_manager = MQTTConfigManager()
        
        # Create sensor schema
        sensor_fields = [
            config_manager.create_field("sensor_id", DataType.STRING, "SENSOR_001"),
            config_manager.create_field("temperature", DataType.FLOAT, 0.0),
            config_manager.create_field("humidity", DataType.FLOAT, 0.0),
            config_manager.create_field("timestamp", DataType.INTEGER, 0)
        ]
        sensor_schema = config_manager.create_message_schema(sensor_fields)
        
        # Create topic
        topic_name = "test/sensors/data"
        topic = Topic(topic_name, mqtt_conn)
        
        # Create subscriber message handler
        subscriber_handler = MessageSchema_to_MqttMessage_Adapter(sensor_schema)
        topic.subscribe(subscriber_handler)
        results.record("5.2: Subscribe to topic with schema adapter", True)
        
        # Wait for subscription to establish
        time.sleep(2)
        
        # Create publisher message handler
        publisher_handler = MessageSchema_to_MqttMessage_Adapter(sensor_schema)
        
        # Publish multiple messages
        test_data = [
            {"sensor_id": "SENSOR_001", "temperature": 22.5, "humidity": 45.0, "timestamp": int(time.time())},
            {"sensor_id": "SENSOR_002", "temperature": 23.8, "humidity": 48.5, "timestamp": int(time.time())},
            {"sensor_id": "SENSOR_003", "temperature": 21.2, "humidity": 42.0, "timestamp": int(time.time())}
        ]
        
        for i, data in enumerate(test_data):
            for key, value in data.items():
                publisher_handler.set_variable(key, value)
            
            topic.publish(publisher_handler.encode())
            print(f"Published message {i+1}: {data}")
            time.sleep(0.5)
        
        # Wait for messages to be received
        time.sleep(2)
        
        # Verify last received message
        last_received = subscriber_handler.args
        results.record("5.3: Receive published messages",
                      last_received["sensor_id"] == "SENSOR_003")
        
        # disconnect
        mqtt_conn.disconnect()
        
    except Exception as e:
        print(f"Test 5 failed with exception: {e}")
        results.record("5.x: Publish/Subscribe", False, str(e))


def test_6_multi_topic_communication(results: TestResults):
    """Test 6: Multiple topics with different schemas"""
    print("\n" + "=" * 70)
    print("TEST 6: Multi-Topic Communication")
    print("=" * 70)
    
    try:
        # Create config manager
        config_manager = MQTTConfigManager()
        
        # Define multiple topics with different schemas
        topics_config = [
            {
                "name": "test/temperature",
                "fields": [
                    ("celsius", DataType.FLOAT, 22.5),
                    ("location", DataType.STRING, "living_room")
                ]
            },
            {
                "name": "test/humidity",
                "fields": [
                    ("percent", DataType.FLOAT, 45.0),
                    ("location", DataType.STRING, "living_room")
                ]
            },
            {
                "name": "test/alerts",
                "fields": [
                    ("alert_type", DataType.STRING, "temperature"),
                    ("severity", DataType.STRING, "warning"),
                    ("message", DataType.STRING, "Temperature threshold exceeded")
                ]
            }
        ]
        
        # Add topics to config manager
        for topic_config in topics_config:
            fields = [config_manager.create_field(name, dtype, value) 
                     for name, dtype, value in topic_config["fields"]]
            message_schema = config_manager.create_message_schema(fields)
            topic_schema = TopicSchema(name=topic_config["name"], message_schema=message_schema)
            config_manager.add_topic(topic_schema)
        
        results.record("6.1: Add multiple topics to config manager", True)
        
        # Get all topics and their messages
        all_topics_messages = config_manager.get_all_topics_messages()
        results.record("6.2: Get all topics and message handlers",
                      len(all_topics_messages) == 3)
        
        # Subscribe to all topics
        subscribers = {}
        for topic, message_handler in all_topics_messages.items():
            topic.subscribe(message_handler)
            subscribers[topic.topic_name] = message_handler
            print(f"Subscribed to: {topic.topic_name}")
        
        results.record("6.3: Subscribe to all topics", len(subscribers) == 3)
        
        # Wait for subscriptions
        time.sleep(2)
        
        # Publish messages to each topic
        test_messages = [
            {"topic": "test/temperature", "data": {"celsius": 25.5, "location": "bedroom"}},
            {"topic": "test/humidity", "data": {"percent": 52.0, "location": "bedroom"}},
            {"topic": "test/alerts", "data": {"alert_type": "humidity", "severity": "info", 
                                              "message": "Humidity normal"}}
        ]
        
        for msg in test_messages:
            topic_schema = config_manager.get_topic_schema(msg["topic"])
            if topic_schema:
                publisher = MessageSchema_to_MqttMessage_Adapter(topic_schema.value)
                for key, value in msg["data"].items():
                    publisher.set_variable(key, value)
                
                topic = Topic(msg["topic"], config_manager.mqtt)
                topic.publish(publisher.encode())
                print(f"Published to {msg['topic']}: {msg['data']}")
                time.sleep(0.5)
        
        # Wait for messages
        time.sleep(2)
        
        # Verify received messages
        verification_count = 0
        for topic_name, handler in subscribers.items():
            if handler.args:
                print(f"Received on {topic_name}: {handler.args}")
                verification_count += 1
        
        results.record("6.4: Verify multi-topic message delivery",
                      verification_count >= 1)
        
        # disconnect
        config_manager.mqtt.disconnect()
        
    except Exception as e:
        print(f"Test 6 failed with exception: {e}")
        results.record("6.x: Multi-topic communication", False, str(e))


def test_7_error_handling(results: TestResults):
    """Test 7: Error handling and edge cases"""
    print("\n" + "=" * 70)
    print("TEST 7: Error Handling")
    print("=" * 70)
    
    try:
        config_manager = MQTTConfigManager()
        
        # Test 1: Set non-existent variable in adapter
        fields = [config_manager.create_field("field1", DataType.STRING, "value1")]
        schema = config_manager.create_message_schema(fields)
        adapter = MessageSchema_to_MqttMessage_Adapter(schema)
        
        try:
            adapter.set_variable("non_existent", "value")
            results.record("7.1: Reject non-existent variable", False, "Should have raised KeyError")
        except KeyError:
            results.record("7.1: Reject non-existent variable", True)
        
        # Test 2: Invalid JSON decode
        try:
            adapter.decode("invalid json{")
            results.record("7.2: Reject invalid JSON", False, "Should have raised ValueError")
        except ValueError:
            results.record("7.2: Reject invalid JSON", True)
        
        # Test 3: Remove non-existent topic
        try:
            config_manager.remove_topic("non_existent_topic")
            results.record("7.3: Reject remove non-existent topic", False, "Should have raised KeyError")
        except KeyError:
            results.record("7.3: Reject remove non-existent topic", True)
        
        # Test 4: Add variable to adapter
        adapter.add_variable("new_field", "new_value")
        results.record("7.4: Add variable to adapter", adapter.args["new_field"] == "new_value")
        
    except Exception as e:
        print(f"Test 7 failed with exception: {e}")
        results.record("7.x: Error handling", False, str(e))


def test_8_integration(results: TestResults):
    """Test 8: Complete integration test with ConfigManager"""
    print("\n" + "=" * 70)
    print("TEST 8: ConfigManager Integration")
    print("=" * 70)
    
    yaml_file = "./R&D/software/communication/Float/test/tmp/test_integration_config.yaml"
    
    try:
        # Create comprehensive config
        config_manager = MQTTConfigManager()
        
        # Add IoT sensor system topics
        topics = [
            {
                "name": "home/living_room/temperature",
                "fields": [
                    ("celsius", DataType.FLOAT, 22.0),
                    ("timestamp", DataType.INTEGER, int(time.time()))
                ]
            },
            {
                "name": "home/living_room/humidity",
                "fields": [
                    ("percent", DataType.FLOAT, 45.0),
                    ("timestamp", DataType.INTEGER, int(time.time()))
                ]
            },
            {
                "name": "home/devices/thermostat",
                "fields": [
                    ("target_temp", DataType.FLOAT, 21.0),
                    ("mode", DataType.STRING, "auto"),
                    ("is_on", DataType.BOOLEAN, True)
                ]
            }
        ]
        
        for topic_data in topics:
            fields = [config_manager.create_field(name, dtype, value) 
                     for name, dtype, value in topic_data["fields"]]
            message_schema = config_manager.create_message_schema(fields)
            topic_schema = TopicSchema(name=topic_data["name"], message_schema=message_schema)
            config_manager.add_topic(topic_schema)
        
        results.record("8.1: Create comprehensive config", True)
        
        # Save config
        config_manager.save_config(yaml_file)
        results.record("8.2: Save comprehensive config", Path(yaml_file).exists())
        
        # Load config in new manager
        new_manager = MQTTConfigManager(config_path=yaml_file)
        results.record("8.3: Load comprehensive config", True)
        
        # Verify all topics loaded
        loaded_topics = set(new_manager.topic_names)
        expected_topics = {"home/living_room/temperature", "home/living_room/humidity", 
                          "home/devices/thermostat"}
        results.record("8.4: Verify all topics loaded", loaded_topics == expected_topics)
        
        # Test publish/subscribe with loaded config
        all_topics = new_manager.get_all_topics_messages()
        
        # Subscribe to temperature topic
        temp_topic = None
        temp_handler = None
        for topic, handler in all_topics.items():
            if topic.topic_name == "home/living_room/temperature":
                temp_topic = topic
                temp_handler = handler
                topic.subscribe(handler)
                break
        
        results.record("8.5: Subscribe using loaded config", temp_handler is not None)
        
        # Wait for subscription
        time.sleep(2)
        
        # Publish temperature update
        if temp_topic and temp_handler:
            temp_handler.set_variable("celsius", 24.5)
            temp_handler.set_variable("timestamp", int(time.time()))
            temp_topic.publish(temp_handler.encode())
            
            time.sleep(1)
            
            # Create new subscriber to verify
            verify_handler = MessageSchema_to_MqttMessage_Adapter(
                new_manager.get_message_schema("home/living_room/temperature") # type: ignore
            )
            verify_topic = Topic("home/living_room/temperature", new_manager.mqtt)
            verify_topic.subscribe(verify_handler)
            
            time.sleep(1)
            
            # Publish again
            temp_handler.set_variable("celsius", 25.0)
            temp_topic.publish(temp_handler.encode())
            
            time.sleep(1)
            
            results.record("8.6: Publish/Subscribe with loaded config",
                          verify_handler.args.get("celsius", 0) > 0)
        
        # disconnect
        new_manager.mqtt.disconnect()
        
    except Exception as e:
        print(f"Test 8 failed with exception: {e}")
        results.record("8.x: ConfigManager integration", False, str(e))


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("MQTT SCHEMA SYSTEM - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    results = TestResults()
    
    # Run all tests
    test_1_config_manager_basic(results)
    test_2_topic_management(results)
    test_3_yaml_persistence(results)
    test_4_schema_adapter(results)
    test_5_publish_subscribe(results)
    test_6_multi_topic_communication(results)
    test_7_error_handling(results)
    test_8_integration(results)
    
    # Print summary
    success = results.summary()
    
    # Print detailed results
    print("\nDetailed Results:")
    for test in results.tests:
        status = "✓" if test["passed"] else "✗"
        message = f" - {test['message']}" if test["message"] else ""
        print(f"{status} {test['name']}{message}")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

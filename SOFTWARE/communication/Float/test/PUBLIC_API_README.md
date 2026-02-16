# MQTT Schema System - Test Suite (Public API Version)

## Overview

This test suite validates the MQTT Schema System using **only public-facing APIs**. The internal abstract schema implementation is kept hidden as intended.

## Public API Modules

The tests use only these public modules:
- ✅ `base_types.py` - Base MQTT message types
- ✅ `mqtt.py` - MQTT connection and topic handling
- ✅ `config_manager.py` - **Primary public API** for schema management
- ✅ `mqtt_schema_adapter.py` - Schema to message adapter
- ✅ `mqtt_schema_types.py` - Schema type definitions
- ⚠️ `abstract_schema_data_types.py` - Only for DataType enum (minimal exposure)

The complex `abstract_schema.py` is **not directly imported** - all schema operations go through `config_manager.py`.

## Key Difference from Previous Version

### ❌ Old Approach (Direct Schema Manipulation)
```python
from abstract_schema import FieldSchema  # Direct access to internal API

# Creating fields directly
field = FieldSchema.string(name="device_name", value="sensor_001")
```

### ✅ New Approach (Through Config Manager)
```python
from config_manager import MQTTConfigManager
from abstract_schema_data_types import DataType

# Creating fields through public API
config = MQTTConfigManager()
field = config.create_field("device_name", DataType.STRING, "sensor_001")
```

## Files

### 1. `test_mqtt_schema_updated.py`
Comprehensive unit tests using public API:
- Config manager operations
- Topic management
- YAML persistence
- Schema adapter
- Publish/Subscribe
- Multi-topic communication
- Error handling
- Integration testing

**40+ test cases** covering all functionality

### 2. `test_real_world_examples_updated.py`
Real-world demonstrations using public API:
- **Smart Home**: Temperature monitoring and control
- **Industrial**: Sensor network monitoring
- **Fleet Tracking**: GPS and vehicle status

### 3. `run_tests_updated.py`
Test runner with pre-flight checks

## Quick Start

### Prerequisites
```bash
# 1. Start MQTT broker
mosquitto -v

# 2. Install dependencies
pip install paho-mqtt pyyaml

# 3. Ensure all modules are accessible
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Run Tests
```bash
# Run everything
python run_tests_updated.py

# Or run individually
python test_mqtt_schema_updated.py
python test_real_world_examples_updated.py
```

## Using the Public API

### Creating Schemas

```python
from config_manager import MQTTConfigManager
from mqtt_schema_types import TopicSchema
from abstract_schema_data_types import DataType

# 1. Create config manager
config = MQTTConfigManager()

# 2. Create fields using config manager's helper
temp_field = config.create_field("temperature", DataType.FLOAT, 22.5)
humidity_field = config.create_field("humidity", DataType.FLOAT, 45.0)
timestamp_field = config.create_field("timestamp", DataType.INTEGER, 0)

# 3. Create message schema
message_schema = config.create_message_schema([
    temp_field,
    humidity_field,
    timestamp_field
])

# 4. Create topic
topic_schema = TopicSchema(name="sensors/room1", message_schema=message_schema)

# 5. Add to config
config.add_topic(topic_schema)

# 6. Save to YAML
config.save_config("my_config.yaml")
```

### Publishing Messages

```python
from mqtt import Mqtt, Topic
from mqtt_schema_adapter import MessageSchema_to_MqttMessage_Adapter

# 1. Get the message schema
message_schema = config.get_message_schema("sensors/room1")

# 2. Create adapter
publisher = MessageSchema_to_MqttMessage_Adapter(message_schema)

# 3. Set values
publisher.set_variable("temperature", 23.5)
publisher.set_variable("humidity", 48.0)
publisher.set_variable("timestamp", int(time.time()))

# 4. Publish
topic = Topic("sensors/room1", config.mqtt)
topic.publish(publisher.encode())
```

### Subscribing to Topics

```python
# 1. Get message schema
message_schema = config.get_message_schema("sensors/room1")

# 2. Create subscriber handler
subscriber = MessageSchema_to_MqttMessage_Adapter(message_schema)

# 3. Subscribe
topic = Topic("sensors/room1", config.mqtt)
topic.subscribe(subscriber)

# 4. Access received data
# subscriber.args contains the latest message
print(subscriber.args["temperature"])
```

### Loading from YAML

```python
# Load existing configuration
config = MQTTConfigManager(config_path="my_config.yaml")

# Get all topics
all_topics = config.get_all_topics_messages()

# Subscribe to all
for topic, handler in all_topics.items():
    topic.subscribe(handler)
```

## Test Coverage

### Unit Tests (Test 1-8)
1. ✅ Config Manager Basic Operations
2. ✅ Topic Management
3. ✅ YAML Persistence
4. ✅ Schema Adapter
5. ✅ Publish/Subscribe
6. ✅ Multi-Topic Communication
7. ✅ Error Handling
8. ✅ Integration Testing

### Real-World Examples
1. ✅ Smart Home Temperature Control
2. ✅ Industrial Sensor Network
3. ✅ Vehicle Fleet Tracking

## API Benefits

Using the config manager as the primary API provides:

1. **Encapsulation**: Complex schema validation is hidden
2. **Simplicity**: One main entry point (`MQTTConfigManager`)
3. **Type Safety**: DataType enum ensures correct field types
4. **Validation**: All validation happens automatically
5. **Persistence**: Built-in YAML save/load
6. **Consistency**: All schemas follow the same patterns

## Common Patterns

### Pattern 1: Create from Scratch
```python
config = MQTTConfigManager()
# Add topics...
config.save_config("config.yaml")
```

### Pattern 2: Load and Extend
```python
config = MQTTConfigManager(config_path="config.yaml")
# Add more topics...
config.save_config("config.yaml")
```

### Pattern 3: Pub/Sub Workflow
```python
# Publisher side
publisher = MessageSchema_to_MqttMessage_Adapter(schema)
publisher.set_variable("field", value)
topic.publish(publisher.encode())

# Subscriber side
subscriber = MessageSchema_to_MqttMessage_Adapter(schema)
topic.subscribe(subscriber)
# Access: subscriber.args["field"]
```

## Troubleshooting

### Issue: Cannot import abstract_schema
**This is expected!** Use `config_manager` instead:
```python
# ❌ Don't do this
from abstract_schema import FieldSchema

# ✅ Do this instead  
from config_manager import MQTTConfigManager
config = MQTTConfigManager()
field = config.create_field(...)
```

### Issue: Need to access DataType
**This is the only exception** - import DataType from abstract_schema_data_types:
```python
from abstract_schema_data_types import DataType

config.create_field("name", DataType.STRING, "value")
```

### Issue: How do I validate a schema?
**Validation is automatic!** When you create fields through `config.create_field()` or add topics with `config.add_topic()`, validation happens automatically.

## Migration Guide

If you have old code using direct schema access:

| Old Code | New Code |
|----------|----------|
| `FieldSchema.string(...)` | `config.create_field(..., DataType.STRING, ...)` |
| `FieldSchema.integer(...)` | `config.create_field(..., DataType.INTEGER, ...)` |
| `FieldSchema.float_field(...)` | `config.create_field(..., DataType.FLOAT, ...)` |
| `FieldSchema.boolean(...)` | `config.create_field(..., DataType.BOOLEAN, ...)` |
| `MessageSchema(name, fields)` | `config.create_message_schema(fields)` |

## Examples in Tests

See `test_mqtt_schema_updated.py` for:
- Creating schemas through config manager
- Managing topics
- YAML persistence
- Error handling

See `test_real_world_examples_updated.py` for:
- Complete application examples
- Best practices
- Real-world usage patterns

## Success Checklist

- [ ] Tests use only public modules
- [ ] No direct `abstract_schema` imports (except DataType)
- [ ] All schema operations go through `config_manager`
- [ ] MQTT broker running
- [ ] All tests pass
- [ ] YAML configs generated

## Summary

This test suite demonstrates the **intended usage** of the MQTT Schema System:
- ✅ Public API through `MQTTConfigManager`
- ✅ Hidden complexity in abstract schema implementation
- ✅ Simple, clean interface for users
- ✅ Comprehensive validation and error handling

The abstract schema modules do the heavy lifting behind the scenes while users enjoy a simple, intuitive API!

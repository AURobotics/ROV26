#import logging -> needs to implemented instead of printing
from random import randint
import threading
from abc import ABC
from threading import Thread
import time
import json
from typing import Any, Dict

from paho.mqtt import client as mqtt_client
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.client import MQTTMessage

# class holding data for connection
class mqtt():
    def __init__(self, address = 'localhost', port = 1883, client_id = None, username = None, password = None):
        self.address = address
        self.port = port
        self.client_id = client_id or f'python-mqtt-{randint(0, 1000)}'
        self.username = username
        self.password = password
        self.unacked_publish = set()
        self._lock = threading.Lock()
        # Registry mapping topic string -> list of mqtt_message handlers
        self._topic_handlers: dict[str, list[mqtt_message]] = {} # for subscribed topics
        self._connect()

    def _connect(self):
        def on_connect(client, userdata, flags, rc, *args, **kwargs):
            if rc == 0:
                print("Connected to mQTT Broker")
                # re-subscribe to all registered topics on (re)connect
                for topic in self._topic_handlers:
                    client.subscribe(topic)
                    print(f'Subscribed to {topic}')
            else:
                print(f"Failed to connect, return code {rc}")

        self.client = mqtt_client.Client(CallbackAPIVersion.VERSION2, client_id=self.client_id)
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        self.client.on_connect = on_connect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
        self.client.connect(self.address, self.port)
        self.client.loop_start()

    def _on_publish(self, client, userdata, mid, *args, **kwargs):
        # paho-mqtt (mQTT v5) may pass extra parameters (reason_code, properties).
        # Accept extras defensively so the callback works across versions.
        with self._lock:
            self.unacked_publish.discard(mid)

    def _on_message(self, client, userdata, message: MQTTMessage):
        """Dispatch incoming messages to all handlers registered for the topic."""
        print(f'Received on {message.topic}: {message.payload.decode()}')
        handlers = self._topic_handlers.get(message.topic, [])
        for handler in handlers:
            try:
                handler.decode(message)
            except Exception as e:
                print(f"Error in message handler for {message.topic}: {e}")

    def register_handler(self, topic: str, handler: mqtt_message):
        """register a message handler for a topic. subscribes if not already subscribed."""
        if topic not in self._topic_handlers:
            self._topic_handlers[topic] = []
            # Only subscribe once the client is connected; on_connect will handle reconnects
            if self.client.is_connected():
                self.client.subscribe(topic)
                print(f'Subscribed to {topic}')
        self._topic_handlers[topic].append(handler)

    def reset_address(self, address):
        self.address = address
        self.client.loop_stop()
        self.client.disconnect()
        self._connect()

    def reset_port(self, port):
        self.port = port
        self.client.loop_stop()
        self.client.disconnect()
        self._connect()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


class topic():
    def __init__(self, topic: str, mqtt_connection: mqtt):
        self.topic = topic
        self.mqtt = mqtt_connection

    @property
    def topic_name(self) -> str:
        return self.topic

    @property
    def mqtt_connection(self) -> mqtt:
        return self.mqtt

    def publish(self, message: str):
        self._pub_thread = Thread(target=self._publishing, args=[self.topic, message], daemon=False)
        self._pub_thread.start()

    def _publishing(self, topic, message):
        mqtt_conn = self.mqtt

        msg = mqtt_conn.client.publish(topic, message)
        with mqtt_conn._lock:
            mqtt_conn.unacked_publish.add(msg.mid)

        # Wait until ack is received
        while True:
            with mqtt_conn._lock:
                if msg.mid not in mqtt_conn.unacked_publish:
                    break
            time.sleep(0.1)

        msg.wait_for_publish()

    def subscribe(self, message_handler: mqtt_message):
        """Register a handler for this topic via the shared mqtt connection."""
        self.mqtt.register_handler(self.topic, message_handler)

class mqtt_message(ABC):
    def __init__(self):
        self.args: Dict[str, Any] = {}

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
    
    def decode(self, message: MQTTMessage):
        """Decode MQTT payload to topic data"""
        # we assume the payload is a string representation of a dictionary because that's how we encode it
        payload = message.payload.decode()
        try:
            self.args = json.loads(payload)  # SAFE - only parses JSON
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {e}, payload: {payload}")


"""
    How does this work?
    1. We create an mqtt connection object (mqtt_connection).
    2. We create a concrete implementation of mqtt_message (e.g. sensor_data_message).
    3. We create a topic object with the topic name and the mqtt_connection.
    4. To subscribe to a topic: topic.subscribe(message_handler).
       Multiple handlers can be registered for the same topic, and multiple topics
       are all handled by a single shared on_message callback on the mqtt object.
    5. To publish: topic.publish(message_handler.encode()).
    6. The message handler's decode method is called with the received message,
       and it updates its internal state accordingly.
"""


if __name__ == "__main__":
    class sensor_data_message(mqtt_message):
        def __init__(self):
            super().__init__()
            self.add_variable("temperature", 0.0)
            self.add_variable("humidity", 0.0)
            self.add_variable("pressure", 1013.25)
            self.add_variable("timestamp", "")

        def update_values(self, temp: float, humidity: float, pressure: float):
            """Helper method to update all sensor values at once"""
            self.set_variable("temperature", temp)
            self.set_variable("humidity", humidity)
            self.set_variable("pressure", pressure)
            self.set_variable("timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))

        def __str__(self):
            return f"SensorData: temp={self.args['temperature']}°C, humidity={self.args['humidity']}%, pressure={self.args['pressure']}hPa"


    class device_status_message(mqtt_message):
        def __init__(self):
            super().__init__()
            self.add_variable("device_id", "")
            self.add_variable("status", "offline")
            self.add_variable("battery_level", 0)
            self.add_variable("uptime_seconds", 0)

        def __str__(self):
            return f"Device {self.args['device_id']}: {self.args['status']}, battery={self.args['battery_level']}%, uptime={self.args['uptime_seconds']}s"

    # Test 1: Basic publish/subscribe with sensor data
    print("=" * 50)
    print("Test 1: Sensor Data Publishing")
    print("=" * 50)

    mqtt_connection = mqtt(address='localhost', port=1883)

    sensor_topic = topic("home/livingroom/sensor", mqtt_connection)
    device_topic = topic("home/devices/status", mqtt_connection)

    sensor_handler = sensor_data_message()
    device_handler = device_status_message()

    print("\nSubscribing to topics...")
    sensor_topic.subscribe(sensor_handler)
    device_topic.subscribe(device_handler)

    time.sleep(2)

    print("\nPublishing sensor data...")

    publisher_sensor = sensor_data_message()
    publisher_device = device_status_message()

    for i in range(3):
        publisher_sensor.update_values(
            temp=22.5 + i*0.5,
            humidity=45.0 + i*2,
            pressure=1012.0 - i*0.5
        )

        print(f"\nPublishing sensor reading {i+1}:")
        print(f"  Data: {publisher_sensor}")
        sensor_topic.publish(publisher_sensor.encode())

        publisher_device.set_variable("device_id", "sensor_001")
        publisher_device.set_variable("status", "online" if i % 2 == 0 else "sleeping")
        publisher_device.set_variable("battery_level", 95 - i*5)
        publisher_device.set_variable("uptime_seconds", 3600 + i*600)

        device_topic.publish(publisher_device.encode())

        time.sleep(1)

        print(f"  Subscriber received sensor: {sensor_handler}")
        print(f"  Subscriber received device: {device_handler}")

    # Test 2: Error handling
    print("\n" + "=" * 50)
    print("Test 2: Error Handling")
    print("=" * 50)

    try:
        sensor_handler.set_variable("nonexistent_var", 123)
    except KeyError as e:
        print(f"Caught expected error: {e}")

    # Test 3: Direct dictionary manipulation
    print("\n" + "=" * 50)
    print("Test 3: Direct Dictionary Access")
    print("=" * 50)

    simple_message = sensor_data_message()
    simple_message.args["custom_field"] = "custom_value"

    print(f"Message with custom field: {simple_message.args}")
    encoded = simple_message.encode()
    print(f"Encoded: {encoded}")

    # Test 4: Multiple subscribers on the same topic (now works correctly)
    print("\n" + "=" * 50)
    print("Test 4: Multiple Subscribers")
    print("=" * 50)

    sensor_handler2 = sensor_data_message()
    # Subscribe a second handler to the same topic via the same topic object
    sensor_topic.subscribe(sensor_handler2)

    time.sleep(1)

    publisher_sensor.update_values(temp=25.0, humidity=50.0, pressure=1010.0)
    sensor_topic.publish(publisher_sensor.encode())

    time.sleep(1)

    print(f"Subscriber 1 received: {sensor_handler}")
    print(f"Subscriber 2 received: {sensor_handler2}")

    print("\n" + "=" * 50)
    print("Test Complete - Waiting for additional messages...")
    print("Press Ctrl+C to exit")
    print("=" * 50)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting test...")
        mqtt_connection.disconnect()

    ##############################################################################

    # testing esp
    # class sensor_data_message(mqtt_message):
    #     def __init__(self):
    #         super().__init__()
    #         # Initialize default values
    #         self.add_variable("temperature", 0.0)
    #         self.add_variable("humidity", 0.0)
            
    #     def update_values(self, temp: float, humidity: float):
    #         """Helper method to update all sensor values at once"""
    #         self.set_variable("temperature", temp)
    #         self.set_variable("humidity", humidity)
            
    #     def __str__(self):
    #         return f"SensorData: temp={self.args['temperature']}°C, humidity={self.args['humidity']}%"

    # class DeviceLed(mqtt_message):
    #     def __init__(self):
    #         super().__init__()
    #         self.message = "OFF"

    #     def set_variable(self, name: str, value):
    #         self.message = str(value)

    #     def encode(self):
    #         return self.message
            
    #     def decode(self, payload:str):
    #         self.message = payload

    #     def __str__(self):
    #         return f"esp led: {self.message}"

    # # Create mQTT connection
    # mqtt_connection = mqtt(address='localhost', port=1883)

    # # Create topics
    # # mqtt_connection.pub.publish("from/esp", "", retain=True)
    # sensor_topic = topic("from/esp", mqtt_connection)
    # to_esp = topic("to/esp", mqtt_connection)

    # # Create message handlers
    # sensor_handler = sensor_data_message()
    # to_esp_handler = DeviceLed()
    # to_esp_test_handler = DeviceLed()

    # # Subscribe to topics
    # print("\nSubscribing to topics...")
    # sensor_topic.subscribe(sensor_handler)
    # # to_esp.subscribe(to_esp_test_handler)
    # # Give time for subscriptions to establish
    # time.sleep(1)

    # # Test publishing sensor data
    # print("\nPublishing sensor data...")

    
    # try:
    #     while True:
    #         print("publishing OFF")
    #         to_esp_handler.set_variable("", "OFF")
    #         to_esp.publish(to_esp_handler.encode())
    #         time.sleep(1)
    #         print("publishing ON")
    #         to_esp_handler.set_variable("", "ON")
    #         to_esp.publish(to_esp_handler.encode())
    #         sensor_handler.update_values(temp=randint(20, 30), humidity=randint(40, 60))
    #         to_esp.publish(sensor_handler.encode())
    #         print(f"from sensor: {sensor_handler}")
    #         time.sleep(1)
    # except KeyboardInterrupt:
    #     print("\nExiting test...")

import logging
import threading
from .base_types import MqttMessage


from threading import Thread
import time
import typing

from paho.mqtt.client import Client as pahoMC # paho_mqtt_client
from paho.mqtt.enums import CallbackAPIVersion


# class holding data for connection
class Mqtt():
    def __init__(self, address = 'localhost', port = 1883):
        self.address = address
        self.port = port
        self.unacked_publish = set()
        self._lock = threading.Lock()
        self._pubSetup()

    def _pubSetup(self):
        self.pub = pahoMC(CallbackAPIVersion.VERSION2)
        self.pub.user_data_set(self.unacked_publish)
        self.pub.on_publish = self._on_publish
        self.pub.connect(self.address, self.port)
        self.pub.loop_start()

    def _on_publish(self, client, userdata, mid, *args, **kwargs):
        # paho-mqtt (MQTT v5) may pass extra parameters (reason_code, properties).
        # Accept extras defensively so the callback works across versions.
        with self._lock:
            try:
                if userdata is not None:
                    userdata.discard(mid)
            except Exception as e:
                logging.error(f"Error in on_publish callback: {e}")

    def reset_address(self, address):
        self.address = address
        self.pub.disconnect()
        self._pubSetup()

    def reset_port(self, port):
        self.port = port
        self.pub.disconnect()
        self._pubSetup()

    def cleanup(self):
        """Clean up MQTT resources"""
        self.pub.loop_stop()
        self.pub.disconnect()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    

class Topic():
    def __init__(self, topic: str, mqtt_connection:Mqtt):
        self.topic = topic
        self.mqtt = mqtt_connection

    @property
    def get_topic(self) -> str:
        return self.topic
    
    @property
    def get_mqtt_connection(self) -> Mqtt:
        return self.mqtt

    def publish(self, message:str):
        self._pub_thread = Thread(target=self._publishing, args=[self.topic, message], daemon=True)
        self._pub_thread.start()
        
    def _publishing(self, topic, message):    
        mqtt_client = self.mqtt
        
        msg = mqtt_client.pub.publish(topic, message)
        if mqtt_client.unacked_publish is not None:
            mqtt_client.unacked_publish.add(msg.mid)
        while len(mqtt_client.unacked_publish):
            time.sleep(0.1)
        msg.wait_for_publish()

    def subscribe(self, message_handler:MqttMessage):
        self.sub_client = pahoMC(CallbackAPIVersion.VERSION2)
        self.message_handler = message_handler # holds the variables that change with publishing (I am depending on the reference here)
        self.sub_client.on_connect = self._sub_on_connect # callback for connection
        self.sub_client.on_message = self._sub_on_message # callback for message received
        self.sub_client.connect(self.mqtt.address, self.mqtt.port)
        self.sub_client.loop_start()

    def _sub_on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f'Failed to connect: {reason_code}')  
        else: # if connection is successful then subscribe to topic
            client.subscribe(self.topic)
            print(f'Subscribed to {self.topic}') # debug print

    def _sub_on_message(self, client, userdata, message):
        payload_str: str = message.payload.decode()
        print(f'A subscriber, received on {message.topic}: {payload_str}') # debug print
        self.message_handler.decode(payload_str) # change the variables in message_handler

"""
    How does this work?
    1. We create an Mqtt connection object (mqtt_connection).
    2. We create a concrete implementation of MqttMessage (TestMessageHandler)
    3. We create a Topic object with the topic name and the mqtt_connection.
    4. to subscribe to a topic: with our message handler (topic.subscribe(message_handler)).
    5. to publish messages to a topic: using encode method (after putting your values in the message handler) in TestMessageHandler (topic.publish(message_handler.encode())).
    6. The message handler's decode method is called with the received message, and it updates its internal state (received_data and message_count) accordingly.

    summarizing MqttMessage:
    - MqttMessage is an abstract base class that defines the structure for MQTT messages.
    - It has a class method "encode" -> use that to encode messages before publishing.
    - It has an abstract method decode -> this is how message will be decoded when received
"""


if __name__ == "__main__":
    # class SensorDataMessage(MqttMessage):
    #     def __init__(self):
    #         super().__init__()
    #         # Initialize default values
    #         self.add_variable("temperature", 0.0)
    #         self.add_variable("humidity", 0.0)
    #         self.add_variable("pressure", 1013.25)
    #         self.add_variable("timestamp", "")
            
    #     def update_values(self, temp: float, humidity: float, pressure: float):
    #         """Helper method to update all sensor values at once"""
    #         self.set_variable("temperature", temp)
    #         self.set_variable("humidity", humidity)
    #         self.set_variable("pressure", pressure)
    #         self.set_variable("timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))
            
    #     def __str__(self):
    #         return f"SensorData: temp={self.args['temperature']}°C, humidity={self.args['humidity']}%, pressure={self.args['pressure']}hPa"


    # # 2. Another message type for testing different data
    # class DeviceStatusMessage(MqttMessage):
    #     def __init__(self):
    #         super().__init__()
    #         self.add_variable("device_id", "")
    #         self.add_variable("status", "offline")
    #         self.add_variable("battery_level", 0)
    #         self.add_variable("uptime_seconds", 0)
            
    #     def __str__(self):
    #         return f"Device {self.args['device_id']}: {self.args['status']}, battery={self.args['battery_level']}%, uptime={self.args['uptime_seconds']}s"

    # # Test 1: Basic publish/subscribe with sensor data
    # print("=" * 50)
    # print("Test 1: Sensor Data Publishing")
    # print("=" * 50)

    # # Create MQTT connection
    # mqtt_connection = Mqtt(address='broker.emqx.io', port=1883)

    # # Create topics
    # sensor_topic = Topic("home/livingroom/sensor", mqtt_connection)
    # device_topic = Topic("home/devices/status", mqtt_connection)

    # # Create message handlers
    # sensor_handler = SensorDataMessage()
    # device_handler = DeviceStatusMessage()

    # # Subscribe to topics
    # print("\nSubscribing to topics...")
    # sensor_topic.subscribe(sensor_handler)
    # device_topic.subscribe(device_handler)

    # # Give time for subscriptions to establish
    # time.sleep(2)

    # # Test publishing sensor data
    # print("\nPublishing sensor data...")

    # # Create a publisher message handler
    # publisher_sensor = SensorDataMessage()
    # publisher_device = DeviceStatusMessage()

    # # Publish some sensor readings
    # for i in range(3):
    #     # Update sensor values
    #     publisher_sensor.update_values(
    #         temp=22.5 + i*0.5,
    #         humidity=45.0 + i*2,
    #         pressure=1012.0 - i*0.5
    #     )
        
    #     # Publish
    #     print(f"\nPublishing sensor reading {i+1}:")
    #     print(f"  Data: {publisher_sensor}")
    #     sensor_topic.publish(publisher_sensor.encode())
        
    #     # Update device status
    #     publisher_device.set_variable("device_id", "sensor_001")
    #     publisher_device.set_variable("status", "online" if i % 2 == 0 else "sleeping")
    #     publisher_device.set_variable("battery_level", 95 - i*5)
    #     publisher_device.set_variable("uptime_seconds", 3600 + i*600)
        
    #     # Publish device status
    #     device_topic.publish(publisher_device.encode())
        
    #     # Wait a bit to see if subscription receives the message
    #     time.sleep(1)
        
    #     # Check what the subscriber received
    #     print(f"  Subscriber received sensor: {sensor_handler}")
    #     print(f"  Subscriber received device: {device_handler}")

    # # Test 2: Error handling - trying to set non-existent variable
    # print("\n" + "=" * 50)
    # print("Test 2: Error Handling")
    # print("=" * 50)

    # try:
    #     sensor_handler.set_variable("nonexistent_var", 123)
    # except KeyError as e:
    #     print(f"Caught expected error: {e}")

    # # Test 3: Direct dictionary manipulation
    # print("\n" + "=" * 50)
    # print("Test 3: Direct Dictionary Access")
    # print("=" * 50)

    # # Create a simple message
    # simple_message = SensorDataMessage()
    # simple_message.args["custom_field"] = "custom_value"  # Direct access

    # print(f"Message with custom field: {simple_message.args}")
    # encoded = simple_message.encode()
    # print(f"Encoded: {encoded}")

    # # Decode it back
    # simple_message.decode(encoded)
    # print(f"Decoded: {simple_message.args}")

    # # Test 4: Multiple subscribers
    # print("\n" + "=" * 50)
    # print("Test 4: Multiple Subscribers")
    # print("=" * 50)

    # # Create another subscriber for the same topic
    # sensor_handler2 = SensorDataMessage()
    # sensor_topic2 = Topic("home/livingroom/sensor", mqtt_connection)
    # sensor_topic2.subscribe(sensor_handler2)

    # time.sleep(1)

    # # Publish one more message
    # publisher_sensor.update_values(temp=25.0, humidity=50.0, pressure=1010.0)
    # sensor_topic.publish(publisher_sensor.encode())

    # time.sleep(1)

    # print(f"Subscriber 1 received: {sensor_handler}")
    # print(f"Subscriber 2 received: {sensor_handler2}")

    # # Keep the program running to receive messages
    # print("\n" + "=" * 50)
    # print("Test Complete - Waiting for additional messages...")
    # print("Press Ctrl+C to exit")
    # print("=" * 50)

    # try:
    #     while True:
    #         time.sleep(1)
    # except KeyboardInterrupt:
    #     print("\nExiting test...")

    # testing esp

    class SensorDataMessage(MqttMessage):
        def __init__(self):
            super().__init__()
            # Initialize default values
            self.add_variable("temperature", 0.0)
            self.add_variable("humidity", 0.0)
            
        def update_values(self, temp: float, humidity: float):
            """Helper method to update all sensor values at once"""
            self.set_variable("temperature", temp)
            self.set_variable("humidity", humidity)
            
        def __str__(self):
            return f"SensorData: temp={self.args['temperature']}°C, humidity={self.args['humidity']}%"

    class DeviceLed(MqttMessage):
        def __init__(self):
            super().__init__()
            self.message = "OFF"

        def set_variable(self, name: str, value):
            self.message = str(value)

        def encode(self):
            return self.message
            
        def decode(self, payload:str):
            self.message = payload

        def __str__(self):
            return f"esp led: {self.message}"

    # Create MQTT connection
    mqtt_connection = Mqtt(address='localhost', port=1883)

    # Create topics
    # mqtt_connection.pub.publish("from/esp", "", retain=True)
    sensor_topic = Topic("from/esp", mqtt_connection)
    to_esp = Topic("to/esp", mqtt_connection)

    # Create message handlers
    sensor_handler = SensorDataMessage()
    to_esp_handler = DeviceLed()
    to_esp_test_handler = DeviceLed()

    # Subscribe to topics
    print("\nSubscribing to topics...")
    sensor_topic.subscribe(sensor_handler)
    # to_esp.subscribe(to_esp_test_handler)
    # Give time for subscriptions to establish
    time.sleep(1)

    # Test publishing sensor data
    print("\nPublishing sensor data...")

    
    try:
        while True:
            print("publishing OFF")
            to_esp_handler.set_variable("", "OFF")
            to_esp.publish(to_esp_handler.encode())
            time.sleep(1)
            print("publishing ON")
            to_esp_handler.set_variable("", "ON")
            to_esp.publish(to_esp_handler.encode())
            print(f"from sensor: {sensor_handler}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting test...")

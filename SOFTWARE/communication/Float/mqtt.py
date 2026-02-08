from abc import ABC, abstractmethod

from threading import Thread
import time

from paho.mqtt.client import Client as pahoMC # paho_mqtt_client
from paho.mqtt.enums import CallbackAPIVersion


# class holding data for connection
class Mqtt():
    def __init__(self, address = 'localhost', port = 1883):
        self.address = address
        self.port = port
        self._pubSetup()
        print("Mqtt initialised")

    def _pubSetup(self):
        self.unacked_publish = set()
        self.pub = pahoMC(CallbackAPIVersion.VERSION2)
        self.pub.user_data_set(self.unacked_publish)
        self.pub.on_publish = self._on_publish
        self.pub.connect(self.address, self.port)
        self.pub.loop_start()

    def _on_publish(self, client, userdata, mid, *args, **kwargs):
        # paho-mqtt (MQTT v5) may pass extra parameters (reason_code, properties).
        # Accept extras defensively so the callback works across versions.
        try:
            if userdata is not None:
                userdata.discard(mid)
        except Exception:
            pass

class MqttMessage(ABC):
    @classmethod
    def encode(cls, *args) -> str:
        if len(args) == 1:
            message = str(args[0])
        elif len(args) > 1:
            message = ",".join(str(arg) for arg in args)
        else:
            message = ""
        
        return message

    @abstractmethod
    def decode(self, data:list):
        pass
    

class Topic():
    def __init__(self, topic, mqtt_connection:Mqtt):
        self.topic = topic
        self.mqtt = mqtt_connection

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
            print(f'Failed to connect to {self.topic}.') 
        else: # if connection is successful then subscribe to topic
            client.subscribe(self.topic)
            print(f'Subscribed to {self.topic}') # debug print

    def _sub_on_message(self, client, userdata, message):
        payload_str: str = message.payload.decode()
        print(f'Received on {message.topic}: {payload_str}') # debug print
        self.message_handler.decode(payload_str.split(',')) # change the variables in message_handler

"""
    How does this work?
    1. We create an Mqtt connection object (mqtt_connection).
    2. We create a concrete implementation of MqttMessage (TestMessageHandler)
    3. We create a Topic object with the topic name and the mqtt_connection.
    4. We subscribe to the topic with our message handler (topic.subscribe(message_handler)).
    5. We publish messages to the topic using encode method in TestMessageHandler (topic.publish(TestMessageHandler.encode(...))).
    6. The message handler's decode method is called with the received message, and it updates its internal state (received_data and message_count) accordingly.

    summarizing MqttMessage:
    - MqttMessage is an abstract base class that defines the structure for MQTT messages.
    - It has a class method "encode" -> use that to encode messages before publishing.
    - It has an abstract method decode -> this is how message will be decoded when received
"""


if __name__ == "__main__":
    # Create MQTT connection
    mqtt_connection = Mqtt()
    
    # Create a concrete implementation of MqttMessage for testing
    class TestMessageHandler(MqttMessage):
        def __init__(self):
            self.received_data = []
            self.message_count = 0
            
        def decode(self, data: list):
            # Store the received data
            self.received_data.append(data)
            self.message_count += 1
            print(f"Message handler received data #{self.message_count}: {data}")
    
    # Create a test message handler
    message_handler = TestMessageHandler()
    
    # Create a Topic object for publishing/subscribing
    topic = Topic('test/topic', mqtt_connection)
    
    # Subscribe to the topic with our message handler
    topic.subscribe(message_handler)
    
    # Wait for connection to establish
    time.sleep(1)
    
    print("Starting MQTT test...")
    
    # Test 1: Publish a simple string message
    print("\nTest 1: Publishing single string message")
    topic.publish(TestMessageHandler.encode("Hello, MQTT!"))
    time.sleep(1)
    
    # Test 2: Publish multiple arguments (will be joined with commas)
    print("\nTest 2: Publishing multiple arguments")
    topic.publish(TestMessageHandler.encode('arg1', 42, 3.14, 'last_arg'))
    time.sleep(1)
    
    # Test 3: Publish multiple messages in a loop
    print("\nTest 3: Publishing multiple messages in loop")
    for i in range(3):
        topic.publish(TestMessageHandler.encode(f'Message #{i}', f'Value_{i*10}', i*100))
        time.sleep(0.5)
    
    # Wait for all messages to be received
    time.sleep(2)
    
    # Print summary
    print(f"\n=== Test Summary ===")
    print(f"Total messages received by handler: {message_handler.message_count}")
    print(f"All received data: {message_handler.received_data}")
    
    # Test that message handler data was properly updated
    if message_handler.message_count > 0:
        print("\n✓ Test PASSED: Messages were received and processed")
    else:
        print("\n✗ Test FAILED: No messages were received")
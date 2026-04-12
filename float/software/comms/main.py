from time import sleep
from comms.mqtt import mqtt, topic, mqtt_message
from comms.file_receiver import file_receiver

MAIN_TOPIC_NAME = "float/data"
SECONDARY_TOPIC_NAME = "float/status"

def main():
    mqtt_client = mqtt("localhost", 1883)

    class status_handler(mqtt_message):
        def __init__(self):
            super().__init__()
            self.status_received = False
            self.status = None

        def decode(self, message):
            self.status = message.payload.decode()
            print(f"Received status message: {self.status}")
            self.status_received = True
            
    float_status_topic = topic(SECONDARY_TOPIC_NAME, mqtt_client)
    float_status_hander = status_handler()
    float_status_topic.subscribe(float_status_hander)
    
    file_receiver_instance = file_receiver(mqtt_client, f"{MAIN_TOPIC_NAME}", crc32=False)

    while not file_receiver_instance.is_complete:
        print("Polling...")
        sleep(5)

def simple_test():
    """A simple test to verify the file receiver works without CRC32 and with small files that fit in one chunk"""
    mqtt_client = mqtt("localhost", 1883)
    
    class test_handler(mqtt_message):
        def decode(self, message):
            print(f"Received message on topic {message.topic}: {message.payload.decode()}")

    handler = test_handler()
    test_topic = topic("test", mqtt_client)

    test_topic.subscribe(handler)

    while True:
        sleep(1)
from time import sleep
from .mqtt import mqtt, topic, mqtt_message
from .file_receiver import file_receiver

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

    class float_comapny_number_handler(mqtt_message):
        def __init__(self):
            super().__init__()
            self.company_number = None
        
        def decode(self, message):
            self.company_number = message.payload.decode()
            print(f"Received company number: {self.company_number}")
            
    float_status_topic = topic(SECONDARY_TOPIC_NAME, mqtt_client)
    float_status_hander = status_handler()
    float_status_topic.subscribe(float_status_hander)
    
    float_company_number_topic = topic(MAIN_TOPIC_NAME + "/credential", mqtt_client)
    float_company_number_handler = float_comapny_number_handler()
    float_company_number_topic.subscribe(float_company_number_handler)

    file_receiver_instance = file_receiver(mqtt_client, f"{MAIN_TOPIC_NAME}", crc32=False)

    while not file_receiver_instance.is_complete:
        print("Polling...")
        sleep(5)

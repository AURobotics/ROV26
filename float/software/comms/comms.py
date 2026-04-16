from time import sleep
from .mqtt import mqtt, topic, mqtt_message
from .file_receiver import file_receiver

MAIN_TOPIC_NAME = "float/data"
SECONDARY_TOPIC_NAME = "float/status"

class StatusHandler(mqtt_message):
        def __init__(self):
            super().__init__()
            self.status_received = False
            self.status = None

        def decode(self, message):
            self.status = message.payload.decode()
            print(f"Received status message: {self.status}")
            self.status_received = True

class FloatCompanyNumberHandler(mqtt_message):
    def __init__(self):
        super().__init__()
        self.company_number = None
    
    def decode(self, message):
        self.company_number = message.payload.decode()
        print(f"Received company number: {self.company_number}")

class Comms:
    def __init__(self):
        self.mqtt_client = mqtt("localhost", 1883)

        self.float_status_topic = topic(SECONDARY_TOPIC_NAME, self.mqtt_client)
        self.float_status_hander = StatusHandler()
        self.float_status_topic.subscribe(self.float_status_hander)

        self.float_company_number_topic = topic(MAIN_TOPIC_NAME + "/credential", self.mqtt_client)
        self.float_company_number_handler = FloatCompanyNumberHandler()
        self.float_company_number_topic.subscribe(self.float_company_number_handler)

        self.file_receiver_instance = file_receiver(self.mqtt_client, f"{MAIN_TOPIC_NAME}", crc32=False)

    def end_comms(self):
        topic("float/end", self.mqtt_client).publish("shutdown")
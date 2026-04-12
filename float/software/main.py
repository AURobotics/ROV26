# main for float

# from comms.main import main, simple_test

# main()

# simple_test()

# from gui.main import run_gui
# run_gui()

import sys
from time import sleep

from PyQt6.QtWidgets import QApplication

from comms.file_receiver import file_receiver
from comms.main import MAIN_TOPIC_NAME, SECONDARY_TOPIC_NAME
from comms.mqtt import topic, mqtt, mqtt_message
from gui.main_window import DemoWindow
from gui.float_tab import DataViewerTab

app = QApplication(sys.argv)
app.setStyle("Fusion")

float_tab = DataViewerTab()

win = DemoWindow(float_tab)
win.show()

mqtt_client = mqtt("localhost", 1883)

class status_handler(mqtt_message):
    def __init__(self):
        super().__init__()
        self.status_received = False
        self.status = None

    def decode(self, message):
        self.status = message.payload.decode()
        float_tab.post_message(f"Received status message: {self.status}")
        self.status_received = True

class company_number_handler(mqtt_message):
    def __init__(self):
        super().__init__()
        self.company_number = None
    
    def decode(self, message):
        self.company_number = message.payload.decode()
        float_tab.post_message(f"Received company number: {self.company_number}")
        
float_status_topic = topic(SECONDARY_TOPIC_NAME, mqtt_client)
float_status_hander = status_handler()
float_status_topic.subscribe(float_status_hander)

float_company_number_topic = topic(f"float/data/credential", mqtt_client)
float_company_number_handler = company_number_handler()
float_company_number_topic.subscribe(float_company_number_handler)

file_receiver_instance = file_receiver(mqtt_client, f"{MAIN_TOPIC_NAME}", crc32=False)

while not file_receiver_instance.is_complete:
    print("Polling...")
    sleep(5)

float_tab.post_message("File transfer complete! Decoding CSV data...", "SUCCESS")
float_tab.load_csv("log.csv")

sys.exit(app.exec())
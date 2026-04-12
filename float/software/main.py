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

# use QTimer for non-blocking polling
from PyQt6.QtCore import QMetaObject, QTimer, Qt

app = QApplication(sys.argv)
app.setStyle("Fusion")

float_tab = DataViewerTab()

win = DemoWindow(float_tab)
win.show()

def post(text: str, level: str = "INFO"):
    """
    Safe to call from ANY thread.
    Routes onto the Qt main-thread event loop via QTimer.singleShot(0).
    Arguments are captured by value with the default-arg trick so the lambda
    always sees the right values even if called later.
    """
    QTimer.singleShot(0, lambda t=text, l=level: float_tab.post_message(t, l))


mqtt_client = mqtt("localhost", 1883)

class status_handler(mqtt_message):
    def __init__(self):
        super().__init__()
        self.status_received = False
        self.status = None

    def decode(self, message):
        self.status = message.payload.decode()
        self.status_received = True

class company_number_handler(mqtt_message):
    def __init__(self):
        super().__init__()
        self.company_number = None
        self.company_number_received = False
    
    def decode(self, message):
        self.company_number = message.payload.decode()
        self.company_number_received = True

float_status_topic = topic(SECONDARY_TOPIC_NAME, mqtt_client)
float_status_handler = status_handler()
float_status_topic.subscribe(float_status_handler)

float_company_number_topic = topic("float/data/credential", mqtt_client)
float_company_number_handler = company_number_handler()
float_company_number_topic.subscribe(float_company_number_handler)

file_receiver_instance = file_receiver(mqtt_client, MAIN_TOPIC_NAME, crc32=False)
 
_file_poll_timer = QTimer()   # keep a reference so it isn't GC'd
_status_poll_timer = QTimer()

def _check_status():
    try:
        if float_status_handler.status_received:
            _status_poll_timer.stop()
            post(f"Float status: {float_status_handler.status}", "OK")
        else:
            print("Polling for float status…")
    except Exception as exc:
        print(f"[_check_status] error: {exc}", file=sys.stderr)
        _status_poll_timer.stop()

_status_poll_timer.timeout.connect(_check_status)
_status_poll_timer.start(3000)   # every 3 s

def _check_file_complete():
    try:
        if file_receiver_instance.is_complete:
            _file_poll_timer.stop()
            if not float_company_number_handler.company_number_received:
                post("File received, but no company number received from float.", "WARN")
            post(f"Received company number: {float_company_number_handler.company_number}", "OK")
            post("CSV file received", "OK")
            float_tab.load_csv("log.csv")
        else:
            print("Polling for file completion…")
    except Exception as exc:
        print(f"[_check_file_complete] error: {exc}", file=sys.stderr)
        _file_poll_timer.stop()
 
_file_poll_timer.timeout.connect(_check_file_complete)
_file_poll_timer.start(5000)   # every 5 s

exit_code = app.exec()
sys.exit(exit_code)
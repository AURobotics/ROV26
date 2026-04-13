# main.py
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

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

# Create a signal proxy/bridge that lives in the main thread
class MQTTSignalBridge(QObject):
    """Bridge to safely emit signals from MQTT callbacks to Qt main thread."""
    status_signal = pyqtSignal(str)
    company_number_signal = pyqtSignal(str)
    file_complete_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()

# Create bridge in main thread BEFORE MQTT handlers
bridge = MQTTSignalBridge()

# Connect bridge signals to float_tab slots
bridge.status_signal.connect(lambda msg: float_tab.post_message(msg, "OK"))
bridge.company_number_signal.connect(lambda msg: float_tab.post_message(msg, "OK"))
bridge.file_complete_signal.connect(lambda: float_tab.post_message("CSV file received", "OK"))
bridge.file_complete_signal.connect(lambda: float_tab.load_csv("log.csv"))

# MQTT handlers
class StatusHandler(mqtt_message):
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
    
    def decode(self, message):
        status = message.payload.decode()
        # Emit signal through bridge - Qt handles thread safety automatically
        self.bridge.status_signal.emit(f"Float status: {status}")

class CompanyNumberHandler(mqtt_message):
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
    
    def decode(self, message):
        company_number = message.payload.decode()
        self.bridge.company_number_signal.emit(f"Received company number: {company_number}")

# Create handlers with bridge reference
status_handler = StatusHandler(bridge)
company_handler = CompanyNumberHandler(bridge)

# Subscribe to topics
float_status_topic = topic(SECONDARY_TOPIC_NAME, mqtt_client)
float_status_topic.subscribe(status_handler)

float_company_number_topic = topic("float/data/credential", mqtt_client)
float_company_number_topic.subscribe(company_handler)

file_receiver_instance = file_receiver(mqtt_client, MAIN_TOPIC_NAME, crc32=False)

# File polling timer (runs in main thread)
_file_poll_timer = QTimer()

def _check_file_complete():
    if file_receiver_instance.is_complete:
        _file_poll_timer.stop()
        bridge.file_complete_signal.emit()

_file_poll_timer.timeout.connect(_check_file_complete)
_file_poll_timer.start(5000)

exit_code = app.exec()
sys.exit(exit_code)
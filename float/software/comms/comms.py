from time import sleep

from comms.float_messages import CompanyNumberHandler, MQTTSignalBridge, StatusHandler
from .mqtt import mqtt, topic, mqtt_message
from .file_receiver import file_receiver
from PySide6.QtCore import QTimer

MAIN_TOPIC_NAME = "float/data"
SECONDARY_TOPIC_NAME = "float/status"

class Comms:
    def __init__(self):
        self._mqtt_client = mqtt("localhost", 1883)
        self.end_topic = topic("float/end", self._mqtt_client)
        
    def float_communication_setup(self, float_window):
        # Create bridge in main thread BEFORE MQTT handlers
        bridge = MQTTSignalBridge()

        # Connect bridge signals to float_window slots
        bridge.status_signal.connect(lambda msg: float_window.post_message(msg, "OK"))
        bridge.company_number_signal.connect(lambda msg: float_window.post_message(msg, "OK"))
        bridge.file_complete_signal.connect(lambda: float_window.post_message("CSV file received", "OK"))
        bridge.file_complete_signal.connect(lambda: float_window.load_csv("log.csv"))

        # Create handlers with bridge reference
        status_handler = StatusHandler(bridge)
        company_handler = CompanyNumberHandler(bridge)

        # Subscribe to topics
        float_status_topic = topic(SECONDARY_TOPIC_NAME, self._mqtt_client)
        float_status_topic.subscribe(status_handler)

        float_company_number_topic = topic("float/data/credential", self._mqtt_client)
        float_company_number_topic.subscribe(company_handler)

        file_receiver_instance = file_receiver(self._mqtt_client, MAIN_TOPIC_NAME, crc32=False)

        # File polling timer (runs in main thread)
        _file_poll_timer = QTimer()
        _status_poll_timer = QTimer()
        _cono_poll_timer = QTimer()

        def _check_handeler_message_receive(handeler, topic:topic, timer):
            if handeler.received:
                timer.stop()
                topic.unsubscribe(handeler)

        def _check_status_handeler():
            _check_handeler_message_receive(status_handler, float_status_topic, _status_poll_timer)
        def _check_cono_handeler():
            _check_handeler_message_receive(company_handler, float_company_number_topic, _cono_poll_timer)

        def _check_file_complete():
            if file_receiver_instance.is_complete:
                _file_poll_timer.stop()
                bridge.file_complete_signal.emit()

        # stops timer when file is received
        _file_poll_timer.timeout.connect(_check_file_complete)
        _file_poll_timer.start(5000)

        # unsubscribes to topics with received messages
        _status_poll_timer.timeout.connect(_check_status_handeler) 
        _status_poll_timer.start(5000)
        _cono_poll_timer.timeout.connect(_check_cono_handeler)
        _cono_poll_timer.start(5000)

    def end_comms(self):
        self.end_topic.publish("shutdown")
        print("sending to shutdown")
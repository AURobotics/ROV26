from time import sleep

from comms.float_messages import CompanyNumberHandler, DepthHandeler, MQTTSignalBridge, StatusHandler
from .mqtt import MQTTClient, Topic
from .file_receiver import file_receiver
from PySide6.QtCore import QTimer

MAIN_TOPIC_NAME = "float/data"
SECONDARY_TOPIC_NAME = "float/status"

class Comms:
    def __init__(self):
        self._mqtt_client = MQTTClient("localhost", 1883)
        self.end_Topic = Topic("float/end", self._mqtt_client)
        # self._debug_get_depth(self._mqtt_client)
        
    def float_communication_setup(self, float_window):
        # Create bridge in main thread BEFORE MQTTClient handlers
        bridge = MQTTSignalBridge()

        # Connect bridge signals to float_window slots
        bridge.status_signal.connect(lambda msg: float_window.post_message(msg, "OK"))
        bridge.company_number_signal.connect(lambda msg: float_window.post_message(msg, "OK"))
        bridge.file_complete_signal.connect(lambda: float_window.post_message("CSV file received", "OK"))
        bridge.file_complete_signal.connect(lambda: float_window.load_csv("log.csv"))

        # Create handlers with bridge reference
        status_handler = StatusHandler(bridge)
        company_handler = CompanyNumberHandler(bridge)

        # Subscribe to Topics
        float_status_Topic = Topic(SECONDARY_TOPIC_NAME, self._mqtt_client)
        float_status_Topic.subscribe(status_handler)

        float_company_number_Topic = Topic("float/data/credential", self._mqtt_client)
        float_company_number_Topic.subscribe(company_handler)

        file_receiver_instance = file_receiver(self._mqtt_client, MAIN_TOPIC_NAME, crc32=False)
        
        # File polling timer (runs in main thread)
        _file_poll_timer = QTimer()
        _status_poll_timer = QTimer()
        _cono_poll_timer = QTimer()

        def _check_handeler_message_receive(handeler, Topic:Topic, timer):
            if handeler.received:
                timer.stop()
                Topic.unsubscribe(handeler)

        def _check_status_handeler():
            _check_handeler_message_receive(status_handler, float_status_Topic, _status_poll_timer)
        def _check_cono_handeler():
            _check_handeler_message_receive(company_handler, float_company_number_Topic, _cono_poll_timer)

        def _check_file_complete():
            if file_receiver_instance.is_complete:
                _file_poll_timer.stop()
                bridge.file_complete_signal.emit()

        # stops timer when file is received
        _file_poll_timer.timeout.connect(_check_file_complete)
        _file_poll_timer.start(5000)

        # unsubscribes to Topics with received messages
        _status_poll_timer.timeout.connect(_check_status_handeler) 
        _status_poll_timer.start(5000)
        _cono_poll_timer.timeout.connect(_check_cono_handeler)
        _cono_poll_timer.start(5000)

    def _debug_get_depth(self, mqtt):
        self.depth_topic = Topic("float/depth", mqtt)
        self.depth_handeler = DepthHandeler()

    def end_comms(self):
        self.end_Topic.publish("shutdown")
        print("sending to shutdown")
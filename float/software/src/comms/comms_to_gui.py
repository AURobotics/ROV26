from time import sleep

from comms.float_messages import MessageLevel, MQTTSignalBridge, TerminalPrintHandler, GUIPrintHandler
from .mqtt import MQTTClient, Topic
from .file_receiver import file_receiver
from PySide6.QtCore import QTimer, Signal

DATA = "float/data"
STATUS = "float/status"
CREDENTIAL = "float/data/credential"
ERROR = "float/error"

SEND_NOW = "float/send_now"
END = "float/end"

class Comms:
    SUBSCRIBED_TOPICS = {
        STATUS: ("Float status: ", MessageLevel.GOOD),
        CREDENTIAL: ("Company number: ", MessageLevel.GOOD),
        DATA: ("received: ", MessageLevel.GOOD),
        ERROR: ("Error: ", MessageLevel.ERROR)
    }
    def __init__(self):
        self._mqtt_client = MQTTClient("localhost", 1883)

        self.file_receiver_instance = file_receiver() # used to creates received file

        # to end comms and close esp
        self.end_Topic = Topic(END, self._mqtt_client)

        # to get depth values online
        # self._debug_get_depth()

        # to send to esp to send current file
        self.send_now_topic = Topic(SEND_NOW, self._mqtt_client)
        
    def float_communication_setup(self, float_window):
        self.topics_and_handlers: dict[str, tuple[Topic, GUIPrintHandler]] = {} # store topics and handlers to manage them later (e.g. unsubscribing)
        def create_handelers_and_subscribe(**kwargs):
            for key in kwargs.keys():
                topic = Topic(key, self._mqtt_client)
                handler = GUIPrintHandler(kwargs[key][0], kwargs[key][1])
                topic.subscribe(handler)
                handler.bridge.connect_function_upon_activation(lambda msg, level: float_window.post_message(msg, level.value))
                self.topics_and_handlers[key] = (topic, handler)

        # Create handlers and subscribe to topics
        file_receiver_bridge = MQTTSignalBridge()
        file_receiver_bridge.connect_function_upon_activation(lambda msg, level: float_window.post_message(msg, level.value))

        create_handelers_and_subscribe(**self.SUBSCRIBED_TOPICS)

        self.file_receiver_instance.start(self._mqtt_client, DATA, crc32=False)

        # File polling timer (runs in main thread)
        _file_poll_timer = QTimer()
        _cono_poll_timer = QTimer()

        def _check_cono_handeler():
            topic: Topic = self.topics_and_handlers[CREDENTIAL][0]
            handler: GUIPrintHandler = self.topics_and_handlers[CREDENTIAL][1]
            if handler.received:
                _cono_poll_timer.stop()
                topic.unsubscribe(handler)

        def _check_file_complete():
            if self.file_receiver_instance.is_complete:
                _file_poll_timer.stop()
                file_receiver_bridge.activate_signal("CSV file received", MessageLevel.GOOD)
                float_window.load_csv(self.file_receiver_instance.filename)

        # stops timer when file is received
        _file_poll_timer.timeout.connect(_check_file_complete)
        _file_poll_timer.start(5000)

        # unsubscribes to Topics with received messages
        _cono_poll_timer.timeout.connect(_check_cono_handeler)
        _cono_poll_timer.start(5000)

    def _debug_get_depth(self):
        self.depth_topic = Topic("float/depth", self._mqtt_client)
        self.depth_handeler = TerminalPrintHandler("Depth = ")
        self.depth_topic.subscribe(self.depth_handeler)

    def send_file_now(self):
        self.send_now_topic.publish("YALA 2B3AT DELWA2TY 7ALAN")
        print("sent file now command")

    def end_comms(self):
        self.end_Topic.publish("shutdown")
        print("sent shutdown command")

    def send_start_message(self):
        start_topic = self.topics_and_handlers[STATUS][0] # reuse status topic to send start message
        start_topic.publish("start")
        print("sent start message")

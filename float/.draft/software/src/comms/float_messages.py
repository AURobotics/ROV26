from typing import Callable

from PySide6.QtCore import QObject, Signal

from .mqtt import MQTTMessageHandler
from enum import Enum

from gui.message_bar import MessageLevel as GUIMessageLevel

class MessageLevel(Enum):
    GOOD = GUIMessageLevel.OK
    ERROR = GUIMessageLevel.ERROR

# Create a signal proxy/bridge that lives in the main thread
class SignalBridge(QObject):
    """Bridge to safely emit signals from MQTT callbacks to Qt main thread."""

    def __init__(self):
        super().__init__()
    
    def activate_signal(self, message: str, level: MessageLevel = MessageLevel.GOOD):
        """Emit a signal with the given message and level. received by qt and used like the connect input"""
        self.signal.emit(message, level) # type: ignore

    def connect_function_upon_activation(self, slot: Callable):
        """Connect a slot to the signal."""
        self.signal.connect(slot) # type: ignore

class MQTTSignalBridge(SignalBridge):
    """Bridge to safely emit signals from MQTT callbacks to Qt main thread."""
    signal = Signal(str, MessageLevel)

    def connect_function_upon_activation(self, slot: Callable[[str, MessageLevel], None]):
        """ Takes a function or lambda that accepts a string and returns None. """
        super().connect_function_upon_activation(slot)


# MQTT handlers
class GUIPrintHandler(MQTTMessageHandler):
    def __init__(self, prefix: str = "Received message:", level: MessageLevel = MessageLevel.GOOD):
        super().__init__()
        self.bridge = MQTTSignalBridge()
        self.prefix = prefix
        self.level = level
        self.received = False

    def decode(self, message):
        decoded_msg = message.payload.decode()
        self.bridge.activate_signal(f"{self.prefix}{decoded_msg}", self.level)
        self.received = True

class TerminalPrintHandler(MQTTMessageHandler):
    def __init__(self, initial_message: str = "Received message:"):
        super().__init__()
        self.initial_message = initial_message

    def decode(self, message):
        print(f"{self.initial_message}{message.payload.decode()}")
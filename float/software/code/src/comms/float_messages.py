from PySide6.QtCore import QObject, Signal

from .mqtt import MQTTMessageHandeler


# Create a signal proxy/bridge that lives in the main thread
class MQTTSignalBridge(QObject):
    """Bridge to safely emit signals from MQTT callbacks to Qt main thread."""

    status_signal = Signal(str)
    company_number_signal = Signal(str)
    file_complete_signal = Signal()
    run_ended_signal = Signal(str)

    def __init__(self):
        super().__init__()


# MQTT handlers
class StatusHandler(MQTTMessageHandeler):
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self.received = False

    def decode(self, message):
        status = message.payload.decode()
        # Emit signal through bridge - Qt handles thread safety automatically
        self.bridge.status_signal.emit(f"Float status: {status}")
        self.received = True


class CompanyNumberHandler(MQTTMessageHandeler):
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self.received = False

    def decode(self, message):
        company_number = message.payload.decode()
        self.bridge.company_number_signal.emit(f"Received company number: {company_number}")
        self.received = True

class RunEndedHandeler(MQTTMessageHandeler):
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge

    def decode(self, message):
        self.bridge.run_ended_signal.emit(message.payload.decode())

class DepthHandeler(MQTTMessageHandeler):
    def __init__(self):
        super().__init__()
        self.depth = 0

    def decode(self, message):
        print(f"depth = {message.payload.decode()}")
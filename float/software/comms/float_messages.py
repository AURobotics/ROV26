from PySide6.QtCore import QObject, Signal

from .mqtt import mqtt_message


# Create a signal proxy/bridge that lives in the main thread
class MQTTSignalBridge(QObject):
    """Bridge to safely emit signals from MQTT callbacks to Qt main thread."""

    status_signal = Signal(str)
    company_number_signal = Signal(str)
    file_complete_signal = Signal()

    def __init__(self):
        super().__init__()


# MQTT handlers
class StatusHandler(mqtt_message):
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self.received = False

    def decode(self, message):
        status = message.payload.decode()
        # Emit signal through bridge - Qt handles thread safety automatically
        self.bridge.status_signal.emit(f"Float status: {status}")
        self.received = True


class CompanyNumberHandler(mqtt_message):
    def __init__(self, bridge):
        super().__init__()
        self.bridge = bridge
        self.received = False

    def decode(self, message):
        company_number = message.payload.decode()
        self.bridge.company_number_signal.emit(f"Received company number: {company_number}")
        self.received = True

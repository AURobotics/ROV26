import serial
from typing import Optional
from enum import Enum
from pathlib import Path



class ConnectionStatus(Enum):
    CONNECTED: ...
    DISCONNECTED: ...
    CONNECTING: ...
    RECONNECTING: ...
    DISCONNECTING: ...


import serial.tools.list_ports

class SerialDeviceFactory:

    _active_locks : dict[Path, ]= {}

    @classmethod
    def connected_devices(cls) -> list[str]:
        return [port.device for port in serial.tools.list_ports.comports()]

    @classmethod
    def open(cls, port: str, baudrate: int):
        device = Device(serial.Serial(port=str(port), baudrate=baudrate), cls)




















































    



class Device:
    def __init__(self, ser: serial.Serial, factory: type[SerialDeviceFactory]):
        self._serial = ser
        self._factory = factory
        self._connection_status = ConnectionStatus.CONNECTED

    @property
    def connection_status(self) -> ConnectionStatus:
        return self._connection_status

    @property
    def port(self) -> str:
        # devices only instantiated with port when successfully connected
        # and never allowed to change ports
        return self._serial.port # type: ignore

    @property
    def incoming(self):
        if self.connected:
            return self._serial.in_waiting
        else:
            return self.connected

    def clean(self):
        self._serial.reset_input_buffer()
        self._serial.reset_output_buffer()

    def disconnect(self):
        if self._connection_status is not ConnectionStatus.CONNECTED:  # disconnect only when connected
            return
        self._serial.close()
        self._serial.port = None
        self._connected = False

    def send(self, data):
        if self._connection_status is ConnectionStatus.CONNECTED:
            self._serial.write(data)

    @property
    def recieve(self):
        if self.connected and self.incoming:
            buf = self._serial.read_until()
            if buf is None:
                self.clean()
            if len(buf) > 0 and buf.endswith(b"\n"):
                return buf

    def reset_connection(self):
        if self.connected and not self.incoming:
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            self.disconnect()

            self._serial = serial.Serial(port=None, baudrate=self.baudrate)

            if self.port is not None:
                self.connect(self.port)

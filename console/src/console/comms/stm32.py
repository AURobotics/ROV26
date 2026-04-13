import os
import threading

from console.comms.messages import Constants, DfuData, Message, MessageType, Payload
from hal.joystick.manager import Path
from hal.serial.serial_device import SerialDevice


class Stm32:
    _ser: SerialDevice | None
    _serial_lock: threading.RLock
    _programmer_lock: threading.RLock
    programmer: Path | None

    def __init__(self, programmer_executable: os.PathLike | str | None) -> None:
        self._ser = None
        self.programmer = Path(programmer_executable) if programmer_executable else None
        self._ready = False
        self._serial_lock = threading.RLock()
        self._programmer_lock = threading.RLock()

    @property
    def connected(self) -> bool:
        with self._serial_lock:
            if self._ser:
                return self._ser.connected
            return False

    @property
    def port(self) -> str | None:
        with self._serial_lock:
            if self._ser:
                return self._ser.port
            else:
                return None

    @port.setter
    def port(self, value: str | None) -> None:
        with self._serial_lock:
            if value is not None:
                self._ser = SerialDevice(value)
            else:
                if self._ser:
                    self._ser.disconnect()
                self._ser = None

    def reset(self) -> None:
        with self._programmer_lock:
            if self.programmer is None or not self.programmer.exists():
                return
            ...  # TODO

    def enter_dfu(self) -> None:
        with self._serial_lock:
            if not self._ser or not self._ser.connected:
                return
            self._ser.send(Message.encode(DfuData()))

    def flash(self, hex_file: os.PathLike | str):
        with self._programmer_lock:
            if self.programmer is None or not self.programmer.exists():
                return
            if self._ser and self._ser.connected:
                self.enter_dfu()
            ...  # TODO

    @property
    def has_incoming(self) -> bool:
        with self._serial_lock:
            if self._ser:
                return self._ser.has_incoming
            return False

    def send(self, payload: Payload) -> None:
        with self._serial_lock:
            if not self._ser or not self._ser.connected:
                return
            self._ser.send(Message.encode(payload))

    def receive(self) -> Payload | None:
        with self._serial_lock:
            if not self._ser or not self._ser.connected:
                return None
            sync_byte = self._ser.read_until(Constants.SYNC_BYTE)
            if not sync_byte:
                return None
            type_byte = self._ser.read()
            if not type_byte:
                return None
            message_type = MessageType.from_type(type_byte[0])
            data = self._ser.read(message_type.size)
            if not data:
                return None
            return Message.decode(message_type, data)

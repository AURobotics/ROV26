import os
import subprocess
import re
import threading

from console.comms.messages import Constants, DfuData, Message, MessageType, Payload
from hal.joystick.manager import Path
from hal.serial.serial_device import SerialDevice


class Stm32:
    _ser: SerialDevice | None
    _serial_lock: threading.RLock
    _programmer_lock: threading.RLock
    programmer: Path | None

    def __init__(self, programmer_executable: os.PathLike | str | None = None) -> None:
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

    def connect(self, port: str) -> None:
        self.port = port

    def disconnect(self) -> None:
        self.port = None

    def reset(self, device: str) -> None:
        with self._programmer_lock:
            if not self.programmer_present:
                return
            subprocess.run([str(self.programmer), "-c", f"port={device}", "-s"])

    def enter_dfu(self) -> None:
        with self._serial_lock:
            if not self._ser or not self._ser.connected:
                return
            self._ser.send(Message.encode(DfuData()))

    def flash(self, device: str, hex_file: os.PathLike | str):
        with self._programmer_lock:
            if not self.programmer_present:
                return
            if self._ser and self._ser.connected:
                self.enter_dfu()
            subprocess.run(
                [str(self.programmer), "-c", f"port={device}", "-d", hex_file, "-s"]
            )

    @property
    def programmable_devices(self) -> list[tuple[str, str]]:
        """
        Returns:
            list[tuple[str, str]]: A tuple of (PortID, Description)
        """
        with self._programmer_lock:
            if not self.programmer_present:
                return []
            cli_result = subprocess.run(
                [str(self.programmer), "-l", "usb"], capture_output=True, text=True
            )
            if cli_result.returncode != 0:
                return []
            ports: list[tuple[str, str]] = re.findall(
                r"Device Index\s+:\s+(.+?)\s+.*?Product ID\s+:\s+(.+)",
                cli_result.stdout,
                re.DOTALL,
            )
            return [(p[0].strip(), p[1].strip()) for p in ports]

    @property
    def programmer_present(self) -> bool:
        with self._programmer_lock:
            if self.programmer is None or not self.programmer.exists():
                return False
            test_command = subprocess.run(
                [str(self.programmer), "--version"],
                capture_output=True,
                text=True,
            )
            if "STM32CubeProgrammer version" in test_command.stdout:
                return True
            return False

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

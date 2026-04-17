import os
import subprocess
import re
import threading

from console.comms.messages import Constants, DfuData, Message, MessageType, Payload
from hal.joystick.manager import Path
from hal.serial.serial_device import SerialDevice, list_ports


class Stm32:
    _ser: SerialDevice
    _serial_lock: threading.RLock
    _programmer_lock: threading.RLock
    programmer: Path | None

    def __init__(
        self,
        read_timeout: float = 0.005,
        write_timeout: float = 0.1,
        continuity_timeout: float = 0.005,
        programmer_executable: os.PathLike | str | None = None,
    ) -> None:
        self._ser = SerialDevice(
            timeout=read_timeout,
            write_timeout=write_timeout,
            inter_byte_timeout=continuity_timeout,
        )
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self.continuity_timeout = continuity_timeout
        self.programmer = Path(programmer_executable) if programmer_executable else None
        self._ready = False
        self._serial_lock = threading.RLock()
        self._programmer_lock = threading.RLock()

    @property
    def connected(self) -> bool:
        with self._serial_lock:
            return self._ser.is_open

    @property
    def port(self) -> str | None:
        with self._serial_lock:
            if self._ser.is_open:
                return self._ser.port
        return None

    @port.setter
    def port(self, value: str | None) -> None:
        with self._serial_lock:
            self._ser.port = value

    @property
    def name(self) -> str | None:
        with self._serial_lock:
            port = self.port
        if port is not None:
            for p in list_ports():
                if port == p.device:
                    return p.description
        return None

    def connect(self, port: str) -> None:
        self.port = port

    def disconnect(self) -> None:
        self.port = None

    def reset(self, device: str) -> None:
        with self._programmer_lock:
            if not self.programmer_present:
                return
            subprocess.run(
                [str(self.programmer), "-c", f"port={device}", "-s"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def enter_dfu(self) -> None:
        with self._serial_lock:
            if not self._ser.is_open:
                return
            self._ser.write(Message.encode(DfuData()))

    def flash(self, device: str, hex_file: os.PathLike | str):
        with self._programmer_lock:
            if not self.programmer_present:
                return
            if self._ser.is_open:
                self.enter_dfu()
            subprocess.run(
                [str(self.programmer), "-c", f"port={device}", "-d", hex_file, "-s"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
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
                [str(self.programmer), "-l", "usb"], capture_output=True, text=True,
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
            env = os.environ.copy()
            lib_path = self.programmer.parent.parent / "lib"
            if "LD_LIBRARY_PATH" in env:
                env["LD_LIBRARY_PATH"] = f"{lib_path}:{env['LD_LIBRARY_PATH']}"
            else:
                env["LD_LIBRARY_PATH"] = str(lib_path)
            test_command = subprocess.run(
                [str(self.programmer), "--version"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if test_command.returncode == 0:
                return True
            return False

    @property
    def has_incoming(self) -> bool:
        with self._serial_lock:
            if self._ser.is_open:
                return self._ser.in_waiting > 0
            return False

    def send(self, payload: Payload) -> None:
        with self._serial_lock:
            if not self._ser.is_open:
                return
            self._ser.write(Message.encode(payload))

    def receive(self) -> Payload | None:
        with self._serial_lock:
            if not self._ser.is_open:
                return None
            sync_byte = self._ser.read_until(Constants.SYNC_BYTE)
            if not sync_byte or sync_byte[-1] != Constants.SYNC_INT:
                return None
            type_byte = self._ser.read()
            if not type_byte:
                return None
            message_type = MessageType.from_type(type_byte[0])
            data = self._ser.read(message_type.size)
            if len(data) != message_type.size:
                return None
            return Message.decode(message_type, data)

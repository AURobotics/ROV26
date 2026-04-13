from __future__ import annotations
from typing import cast, Self

import serial
import threading

import sys

if sys.platform == "win32":
    from serial.tools.list_ports import comports as list_ports
else:
    from serial.tools.list_ports_common import ListPortInfo
    from pathlib import Path
    from serial.tools.list_ports import comports

    def list_ports() -> list[ListPortInfo]:
        devices = [str(path.resolve()) for path in Path("/dev/serial/by-id/").glob("*")]
        ports = comports()
        return [port for port in ports if port.device in devices]


class SerialDevice:
    _registry: dict[str, SerialDevice] = {}
    _connection_lock: threading.RLock = threading.RLock()

    _serial: serial.Serial
    _port: str
    _baudrate: int

    def __new__(cls, port: str, **kwargs) -> Self:
        with cls._connection_lock:
            if sys.platform != "win32":
                port = str(Path(port).resolve())
            if port not in cls._registry:
                instance = super().__new__(cls)
                cls._registry[port] = instance
            else:
                instance = cls._registry[port]
            return cast(Self, instance)

    def __init__(self, port: str, baudrate: int = 9600, timeout: float | None = None):
        available_ports = [port.device for port in list_ports()]
        if sys.platform != "win32":
            port_path = Path(port).resolve()
            if not port_path.exists():
                raise ValueError(f"Invalid device path: {port}")
            port = str(port_path)
        if port not in available_ports:
            raise ValueError(f"Provided device {port} is not a serial port")

        self._port = port
        if not self._check_alive() or (
            hasattr(self, "_baudrate") and self._baudrate != baudrate
        ):
            with self._connection_lock:
                try:
                    self._serial = serial.Serial(
                        port=port, baudrate=baudrate, timeout=timeout
                    )
                except:
                    self._unregister_port(port)
        self._baudrate = baudrate

    def _check_alive(self) -> bool:
        if not hasattr(self, "_serial"):
            return False
        try:
            self._serial.write(b"")
            return True
        except:
            return False

    @property
    def connected(self) -> bool:
        if not self._check_alive():
            self.disconnect()
            return False
        return True

    @property
    def port(self) -> str:
        if not self.connected:
            return "Disconnected"
        return self._port

    @property
    def has_incoming(self) -> bool:
        try:
            if self.connected:
                return self._serial.in_waiting > 0
            else:
                return False
        except:
            return False

    def flush(self) -> None:
        try:
            if self.connected:
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()
        except:
            return

    def flush_in(self) -> None:
        try:
            if self.connected:
                self._serial.reset_input_buffer()
        except:
            return

    def flush_out(self) -> None:
        try:
            if self.connected:
                self._serial.reset_output_buffer()
        except:
            return

    @classmethod
    def _unregister_port(cls, port) -> None:
        with cls._connection_lock:
            if port in cls._registry:
                cls._registry.pop(port)

    def disconnect(self):
        if hasattr(self, "_serial") and self._serial.is_open:
            try:
                self._serial.close()
            except:
                pass
        self._unregister_port(self._port)

    def send(self, data) -> None:
        if self.connected:
            try:
                self._serial.write(data)
            except:
                return

    def read(self, size=1) -> bytes:
        try:
            if self.connected:
                buf = self._serial.read(size)
                if not buf:
                    self.flush_in()
                return buf
        except:
            pass
        return bytes()

    def read_until(self, byte: bytes) -> bytes:
        try:
            if self.connected:
                buf = self._serial.read_until(byte)
                if not buf:
                    self.flush_in()
                return buf
        except:
            pass
        return bytes()

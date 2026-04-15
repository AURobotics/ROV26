from __future__ import annotations
from dataclasses import dataclass
from typing import cast, TYPE_CHECKING

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


@dataclass(slots=True)
class _RegistryEntry:
    serial: serial.Serial
    usage_counter: int


class _SerialDevice:
    _registry: dict[str, _RegistryEntry] = {}
    _connection_lock: threading.RLock = threading.RLock()
    _fallback_serial: serial.Serial = serial.Serial()

    _serial: serial.Serial | None
    _settings: dict

    def __init__(self, *args, **kwargs) -> None:
        if args:
            port: str | None = args[0]
            args = args[1:]

        else:
            port: str | None = kwargs.get("port")
        if not port:
            settings = serial.Serial(*args, **kwargs).get_settings()
            settings.pop("port", None)
            self._settings = settings
            self._serial = None
            return
        with self._connection_lock:
            try:
                self._serial = self._acquire_port(port, *args, **kwargs)
                settings = self._serial.get_settings()
                settings.pop("port", None)
                self._settings = settings
            except:
                self._release_port(port)
                raise

    @property
    def is_open(self) -> bool:
        with self._connection_lock:
            if not self._serial or not self._serial.is_open:
                return False
            try:
                self._serial.write(b"")
                return True
            except:
                return False

    @property
    def port(self) -> str | None:
        if not self._serial:
            return None
        if not self.is_open:
            self._release_port(self._serial.port)
            self._serial = None
            return None
        return self._serial.port

    @port.setter
    def port(self, port: str | None):
        if port == self.port:
            return
        with self._connection_lock:
            if self._serial:
                self._release_port(self._serial.port)
                self._serial = None
            if port:
                self._serial = self._acquire_port(port, **self._settings)

    def open(self) -> None:
        if self._serial and not self.is_open:
            self.port = self._serial.port

    @classmethod
    def _acquire_port(cls, port: str, *args, **kwargs) -> serial.Serial:
        available_ports = [port.device for port in list_ports()]
        if sys.platform != "win32":
            port_path = Path(port).resolve()
            if not port_path.exists():
                raise ValueError(f"Invalid device path: {port}")
            port = str(port_path)
        if port not in available_ports:
            raise ValueError(f"Provided device {port} is not a serial port")
        with cls._connection_lock:
            if port not in cls._registry:
                instance = serial.Serial(port=port, *args, **kwargs)
                cls._registry[port] = _RegistryEntry(instance, 1)
            else:
                settings = serial.Serial(*args, **kwargs).get_settings()
                entry = cls._registry[port]
                instance = entry.serial
                prev_settings = instance.get_settings()
                prev_settings.pop("port", None)
                if prev_settings != settings:
                    instance.apply_settings(settings)
                entry.usage_counter += 1

            return cast(serial.Serial, instance)

    @classmethod
    def _release_port(cls, port) -> None:
        with cls._connection_lock:
            entry = cls._registry.get(port)
            if not entry:
                return
            entry.usage_counter -= 1
            if entry.usage_counter == 0:
                entry.serial.close()
                cls._registry.pop(port)

    def __getattr__(self, name):
        with self._connection_lock:
            if self._serial:
                return getattr(self._serial, name)
            else:
                return getattr(self._fallback_serial, name)


if TYPE_CHECKING:

    class SerialDevice(serial.Serial): ...
else:
    SerialDevice = _SerialDevice

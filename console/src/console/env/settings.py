import sys
from typing import Any

from PySide6.QtCore import QObject, QSettings, Signal

from console.assets import get_asset
from console.env.pathing import get_base_path

class _SignalHolder(QObject):
    changed = Signal(str, object)  # key, value

_signal_holder = _SignalHolder()

class Settings:
    changed = _signal_holder.changed

    _fresh_start: bool

    def __init__(self) -> None:
        usr = get_base_path() / "settings.ini"
        self._fresh_start = not usr.exists()
        usr.touch()
        usr_path = str(usr)
        self._user_settings = QSettings(usr_path, QSettings.Format.IniFormat)
        default_path = get_asset("default_settings.ini")
        self._default_settings = QSettings(default_path, QSettings.Format.IniFormat)
        platform_path = get_asset(f"default_settings_{sys.platform}.ini")
        self._platform_settings = QSettings(platform_path, QSettings.Format.IniFormat)

    @property
    def is_fresh(self) -> bool:
        return self._fresh_start

    def get_default(self, key: str) -> Any:
        if self._platform_settings.contains(key):
            return self._platform_settings.value(key)
        else:
            return self._default_settings.value(key)


    def get(self, key: str) -> Any:
        if self._user_settings.contains(key):
            return self._user_settings.value(key)
        else:
            return self.get_default(key)

    def set(self, key: str, value: Any) -> None:
        self._user_settings.setValue(key, value)
        self.changed.emit(key, value)
        self._user_settings.sync()

    def restore_defaults(self) -> None:
        self._user_settings.clear()
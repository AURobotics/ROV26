from typing import Any

from PySide6.QtCore import QSettings
from console.assets import get_asset

_default_settings = QSettings(
    get_asset("default_settings.ini"), QSettings.Format.IniFormat
)

_default_settings_windows = QSettings(
    get_asset("default_settings_win32.ini"), QSettings.Format.IniFormat
)


def get(key: str) -> Any:
    return _default_settings.value(key)
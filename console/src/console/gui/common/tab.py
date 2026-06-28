from typing import Any

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QWidget

from console.env import Settings


class GuiTab(QWidget):
    attention_needed = Signal(bool)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        Settings.changed.connect(self.on_settings_changed)

    @Slot(str, object)
    def on_settings_changed(self, key: str, value: Any) -> None: ...

    @property
    def needs_attention(self) -> bool:
        return False

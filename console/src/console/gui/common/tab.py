from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget


class GuiTab(QWidget):
    attention_needed = Signal(bool)

    @property
    def needs_attention(self) -> bool:
        return False

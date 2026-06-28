from PySide6.QtGui import QFocusEvent, QShowEvent
from PySide6.QtWidgets import QComboBox
from PySide6.QtCore import Signal


class ClickableComboBox(QComboBox):
    triggered = Signal()

    def showPopup(self) -> None:
        self.triggered.emit()
        return super().showPopup()

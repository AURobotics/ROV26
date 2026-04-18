from PySide6.QtWidgets import QWidget, QGridLayout, QProgressBar, QLabel, QSizePolicy
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtCore import QTimer

from random import randint


class LeakageDisplay(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        font = QFont()
        font.setPointSize(10)

        self._layout = QGridLayout(self)

        self._colour1 = "#62c1e5"

        self._sensor1 = QProgressBar()
        self._sensor1.setTextVisible(False)
        self._sensor1.setFixedHeight(8)
        self._sensor1.setStyleSheet(
            """
            QProgressBar {
                border-radius: 4px;
                background-color: grey;
                padding: 0px;
            }
            QProgressBar::chunk {
                border-radius: 4px;
                background-color: """
            + self._colour1
            + ";}"
        )
        self._sensor1.setRange(0, 100)
        self._sensor1.setValue(0)
        self._sensor1.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._layout.addWidget(self._sensor1, 0, 0)

        self._label1 = QLabel("temp1")
        self._label1.setFont(font)
        self._label1.setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum
        )
        self._layout.addWidget(self._label1, 0, 1)

        metrics = QFontMetrics(font)
        max_label_width = metrics.horizontalAdvance("100%")
        self._layout.setColumnMinimumWidth(1, max_label_width + 10)
        self._layout.setColumnStretch(1, 0)

        self._timer = QTimer()
        self._timer.timeout.connect(self.updateSensors)
        self._timer.start(100)

    def updateSensors(self):
        new_value = max(0, min(100, self._sensor1.value() + randint(-5, 5)))
        if new_value != self._sensor1.value():
            self._sensor1.setValue(new_value)
            self._label1.setText(f"{self._sensor1.value()}%")

            if self._sensor1.value() < 25:
                new_colour = "#62c1e5"
            elif self._sensor1.value() < 50:
                new_colour = "#F2D06B"
            elif self._sensor1.value() < 75:
                new_colour = "#F4A261"
            else:
                new_colour = "#E76F51"

            if new_colour != self._colour1:
                self._colour1 = new_colour
                self._sensor1.setStyleSheet(
                    """
                    QProgressBar {
                        border-radius: 4px;
                        background-color: grey;
                        padding: 0px;
                    }
                    QProgressBar::chunk {
                        border-radius: 4px;
                        background-color: """
                    + self._colour1
                    + ";}"
                )

    def hideEvent(self, event):
        super().hideEvent(event)
        self._timer.stop()

    def showEvent(self, event):
        super().showEvent(event)
        self._timer.start(100)

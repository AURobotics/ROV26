from PySide6.QtWidgets import (
    QLabel,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from console.comms.rov.stm32 import Stm32
from console.gui.connections_tab.serial_tab import SerialTab
from hal.joystick.active_joystick import ActiveJoystick

class ConnectionsTab(QWidget):
    def __init__(self, joystick: ActiveJoystick, serial: Stm32):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        joystick_menu = QLabel("Placeholder for joystick menu")
        joystick_menu.setAlignment(Qt.AlignmentFlag.AlignCenter)

        serial_tab = SerialTab(serial)

        self.splitter.addWidget(joystick_menu)
        self.splitter.addWidget(serial_tab)

        layout.addWidget(self.splitter)

    def hideEvent(self, event):
        super().hideEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self.splitter.setSizes([self.width() // 2, self.width() // 2])

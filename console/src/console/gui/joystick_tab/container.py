from string import Template

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from console.gui.common.combobox import ClickableComboBox
from console.gui.common.tab import GuiTab
from hal.joystick.active_joystick import ActiveJoystick
from hal.joystick.manager import JoystickManager


class JoystickTab(GuiTab):
    _CONNECTED_STATUS = Template("Connected to $name")
    _CONNECTED_HINT = Template(
        "Index: $idx\nID: $guid\nPower: $power\nGamepad: $gamepad"
    )
    _DISCONNECTED_STATUS = "Not connected to a joystick"
    _DISCONNECTED_HINT = "Connect to a joystick to start piloting"
    _refresh_signal = Signal()

    def __init__(self, joystick: ActiveJoystick):
        super().__init__()

        self.joystick = joystick
        self.manager = JoystickManager()

        self.main_layout = QVBoxLayout(self)
        self.main_layout.addStretch()

        self.status_label = QLabel(self._DISCONNECTED_STATUS)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.main_layout.addWidget(self.status_label)
        self.hint_label = QLabel(self._DISCONNECTED_HINT)
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.hint_label.setStyleSheet("font-size: 12px;")
        self.main_layout.addWidget(
            self.hint_label, alignment=Qt.AlignmentFlag.AlignHCenter
        )
        self.main_layout.addStretch()

        utils_hbox = QHBoxLayout()
        port_group = QGroupBox()
        port_group.setTitle("Manage Connection")
        port_form = QFormLayout(port_group)
        self.joy_selector = ClickableComboBox()
        self.joy_selector.activated.connect(self.select_joystick)
        port_form.addRow("Joystick:", self.joy_selector)
        self.disconnect_button = QPushButton("Disconnect")
        self.disconnect_button.pressed.connect(self.deselect_joystick)
        self.disconnect_button.setFixedWidth(120)
        port_form.addWidget(self.disconnect_button)
        utils_hbox.addWidget(port_group)

        self._disconnected = False

        self.main_layout.addLayout(utils_hbox)
        self._refresh_signal.connect(self.refresh_joysticks)
        self._connection_callback = lambda x, y: self._refresh_signal.emit()
        self.manager.add_connection_listener(self._connection_callback)

        self.refresh_joysticks()

    @property
    def needs_attention(self) -> bool:
        return self.joystick.selected is None

    @Slot(int)
    def select_joystick(self, idx: int) -> None:
        joysticks = self.manager.joysticks
        if idx < len(joysticks):
            self.joystick.selected = self.manager.joysticks[idx]
        self._disconnected = False
        self.refresh_joysticks()

    def deselect_joystick(self) -> None:
        self.joystick.selected = None
        self._disconnected = True
        self.refresh_joysticks()

    @Slot()
    def refresh_joysticks(self) -> None:
        if self.joystick.selected is not None and not self.joystick.connected:
            self.joystick.selected = None
        if (
            self.joystick.selected is None
            and self.manager.joysticks
            and not self._disconnected
        ):
            self.joystick.selected = self.manager.joysticks[0]

        self.joy_selector.clear()

        for i, joy in enumerate(self.manager.joysticks):
            self.joy_selector.addItem(joy.name)
            if self.joystick.selected == joy:
                self.joy_selector.setCurrentIndex(i)

        self.disconnect_button.setEnabled(self.joystick.selected is not None)
        self.attention_needed.emit(self.joystick.selected is None)
        if self.joystick.selected is None:
            self.joy_selector.setCurrentIndex(-1)
            self.status_label.setText(self._DISCONNECTED_STATUS)
            self.hint_label.setText(self._DISCONNECTED_HINT)
        else:
            self.status_label.setText(
                self._CONNECTED_STATUS.substitute(name=self.joystick.name)
            )
            self.hint_label.setText(
                self._CONNECTED_HINT.substitute(
                    idx=self.joystick.id,
                    power=self.joystick.power,
                    guid=self.joystick.guid,
                    gamepad="yes" if self.joystick.is_gamepad else "no",
                )
            )

from PySide6.QtCore import Slot, Signal
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMenuBar, QMenu, QWidget
from PySide6.QtGui import QAction
from console.core.active_joystick import ActiveJoystick
from console.core.comms.stm32 import STM32
from lib.device.joystick import JoystickManager


class MenuBar(QMenuBar):
    _joysticks_changed = Signal()

    def __init__(
        self, parent: QWidget, active_joystick: ActiveJoystick, serial_device: STM32
    ):
        super().__init__(parent=parent)
        self._serial_menu = self.addMenu("Serial Port")
        self._serial_menu_sep = self._serial_menu.addSeparator()
        self._serial_menu_add_custom = self._serial_menu.addAction("Custom Port")
        self._serial_menu_no_serial = QAction("No Serial Ports")
        self._serial_menu_no_serial.setEnabled(False)
        self._displayed_ports: dict[str, QAction] = {}
        self._custom_port: tuple[str, QAction] | None = None
        self._serial_menu.aboutToShow.connect(self.update_serial_ports)
        self._serial = serial_device

        self._active_joystick = active_joystick
        self._joystick_menu = self.addMenu("Joystick")
        self._no_joystick_action = QAction("No joysticks Connected", self._joystick_menu)
        self._no_joystick_action.setEnabled(False)
        self._displayed_joysticks: dict[int, QAction] = {}
        self._joyman = JoystickManager()
        self._on_joysticks_changed = lambda x,y: self._joysticks_changed.emit()
        self._joyman.add_connection_listener(self._on_joysticks_changed)
        self._joysticks_changed.connect(self.update_joysticks)
        self.triggered.connect(self._on_triggered)
        self.refresh()

    @Slot(QAction)
    def _on_triggered(self, action: QAction):
        parent = action.parent()
        if parent == self._joystick_menu:
            self._on_joystick_action(action)
        elif parent == self._serial_menu:
            self._on_serial_port_action(action)

    def _on_joystick_action(self, action: QAction):
        for j_id, a in self._displayed_joysticks.items():
            if a == action:
                if not action.isChecked():
                    self._active_joystick.selected = None
                else:
                    self._active_joystick.selected = self._joyman.joystick_by_id(j_id)
                return

    def _on_serial_port_action(self, action: QAction):
        if action == self._serial_menu_add_custom:
            self.manual_port_selection()
            return
        if self._custom_port is not None and action == self._custom_port[1]:
            if self._custom_port[1].isChecked():
                self._serial.disconnect()
            else:
                self._serial.connect(self._custom_port[0])
            return
        for port, a in self._displayed_ports.items():
            if a == action:
                if not action.isChecked():
                    self._serial.disconnect()
                else:
                    self._serial.connect(port)
                return

    @Slot()
    def refresh(self):
        self.update_joysticks()
        self.update_serial_ports()

    @Slot(object)
    def update_joysticks(self):
        joysticks = self._joyman.joysticks
        if len(joysticks) == 0:
            for action in list(self._joystick_menu.actions()):
                self._joystick_menu.removeAction(action)
            self._displayed_joysticks = {}
            self._joystick_menu.addAction(self._no_joystick_action)
            return
        else:
            if self._no_joystick_action in self._joystick_menu.actions():
                self._active_joystick.selected = joysticks[0]
                self._joystick_menu.removeAction(self._no_joystick_action)


        new_joysticks = {j.id for j in joysticks}
        old_joysticks = set(self._displayed_joysticks.keys())
        to_remove = old_joysticks.difference(new_joysticks)
        to_add = new_joysticks.difference(old_joysticks)

        for j_id, action in list(self._displayed_joysticks.items()):
            if j_id in to_remove:
                self._joystick_menu.removeAction(action)
                self._displayed_joysticks.pop(j_id)
                action.deleteLater()

        for joystick in joysticks:
            action: QAction
            if joystick.id not in to_add:
                action = self._displayed_joysticks[joystick.id]
            else:
                action = QAction(
                    f"{joystick.id}: {joystick.name}", self._joystick_menu
                )
                self._joystick_menu.addAction(action)
                action.setCheckable(True)
                self._displayed_joysticks[joystick.id] = action
            action.setChecked(self._active_joystick.selected == joystick)

    @Slot()
    def update_serial_ports(self):
        ports = self._serial.available_ports
        new_ports = set(ports)
        old_ports = set(self._displayed_ports.keys())
        to_remove = old_ports.difference(new_ports)
        to_add = new_ports.difference(old_ports)
        connected_port: str | None = (
            self._serial.port if self._serial.connected else None
        )

        for port, action in self._displayed_ports.items():
            if port in to_remove:
                self._displayed_ports.pop(port)
                self._serial_menu.removeAction(action)

        for port in ports:
            action: QAction
            if port not in to_add:
                action = self._displayed_ports[port]
            else:
                action = QAction(port, self._serial_menu)
                self._serial_menu.insertAction(self._serial_menu_sep, action)
                action.setCheckable(True)
                self._displayed_ports[port] = action
            action.setChecked(port == connected_port)

        if (
            connected_port is None or connected_port not in ports
        ) and self._custom_port is not None:
            self._serial_menu.removeAction(self._custom_port[1])
            self._custom_port = None

        elif connected_port is not None:
            if self._custom_port is not None:
                action = self._custom_port[1]
                action.setText(connected_port)
                self._custom_port = (connected_port, action)
            else:
                action = QAction(connected_port, self._serial_menu)
                self._custom_port = (connected_port, action)
                self._serial_menu.addAction(action)

    def manual_port_selection(self):
        text, ok = QInputDialog.getText(
            self,
            "Custom Port",
            "Port Name (RFC2217 NOT FULLY SUPPORTED):",
            QLineEdit.EchoMode.Normal,
            "COM",
        )
        if ok:
            self._serial.connect(text)

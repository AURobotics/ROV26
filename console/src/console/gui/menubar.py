from PySide6.QtCore import Slot, Signal
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMenuBar, QMenu, QWidget
from PySide6.QtGui import QAction
from typing import Collection
from console.core.comms.stm32 import STM32
from console.core.gamepad import ConnectionUpdate, Controller


class MenuBar(QMenuBar):
    _esp_menu: QMenu
    _controller_menu: QMenu
    _esp_actions: list[QAction]
    _controllers_changed = Signal(object)

    def __init__(self, parent: QWidget, controller: Controller, serial_device: STM32):
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

        self._controller_menu = self.addMenu("Controller")
        self._displayed_controllers: dict[int, QAction] = {}
        self._controller = controller
        controller.register_connection_listener(self._controllers_changed.emit)
        self._controllers_changed.connect(self.update_controllers)

        self.triggered.connect(self._on_triggered)

    @Slot(QAction)
    def _on_triggered(self, action: QAction):
        parent = action.parent()
        if parent == self._controller_menu:
            self._on_controller_action(action)
        elif parent == self._serial_menu:
            self._on_serial_port_action(action)

    def _on_controller_action(self, action: QAction):
        for c_id, a in self._displayed_controllers.items():
            if a == action:
                if not action.isChecked():
                    self._controller.gamepad = None
                else:
                    self._controller.gamepad = c_id
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
        self.update_controllers()
        self.update_serial_ports()

    @Slot(object)
    def update_controllers(self, controllers: Collection[ConnectionUpdate]):
        if len(controllers) == 0:
            for action in self._controller_menu.actions():
                self._controller_menu.removeAction(action)
            self._displayed_controllers = {}
            no_controller = QAction("No Controllers Connected", self._controller_menu)
            no_controller.setEnabled(False)
            self._controller_menu.addAction(no_controller)
            return

        new_controllers = {c["id"] for c in controllers}
        old_controllers = set(self._displayed_controllers.keys())
        to_remove = old_controllers.difference(new_controllers)
        to_add = new_controllers.difference(old_controllers)

        for c_id, action in self._displayed_controllers.items():
            if c_id in to_remove:
                self._controller_menu.removeAction(action)
                self._displayed_controllers.pop(c_id)

        for controller in controllers:
            action: QAction
            if controller["id"] not in to_add:
                action = self._displayed_controllers[controller["id"]]
            else:
                action = QAction(
                    f"{controller['id']}: {controller['name']}", self._controller_menu
                )
                self._controller_menu.addAction(action)
                action.setCheckable(True)
                self._displayed_controllers[controller["id"]] = action
            action.setChecked(controller["open"])

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

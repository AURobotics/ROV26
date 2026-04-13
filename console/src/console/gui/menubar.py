from PySide6.QtCore import Slot, Signal
from PySide6.QtWidgets import QMenuBar, QWidget
from PySide6.QtGui import QAction
from hal.joystick.active_joystick import ActiveJoystick
from hal.joystick.manager import JoystickManager


class MenuBar(QMenuBar):
    _joysticks_changed = Signal()

    def __init__(self, parent: QWidget, active_joystick: ActiveJoystick):
        super().__init__(parent=parent)
        self._active_joystick = active_joystick
        self._joystick_menu = self.addMenu("Joystick")
        self._no_joystick_action = QAction(
            "No joysticks Connected", self._joystick_menu
        )
        self._no_joystick_action.setEnabled(False)
        self._displayed_joysticks: dict[int, QAction] = {}
        self._joyman = JoystickManager()
        self._on_joysticks_changed = lambda x, y: self._joysticks_changed.emit()
        self._joyman.add_connection_listener(self._on_joysticks_changed)
        self._joysticks_changed.connect(self.update_joysticks)
        self.triggered.connect(self._on_triggered)
        self.refresh()

    @Slot(QAction)
    def _on_triggered(self, action: QAction):
        parent = action.parent()
        if parent == self._joystick_menu:
            self._on_joystick_action(action)

    def _on_joystick_action(self, action: QAction):
        for j_id, a in self._displayed_joysticks.items():
            if a == action:
                if not action.isChecked():
                    self._active_joystick.selected = None
                else:
                    self._active_joystick.selected = self._joyman.joystick_by_id(j_id)
                return

    @Slot()
    def refresh(self):
        self.update_joysticks()

    @Slot(object)
    def update_joysticks(self):
        joysticks = self._joyman.joysticks
        if len(joysticks) == 0:
            for action in list(self._joystick_menu.actions()):
                self._joystick_menu.removeAction(action)
            self._displayed_joysticks = {}
            self._joystick_menu.addAction(self._no_joystick_action)
            self._active_joystick.selected = None
            return
        else:
            if self._no_joystick_action in self._joystick_menu.actions():
                self._joystick_menu.removeAction(self._no_joystick_action)
            if self._active_joystick.selected not in joysticks:
                self._active_joystick.selected = joysticks[0]

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
                action = QAction(f"{joystick.id}: {joystick.name}", self._joystick_menu)
                self._joystick_menu.addAction(action)
                action.setCheckable(True)
                self._displayed_joysticks[joystick.id] = action
            action.setChecked(self._active_joystick.selected == joystick)

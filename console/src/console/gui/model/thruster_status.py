from PySide6.QtCore import QTimer, Slot, QObject, Property, Signal
from random import uniform

class ThrusterStatus(QObject):
    thrustLevelChanged = Signal()

    def __init__(self):
        super().__init__()
        self._thrustLevel1 = 0
        self._thrustLevel2 = 0
        self._thrustLevel3 = 0
        self._thrustLevel4 = 0

        self._timer = QTimer()
        self._timer.timeout.connect(self.update_thrust)
        self._timer.start(500)

    @Property(float, notify=thrustLevelChanged)
    def thrustLevel1(self):
        return self._thrustLevel1
    
    @Property(float, notify=thrustLevelChanged)
    def thrustLevel2(self):
        return self._thrustLevel2

    @Property(float, notify=thrustLevelChanged)
    def thrustLevel3(self):
        return self._thrustLevel3

    @Property(float, notify=thrustLevelChanged)
    def thrustLevel4(self):
        return self._thrustLevel4

    @Slot()
    def update_thrust(self):
        new_thrust1 = max(-1, min(1, self._thrustLevel1 + uniform(-0.1, 0.1)))
        new_thrust2 = max(-1, min(1, self._thrustLevel2 + uniform(-0.1, 0.1)))
        new_thrust3 = max(-1, min(1, self._thrustLevel3 + uniform(-0.1, 0.1)))
        new_thrust4 = max(-1, min(1, self._thrustLevel4 + uniform(-0.1, 0.1)))

        changed = False
        if self._thrustLevel1 != new_thrust1:
            self._thrustLevel1 = new_thrust1
            changed = True
        if self._thrustLevel2 != new_thrust2:
            self._thrustLevel2 = new_thrust2
            changed = True
        if self._thrustLevel3 != new_thrust3:
            self._thrustLevel3 = new_thrust3
            changed = True
        if self._thrustLevel4 != new_thrust4:
            self._thrustLevel4 = new_thrust4
            changed = True
        if changed:
            self.thrustLevelChanged.emit()
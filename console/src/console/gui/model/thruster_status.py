import math
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
        self._thrustLevel5 = 0

        self._total_h_thrust = 0
        self._h_angle = 0

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
    
    @Property(float, notify=thrustLevelChanged)
    def thrustLevel5(self):
        return self._thrustLevel5
    
    @Property(float, notify=thrustLevelChanged)
    def totalHorizontalThrust(self):
        return self._total_h_thrust
    
    @Property(float, notify=thrustLevelChanged)
    def horizontalAngle(self):
        return self._h_angle
    
    def calc_direction(self):
        x_total = self._thrustLevel1 / math.sqrt(2)
        y_total = self._thrustLevel1 / math.sqrt(2)
        x_total = x_total - self._thrustLevel2 / math.sqrt(2)
        y_total = y_total + self._thrustLevel2 / math.sqrt(2)
        x_total = x_total - self._thrustLevel3 / math.sqrt(2)
        y_total = y_total + self._thrustLevel3 / math.sqrt(2)
        x_total = x_total + self._thrustLevel4 / math.sqrt(2)
        y_total = y_total + self._thrustLevel4 / math.sqrt(2)

        self._total_h_thrust = math.sqrt(x_total**2 + y_total**2)
        self._h_angle = math.atan2(y_total, x_total) * 180 / math.pi

    @Slot()
    def update_thrust(self):
        new_thrust1 = max(-1, min(1, self._thrustLevel1 + uniform(-0.1, 0.1)))
        new_thrust2 = max(-1, min(1, self._thrustLevel2 + uniform(-0.1, 0.1)))
        new_thrust3 = max(-1, min(1, self._thrustLevel3 + uniform(-0.1, 0.1)))
        new_thrust4 = max(-1, min(1, self._thrustLevel4 + uniform(-0.1, 0.1)))
        new_thrust5 = max(-1, min(1, self._thrustLevel5 + uniform(-0.1, 0.1)))

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
        if self._thrustLevel5 != new_thrust5:
            self._thrustLevel5 = new_thrust5
            changed = True
        if changed:
            self.calc_direction()
            self.thrustLevelChanged.emit()
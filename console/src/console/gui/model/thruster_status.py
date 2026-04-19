import math
from PySide6.QtCore import QTimer, Slot, QObject, Property, Signal

from console.comms.manager import CommunicationManager


class ThrusterStatus(QObject):
    thrustLevelChanged = Signal()

    def __init__(self, comms: CommunicationManager):
        super().__init__()
        self._comms = comms
        self._h_thrust1 = 0
        self._h_thrust2 = 0
        self._h_thrust3 = 0
        self._h_thrust4 = 0
        self._v_thrust1 = 0
        self._v_thrust2 = 0
        self._v_thrust3 = 0
        self._v_thrust4 = 0

        self._total_h_thrust = 0
        self._h_angle = 0

        self._timer = QTimer()
        self._timer.timeout.connect(self.update_thrust)
        self._timer.start(40)

    @Property(float, notify=thrustLevelChanged)
    def h_thrust1(self):
        return self._h_thrust1

    @Property(float, notify=thrustLevelChanged)
    def h_thrust2(self):
        return self._h_thrust2

    @Property(float, notify=thrustLevelChanged)
    def h_thrust3(self):
        return self._h_thrust3

    @Property(float, notify=thrustLevelChanged)
    def h_thrust4(self):
        return self._h_thrust4

    @Property(float, notify=thrustLevelChanged)
    def v_thrust1(self):
        return self._v_thrust1

    @Property(float, notify=thrustLevelChanged)
    def v_thrust2(self):
        return self._v_thrust2

    @Property(float, notify=thrustLevelChanged)
    def v_thrust3(self):
        return self._v_thrust3

    @Property(float, notify=thrustLevelChanged)
    def v_thrust4(self):
        return self._v_thrust4

    @Property(float, notify=thrustLevelChanged)
    def totalHorizontalThrust(self):
        return self._total_h_thrust

    @Property(float, notify=thrustLevelChanged)
    def horizontalAngle(self):
        return self._h_angle

    def calc_direction(self):
        x_total = self._h_thrust1 / math.sqrt(2)
        y_total = self._h_thrust1 / math.sqrt(2)
        x_total = x_total - self._h_thrust2 / math.sqrt(2)
        y_total = y_total + self._h_thrust2 / math.sqrt(2)
        x_total = x_total - self._h_thrust3 / math.sqrt(2)
        y_total = y_total + self._h_thrust3 / math.sqrt(2)
        x_total = x_total + self._h_thrust4 / math.sqrt(2)
        y_total = y_total + self._h_thrust4 / math.sqrt(2)

        self._total_h_thrust = math.sqrt(x_total**2 + y_total**2)
        self._h_angle = math.atan2(y_total, x_total) * 180 / math.pi

    @Slot()
    def update_thrust(self):
        model = self._comms.sensor_cache
        new_thrust1 = model.thrusters[0]
        new_thrust2 = model.thrusters[1]
        new_thrust3 = model.thrusters[2]
        new_thrust4 = model.thrusters[3]
        new_thrust5 = model.thrusters[4]
        new_thrust6 = model.thrusters[5]
        new_thrust7 = model.thrusters[6]
        new_thrust8 = model.thrusters[7]

        changed = False
        if self._h_thrust1 != new_thrust1:
            self._h_thrust1 = new_thrust1
            changed = True
        if self._h_thrust2 != new_thrust2:
            self._h_thrust2 = new_thrust2
            changed = True
        if self._h_thrust3 != new_thrust3:
            self._h_thrust3 = new_thrust3
            changed = True
        if self._h_thrust4 != new_thrust4:
            self._h_thrust4 = new_thrust4
            changed = True
        if self._v_thrust1 != new_thrust5:
            self._v_thrust1 = new_thrust5
            changed = True
        if self._v_thrust2 != new_thrust6:
            self._v_thrust2 = new_thrust6
            changed = True
        if self._v_thrust3 != new_thrust7:
            self._v_thrust3 = new_thrust7
            changed = True
        if self._v_thrust4 != new_thrust8:
            self._v_thrust4 = new_thrust8
            changed = True
        if changed:
            self.calc_direction()
            self.thrustLevelChanged.emit()

    def stop_timer(self):
        self._timer.stop()

    def start_timer(self):
        self._timer.start(40)

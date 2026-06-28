from PySide6.QtCore import QTimer, Slot, QObject, Property, Signal

import random

from console.comms.manager import CommunicationManager


class OrientationData(QObject):
    orientation_changed = Signal()

    def __init__(self, comms: CommunicationManager):
        super().__init__()
        self._comms = comms

        self._bearing = 0
        self._pitch = 0
        self._roll = 0
        self._depth = 0

        self._max_depth = 5
        self._pitchFOV = 90  # (+/- 45 degrees)

        self._timer = QTimer()
        self._timer.timeout.connect(self.update_orientation)
        self._timer.start(15)

    # This 'Property' is what QML "binds" to
    @Property(float, notify=orientation_changed)
    def bearing(self):
        return self._bearing

    @Property(float, notify=orientation_changed)
    def pitch(self):
        return self._pitch

    @Property(float, notify=orientation_changed)
    def roll(self):
        return self._roll

    @Property(float, notify=orientation_changed)
    def depth(self):
        return self._depth

    @Property(float, notify=orientation_changed)
    def max_depth(self):
        return self._max_depth

    @Property(float, notify=orientation_changed)
    def pitchFOV(self):
        return self._pitchFOV

    @Slot()
    def update_orientation(self):
        model = self._comms.sensor_cache
        new_bearing = model.yaw
        if self._bearing != new_bearing:
            self._bearing = new_bearing
        new_pitch = model.pitch
        if self._pitch != new_pitch:
            self._pitch = new_pitch
        new_roll = model.roll
        if self._roll != new_roll:
            self._roll = new_roll
        new_depth = model.depth
        if self._depth != new_depth:
            self._depth = new_depth
        self.orientation_changed.emit()

    def stop_timer(self):
        self._timer.stop()

    def start_timer(self):
        self._timer.start(15)

from PySide6.QtCore import QTimer, Slot, QObject, Property, Signal

from console.gui.model.sensors import Sensors

class OrientationData(QObject):
    bearingChanged = Signal()
    pitchChanged = Signal()
    rollChanged = Signal()
    pitchFOVChanged = Signal()

    def __init__(self, model: Sensors):
        super().__init__()
        self._model = model
        self._bearing = 0
        self._pitch = 0
        self._roll = 0
        self._pitchFOV = 90 # (+/- 45 degrees)

        self._timer = QTimer()
        self._timer.timeout.connect(self.update_orientation)
        self._timer.start(40)

    # This 'Property' is what QML "binds" to
    @Property(float, notify=bearingChanged)
    def bearing(self):
        return self._bearing

    @Property(float, notify=pitchChanged)
    def pitch(self):
        return self._pitch

    @Property(float, notify=rollChanged)
    def roll(self):
        return self._roll
    
    @Property(float, notify=pitchFOVChanged)
    def pitchFOV(self):
        return self._pitchFOV

    @Slot()
    def update_orientation(self):
        new_bearing = self._model.yaw
        if self._bearing != new_bearing:
            self._bearing = new_bearing
            self.bearingChanged.emit() # This tells QML to refresh!
        new_pitch = self._model.pitch
        if self._pitch != new_pitch:
            self._pitch = new_pitch
            self.pitchChanged.emit()
        new_roll = self._model.roll
        if self._roll != new_roll:
            self._roll = new_roll
            self.rollChanged.emit()

    def stop_timer(self):
        self._timer.stop()

    def start_timer(self):
        self._timer.start(40)
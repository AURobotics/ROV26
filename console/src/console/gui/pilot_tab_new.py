from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy
from console.gui.camera_display import CameraDisplay
from console.gui.leakage_display import LeakageDisplay
from console.gui.model.orientation_data import OrientationData
from console.gui.model.sensors import Sensors
from console.gui.model.thruster_status import ThrusterStatus
from console.gui.status_widget import StatusWidget

class PilotTab2(QWidget):
    def __init__(self, cam1,cam2,cam3, comms):
        super().__init__()

        self._comms = comms

        self._vLayout = QVBoxLayout(self)

        #1. Camera Displays
        self._cam_layout = QHBoxLayout()
        self.camera1 = CameraDisplay(cam1)
        self.camera2 = CameraDisplay(cam2)
        self.camera3 = CameraDisplay(cam3)
        self.camera1.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.camera2.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.camera3.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._cam_layout.addWidget(self.camera1, stretch=1)
        self._cam_layout.addWidget(self.camera2, stretch=1)
        self._cam_layout.addWidget(self.camera3, stretch=1)

        self._vLayout.addLayout(self._cam_layout, stretch=1)

        #2. Bottom Widgets
        self._widget_layout = QHBoxLayout()

        #2.1 Leakage
        self.leakage_widget = LeakageDisplay()
        self.leakage_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._widget_layout.addWidget(self.leakage_widget, stretch=0)

        #2.2 Thrusters
        self.thruster_layout_widget = StatusWidget(ThrusterStatus(Sensors(self._comms)), "thrusterLayout.qml")
        self.thruster_layout_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._widget_layout.addWidget(self.thruster_layout_widget, stretch=0)

        #2.3 Depth
        self.depth_widget = StatusWidget(OrientationData(Sensors(self._comms)), "depth.qml")
        self.depth_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._widget_layout.addWidget(self.depth_widget, stretch=0)


        #2.4 Orientation
        self._orientation_layout = QVBoxLayout()
        self.compass_widget = StatusWidget(OrientationData(Sensors(self._comms)), "compassWidget.qml")
        self.pitch_roll_widget = StatusWidget(OrientationData(Sensors(self._comms)), "pitchRoll.qml")
        self.compass_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.pitch_roll_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._orientation_layout.addWidget(self.compass_widget, stretch=0)
        self._orientation_layout.addWidget(self.pitch_roll_widget, stretch=0)

        self._widget_layout.addLayout(self._orientation_layout, stretch=0)

        self._vLayout.addLayout(self._widget_layout, stretch=2)
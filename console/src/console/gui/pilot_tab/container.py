from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QMainWindow,
    QDockWidget,
)
from PySide6.QtCore import Qt

from console.comms.manager import CommunicationManager
from console.gui.common.camera_display import CameraDisplay
from console.gui.common.tab import GuiTab
from console.gui.pilot_tab.leakage_display import LeakageDisplay
from console.gui.model.orientation_data import OrientationData
from console.gui.model.thruster_status import ThrusterStatus
from console.gui.pilot_tab.status_widget import StatusWidget
from console.gui.pilot_tab.auto_control_input import AutoControlInput


class PilotTab(GuiTab):
    def __init__(self, cam1, cam2, cam3, comms: CommunicationManager):
        super().__init__()
        self._comms = comms

        # 1. Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 2. Inner Dock Host
        self.dock_host = QMainWindow()
        self.dock_host.setWindowFlags(Qt.WindowType.Widget)
        self.dock_host.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.GroupedDragging
            | QMainWindow.DockOption.VerticalTabs
        )
        self.main_layout.addWidget(self.dock_host)

        # 3. Central Widget (Fixed Cameras)
        self.camera_container = QWidget()
        self._cam_layout = QHBoxLayout(self.camera_container)

        self.camera1 = CameraDisplay(cam1)
        self.camera2 = CameraDisplay(cam2)
        self.camera3 = CameraDisplay(cam3)

        for cam in [self.camera1, self.camera2, self.camera3]:
            cam.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
            )
            self._cam_layout.addWidget(cam, stretch=1)
            cam._view.setScaledContents(True)

        self.dock_host.setCentralWidget(self.camera_container)

        # 4. Initialize and Position Docks
        self._setup_docks()

    def _setup_docks(self):
        self.dock_host.setCorner(
            Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea
        )

        # 4.1 Create the actual instances of your widgets
        self.leakage_widget = LeakageDisplay(self._comms)
        self.thruster_layout_widget = StatusWidget(
            ThrusterStatus(self._comms), "thrusterLayout.qml"
        )
        self.depth_widget = StatusWidget(OrientationData(self._comms), "depth.qml")
        self.compass_widget = StatusWidget(
            OrientationData(self._comms), "compassWidget.qml"
        )
        self.pitch_roll_widget = StatusWidget(
            OrientationData(self._comms), "pitchRoll.qml"
        )
        self.auto_input_widget = AutoControlInput(self._comms)

        # 4.2 Wrap them in Docks
        self.leak_dock = self._create_dock("Leakage", self.leakage_widget)
        self.thruster_dock = self._create_dock("Thrusters", self.thruster_layout_widget)
        self.depth_dock = self._create_dock("Depth", self.depth_widget)
        self.compass_dock = self._create_dock("Compass", self.compass_widget)
        self.pitch_dock = self._create_dock("Pitch/Roll", self.pitch_roll_widget)
        self.auto_input_dock = self._create_dock(
            "Automatic Control", self.auto_input_widget
        )

        # 4.3 Initial Layout Positioning
        self.dock_host.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea, self.auto_input_dock
        )

        self.dock_host.splitDockWidget(
            self.auto_input_dock, self.thruster_dock, Qt.Orientation.Horizontal
        )

        self.dock_host.splitDockWidget(
            self.thruster_dock, self.depth_dock, Qt.Orientation.Horizontal
        )

        self.dock_host.splitDockWidget(
            self.depth_dock, self.compass_dock, Qt.Orientation.Horizontal
        )

        self.dock_host.splitDockWidget(
            self.depth_dock, self.leak_dock, Qt.Orientation.Vertical
        )

        self.dock_host.splitDockWidget(
            self.compass_dock, self.pitch_dock, Qt.Orientation.Horizontal
        )

    def _create_dock(self, title, widget):
        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        return dock

    def hideEvent(self, event):
        super().hideEvent(event)
        for dock in self.findChildren(QDockWidget):
            if dock.isFloating():
                dock.hide()

    def showEvent(self, event):
        super().showEvent(event)
        for dock in self.findChildren(QDockWidget):
            if dock.isFloating():
                dock.show()

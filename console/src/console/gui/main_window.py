from PySide6.QtWidgets import QMainWindow
from console.core.comms.comms import CommunicationManager
from console.core.comms.stm32 import STM32
from console.core.gamepad import Controller
from console.core.vision.camera import VideoStream
from console.gui.menubar import MenuBar
from console.gui.model.sensors import Sensors
from console.gui.model.orientation_data import OrientationData
from console.gui.model.thruster_status import ThrusterStatus
from console.gui.pilot_tab import PilotTab
from console.gui.status_widget import StatusWidget


class MainWindow(QMainWindow):
    def __init__(self, serial_device, gamepad, comms):
        super().__init__()

        self.setWindowTitle("ROV Console")

        menubar = MenuBar(self, gamepad, serial_device)
        self.setMenuBar(menubar)
        self.camera = VideoStream('test.sdp')

        self.pilot_tab = PilotTab(self.camera, self.camera, self.camera)

        self.setCentralWidget(self.pilot_tab)

        self.pitch_roll_widget = StatusWidget(
            OrientationData(Sensors(comms)), "pitch_roll"
        )
        self.pilot_tab.grid_layout.addWidget(self.pitch_roll_widget, 1, 2)
        self.thruster_layout_widget = StatusWidget(
            ThrusterStatus(Sensors(comms)), "thruster_layout"
        )
        self.pilot_tab.grid_layout.addWidget(self.thruster_layout_widget, 1, 1)
        self.compass_widget = StatusWidget(OrientationData(Sensors(comms)), "compass")
        self.pilot_tab.grid_layout.addWidget(self.compass_widget, 1, 0)

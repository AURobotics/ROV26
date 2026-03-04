from PySide6.QtWidgets import QMainWindow, QTabWidget
from console.core.comms.comms import CommunicationManager
from console.core.comms.stm32 import STM32
from console.core.gamepad import Controller
from console.core.vision.camera import VideoStream
from console.gui.menubar import MenuBar
from console.gui.model.sensors import Sensors
from console.gui.pilot_tab import PilotTab
from console.gui.pitch_roll import PitchRollWidget
from console.gui.thruster_layout import ThrusterLayoutWidget
from console.gui.compass import CompassWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("ROV Console")

        self._controller = Controller()
        self._stm = STM32(baudrate=115200)

        menubar = MenuBar(self, self._controller, self._stm)
        self.setMenuBar(menubar)

        self._comms = CommunicationManager(self._stm, self._controller)

        self.camera = VideoStream(0)
        
        self.pilot_tab = PilotTab(self.camera, self.camera, self.camera)

        self.setCentralWidget(self.pilot_tab)

        #Temporary addition of 2 widgets
        self.pitch_roll_widget = PitchRollWidget(Sensors(self._comms))
        self.pilot_tab.grid_layout.addWidget(self.pitch_roll_widget, 1, 2)
        self.thruster_layout_widget = ThrusterLayoutWidget(Sensors(self._comms))
        self.pilot_tab.grid_layout.addWidget(self.thruster_layout_widget, 1, 1)
        self.compass_widget = CompassWidget(Sensors(self._comms))
        self.pilot_tab.grid_layout.addWidget(self.compass_widget, 1, 0)

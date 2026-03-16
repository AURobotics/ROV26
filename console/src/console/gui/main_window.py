from PySide6.QtWidgets import QMainWindow, QTabWidget
from console.core.comms.comms import CommunicationManager
from console.core.comms.stm32 import STM32
from console.core.gamepad import Controller
from console.core.vision.camera import VideoStream
from console.gui.menubar import MenuBar
from console.gui.pilot_tab_new import PilotTab2   # Change to PilotTab when ready
from console.gui.status_widget import StatusWidget

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
        
        self.pilot_tab = PilotTab2(self.camera, self.camera, self.camera, self._comms)  # Pass the same camera for now, replace with actual cameras when available

        self.setCentralWidget(self.pilot_tab)
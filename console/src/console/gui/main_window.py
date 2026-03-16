from PySide6.QtWidgets import QMainWindow
from console.core.comms.comms import CommunicationManager
from console.core.comms.stm32 import STM32
from console.core.gamepad import Controller
from console.core.vision.camera import VideoStream
from console.gui.menubar import MenuBar
from console.gui.pilot_tab_new import PilotTab
from console.gui.status_widget import StatusWidget


class MainWindow(QMainWindow):
    def __init__(self, serial_device, gamepad, comms):
        super().__init__()

        self.setWindowTitle("ROV Console")

        menubar = MenuBar(self, gamepad, serial_device)
        self.setMenuBar(menubar)
        self.camera = VideoStream('test.sdp')

        self._comms = CommunicationManager(self._stm, self._controller)

        self.camera = VideoStream(0)
        
        self.pilot_tab = PilotTab2(self.camera, self.camera, self.camera, self._comms)  # Pass the same camera for now, replace with actual cameras when available

        self.setCentralWidget(self.pilot_tab)

from PySide6.QtWidgets import QMainWindow
from console.core.comms.comms import CommunicationManager
from console.core.comms.stm32 import STM32
from console.core.gamepad import Controller
from console.core.vision.camera import VideoStream
from console.gui.menubar import MenuBar
from console.gui.pilot_tab_new import PilotTab2
from console.gui.status_widget import StatusWidget


class MainWindow(QMainWindow):
    def __init__(self, serial_device, gamepad, comms):
        super().__init__()

        self.setWindowTitle("ROV Console")

        menubar = MenuBar(self, gamepad, serial_device)
        self.setMenuBar(menubar)
        cam1 = VideoStream('cam1.sdp')
        cam2 = VideoStream('cam2.sdp')
        cam3 = VideoStream('cam3.sdp')

        self._comms = CommunicationManager(serial_device, gamepad)
        
        self.pilot_tab = PilotTab2(cam1, cam2, cam3, self._comms)  # Pass the same camera for now, replace with actual cameras when available

        self.setCentralWidget(self.pilot_tab)

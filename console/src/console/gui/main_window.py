from PySide6.QtWidgets import QMainWindow
from console.core.vision.camera import VideoStream
from console.gui.menubar import MenuBar
from lib.joystick.active_joystick import ActiveJoystick
from console.gui.pilot_tab_new import PilotTab2


class MainWindow(QMainWindow):
    def __init__(self, serial_device, active_joystick: ActiveJoystick, comms):
        super().__init__()

        self.setWindowTitle("ROV Console")

        menubar = MenuBar(self, active_joystick, serial_device)
        self.setMenuBar(menubar)
        ports = [5000, 5002, 5004]
        pipelines = [
            f"udpsrc address=239.1.1.1 port={port} ! "
            "application/x-rtp, payload=96 ! "
            "rtph264depay ! "
            "h264parse ! "
            "avdec_h264 ! "
            "videoconvert ! "
            "appsink" for port in ports
        ]
        cam1 = VideoStream(pipelines[0])
        cam2 = VideoStream(pipelines[1])
        cam3 = VideoStream(pipelines[2])

        
        self.pilot_tab = PilotTab2(cam1, cam2, cam3, comms)

        self.setCentralWidget(self.pilot_tab)

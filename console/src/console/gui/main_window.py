from PySide6.QtWidgets import QMainWindow
# from console.core.vision.camera import VideoStream
from console.gui.menubar import MenuBar
from console.core.active_joystick import ActiveJoystick
# from console.gui.pilot_tab_new import PilotTab2


class MainWindow(QMainWindow):
    def __init__(self, serial_device, active_joystick: ActiveJoystick, comms):
        super().__init__()

        self.setWindowTitle("ROV Console")

        menubar = MenuBar(self, active_joystick, serial_device)
        self.setMenuBar(menubar)
        pipeline = (
            "udpsrc address=239.1.1.1 port=5000 ! "
            "application/x-rtp, payload=96 ! "
            "rtph264depay ! "
            "h264parse ! "
            "avdec_h264 ! "
            "videoconvert ! "
            "appsink"
        )
        # cam1 = VideoStream(pipeline)
        # cam2 = VideoStream(pipeline)
        # cam3 = VideoStream(pipeline)

        
        # self.pilot_tab = PilotTab2(cam1, cam2, cam3, comms)

        # self.setCentralWidget(self.pilot_tab)

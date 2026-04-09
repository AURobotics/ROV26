from PySide6.QtWidgets import QMainWindow, QStackedWidget, QToolBar
from PySide6.QtCore import Qt
from PySide6.QtGui import QActionGroup, QAction
from console.core.vision.camera import VideoStream
from console.gui.menubar import MenuBar
from hal.joystick.active_joystick import ActiveJoystick
from console.gui.pilot_tab_new import PilotTab2
from console.gui.cv_tab import CVTab


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

        self._stack = QStackedWidget()
        
        self._pilot_tab = PilotTab2(cam1, cam2, cam3, comms)
        self._cv_tab = CVTab()

        self._stack.addWidget(self._pilot_tab)
        self._stack.addWidget(self._cv_tab)

        self.setCentralWidget(self._stack)

        self._toolbar = QToolBar()
        self._toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self._toolbar)

        self._group = QActionGroup(self)
        self._group.setExclusive(True)

        for i, name in enumerate(["Pilot", "CV"]):
            self._setup_action(i, name)

    def _setup_action(self, idx, name):
        action = QAction(name, self, checkable=True)
        action.setData(idx)
        self._group.addAction(action)
        self._toolbar.addAction(action)
        action.triggered.connect(lambda _:self._stack.setCurrentIndex(action.data()))
        if idx == 0:
            action.setChecked(True)
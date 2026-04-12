from PySide6.QtWidgets import QMainWindow
from hal.camera.camera import VideoStream
from console.gui.menubar import MenuBar
from hal.joystick.active_joystick import ActiveJoystick
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

        
        self._pilot_tab = PilotTab2(cam1, cam2, cam3, comms)
        self._cv_tab = CVTab()
        self._float_tab = FloatTab()

        self._stack.addWidget(self._pilot_tab)
        self._stack.addWidget(self._cv_tab)
        self._stack.addWidget(self._float_tab)

        self.setCentralWidget(self._stack)

        self._sidebar = QToolBar()
        self._sidebar.setMovable(False)
        self._sidebar.setStyleSheet("""
            QToolBar {
                background-color: #2b2b2b;
                border-right: 1px solid #444444;
                spacing: 10px;
                padding: 5px;
            }

            QToolButton {
                color: white;
                width: 24px;
                background-color: transparent;
                border-radius: 4px;
                padding: 8px;
            }
            
            QToolButton:hover {
                background-color: #3d3d3d;
            }

            QToolButton:checked {
                background-color: #0078d7;
                font-weight: bold;
            }
        """)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self._sidebar)

        self._sidebar_actions = QActionGroup(self)
        self._sidebar_actions.setExclusive(True)

        for i, name in enumerate(["Pilot", "CV", "Float"]):
            self._setup_action(i, name)

    def _setup_action(self, idx, name):
        action = QAction(name, self, checkable=True)
        action.setData(idx)
        self._sidebar_actions.addAction(action)
        self._sidebar.addAction(action)
        action.triggered.connect(lambda _:self._stack.setCurrentIndex(action.data()))
        if idx == 0:
            action.setChecked(True)
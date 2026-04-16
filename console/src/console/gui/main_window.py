from typing import cast

from PySide6.QtWidgets import (
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QToolBar,
    QWidget,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QActionGroup, QAction, QIcon
from console.assets import get_asset
from console.comms.stm32 import Stm32
from console.gui.common.tab import GuiTab
from console.gui.joystick_tab.container import JoystickTab
from console.gui.serial_tab import SerialTab
from console.gui.settings_tab.container import SettingsTab
from hal.camera.camera import VideoStream
from hal.joystick.active_joystick import ActiveJoystick
from console.gui.pilot_tab import PilotTab
from console.gui.cv_tab import CVTab


class MainWindow(QMainWindow):
    def __init__(self, stm: Stm32, active_joystick: ActiveJoystick, comms):
        super().__init__()

        self.setWindowTitle("ROV Console")
        ports = [5000, 5002, 5004]
        pipelines = [
            f"udpsrc address=239.1.1.1 port={port} ! "
            "application/x-rtp, payload=96 ! "
            "rtph264depay ! "
            "h264parse ! "
            "avdec_h264 ! "
            "videoconvert ! "
            "appsink"
            for port in ports
        ]
        cam1 = VideoStream(pipelines[0])
        cam2 = VideoStream(pipelines[1])
        cam3 = VideoStream(pipelines[2])

        self._stack = QStackedWidget()

        self._pilot_tab = PilotTab(cam1, cam2, cam3, comms)
        self._cv_tab = CVTab(cam1)
        self._serial_tab = SerialTab(stm)
        self._joystick_tab = JoystickTab(active_joystick)
        self._settings_tab = SettingsTab()

        self._stack.addWidget(self._pilot_tab)
        self._stack.addWidget(self._cv_tab)
        self._stack.addWidget(self._serial_tab)
        self._stack.addWidget(self._joystick_tab)
        self._stack.addWidget(self._settings_tab)

        self.setCentralWidget(self._stack)

        self._toolbar = QToolBar()
        self._toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self._toolbar)

        self._group = QActionGroup(self)
        self._group.setExclusive(True)

        for i, name in enumerate(["Pilot", "Crab", "Serial", "Joystick", "Settings"]):
            self._setup_action(i, name)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self._toolbar.insertWidget(self._toolbar.actions()[-1], spacer)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        hide_action = self._toolbar.toggleViewAction()
        hide_action.setText("Hide sidebar")
        hide_action.setShortcut("Ctrl+B")
        hide_action.triggered.connect(
            lambda: hide_action.setText(
                f"{'Show' if self._toolbar.isHidden() else 'Hide'} sidebar"
            )
        )
        self._toolbar.setToolTip("Toggle visibility with Ctrl+B")
        self.menuBar().addAction(hide_action)

    def _setup_action(self, idx, name):
        action = QAction(name, self, checkable=True)
        action.setData(idx)
        action.setIcon(QIcon(get_asset(f"tabs/{name}.svg")))
        self._group.addAction(action)
        self._toolbar.addAction(action)
        tab = self._stack.widget(idx)
        if tab:
            tab = cast(GuiTab, tab)
            tab.attention_needed.connect(
                lambda alert, a=action: a.setIcon(
                    QIcon(get_asset(f"tabs/{name + ('_alert' if alert else '')}.svg"))
                )
            )
            tab.attention_needed.emit(tab.needs_attention)
        action.triggered.connect(lambda _: self._stack.setCurrentIndex(action.data()))
        if idx == 0:
            action.setChecked(True)

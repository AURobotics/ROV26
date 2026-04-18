from typing import cast

from PySide6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStackedWidget,
    QToolBar,
    QWidget,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QActionGroup, QAction, QIcon
from console.assets import get_asset
from console.comms.stm32 import Stm32
from console.env import Settings
from console.gui.common.tab import GuiTab
from console.gui.joystick_tab.container import JoystickTab
from console.gui.serial_tab import SerialTab
from console.gui.settings_tab.container import SettingsTab
from hal.camera.camera import VideoStream
from hal.joystick.active_joystick import ActiveJoystick
from console.gui.pilot_tab import PilotTab
from console.gui.cv_tab import CvTab


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

        self.stack = QStackedWidget()

        pilot_tab = PilotTab(cam1, cam2, cam3, comms)
        cv_tab = CvTab(cam1)
        serial_tab = SerialTab(stm)
        joystick_tab = JoystickTab(active_joystick)
        settings_tab = SettingsTab()

        self.stack.addWidget(pilot_tab)
        self.stack.addWidget(cv_tab)
        self.stack.addWidget(serial_tab)
        self.stack.addWidget(joystick_tab)
        self.stack.addWidget(settings_tab)

        self.setCentralWidget(self.stack)

        self.sidebar = QToolBar()
        self.sidebar.setIconSize(QSize(24, 24))
        self.sidebar.setMovable(False)
        self.sidebar.setStyleSheet("""
            QToolBar {
                border-right: 1px solid #555555;
                spacing: 10px;
                padding: 5px;
            }

            QToolButton {
                color: white;
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
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.sidebar)

        self.sidebar_actions = QActionGroup(self)
        self.sidebar_actions.setExclusive(True)

        for i, name in enumerate(["Pilot", "Crab", "Serial", "Joystick", "Settings"]):
            self._setup_action(i, name)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.sidebar.insertWidget(self.sidebar.actions()[-1], spacer)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        hide_action = self.sidebar.toggleViewAction()
        hide_action.setText("Hide sidebar")
        hide_action.setShortcut("Ctrl+B")
        hide_action.triggered.connect(
            lambda: hide_action.setText(
                f"{'Show' if self.sidebar.isHidden() else 'Hide'} sidebar"
            )
        )
        self.sidebar.setToolTip("Toggle visibility with Ctrl+B")
        self.menuBar().addAction(hide_action)

    def _setup_action(self, idx, name):
        action = QAction(name, self, checkable=True)
        action.setData(idx)
        action.setIcon(QIcon(get_asset(f"tabs/{name}.svg")))
        self.sidebar_actions.addAction(action)
        self.sidebar.addAction(action)
        tab = self.stack.widget(idx)
        if tab:
            tab = cast(GuiTab, tab)
            tab.attention_needed.connect(
                lambda alert, a=action: a.setIcon(
                    QIcon(get_asset(f"tabs/{name + ('_alert' if alert else '')}.svg"))
                )
            )
            tab.attention_needed.emit(tab.needs_attention)
        action.triggered.connect(lambda _: self.stack.setCurrentIndex(action.data()))
        if idx == 0:
            action.setChecked(True)

    def initial_setup(self):
        reply = QMessageBox(
            QMessageBox.Icon.Question,
            "Initial Setup",
            "It looks like this is the first time you open the ROV console. Would you like to open the settings to finish any needed setup?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self,
            Qt.WindowType.Dialog
        ).exec()

        if reply == QMessageBox.StandardButton.Yes:
            settings_action = self.sidebar_actions.actions()[-1]
            settings_action.triggered.emit()
            settings_action.setChecked(True)

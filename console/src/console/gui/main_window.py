from PySide6.QtWidgets import QMainWindow, QWidget, QToolBar, QStatusBar, QLabel, QPushButton, QDockWidget, QVBoxLayout, QTabWidget
from PySide6.QtGui import QAction, QIcon
from console.gui.camera_display import Camera
from PySide6.QtCore import Qt
from console.gui.pilot_tab import PilotTab
from console.gui.copilot_tab import CoPilotTab
from console.gui.pitch_roll import PitchRollWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Main Window")
        
        tool_bar = QToolBar("Main ToolBar")
        self.addToolBar(tool_bar)
        connect_esp_action = QAction("Connect ESP", self)
        connect_esp_action.setStatusTip("Connect ESP to App")
        connect_esp_action.triggered.connect(self.connect_esp)
        tool_bar.addAction(connect_esp_action)

        connect_controller_action = QAction(QIcon("playstation-controller.webp"), "Connect Controller", self)
        connect_controller_action.setStatusTip("Connect Controller to App")
        connect_controller_action.triggered.connect(self.connect_controller)
        tool_bar.addAction(connect_controller_action)

        tool_bar.addSeparator()

        self.setStatusBar(QStatusBar(self))

        self.sidebar = QDockWidget("Controls", self)
        self.sidebar.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        #self.sidebar.resize(400, self.height())
        
        button1 = QPushButton("One")
        button2 = QPushButton("Two")
        label1 = QLabel("A Label")

        sidebar_layout = QVBoxLayout()
        sidebar_layout.addWidget(button1)
        sidebar_layout.addWidget(button2)
        sidebar_layout.addWidget(label1)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar_layout)

        self.sidebar.setWidget(sidebar_widget)

        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.sidebar)
        self.resizeDocks([self.sidebar], [250], Qt.Orientation.Horizontal)
        self.sidebar.hide()

        self.camera = Camera(0)
        
        self.pilot_tab = PilotTab(self.toggle_sidebar, self.camera, self.camera, self.camera)
        self.copilot_tab = CoPilotTab(self.toggle_sidebar, self.camera)

        tab_widget = QTabWidget()
        tab_widget.addTab(self.pilot_tab, "Pilot")
        tab_widget.addTab(self.copilot_tab, "Co-Pilot")

        self.setCentralWidget(tab_widget)

        #Temporary addition of the pitch-roll widget
        self.pitch_roll_widget = PitchRollWidget()
        self.pilot_tab.grid_layout.addWidget(self.pitch_roll_widget, 1, 2)


    def connect_esp(self):
        print("ESP Connected")

    def connect_controller(self):
        print("Controller Connected")

    def toggle_sidebar(self, checked):
        self.sidebar.setVisible(checked)
          
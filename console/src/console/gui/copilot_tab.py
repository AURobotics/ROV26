from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QLabel
from PySide6.QtGui import QPixmap
from gui.camera_display import CameraDisplay
from assets import get_asset

class CoPilotTab(QWidget):
    def __init__(self, toggle_sidebar, cam1):
        super().__init__()

        grid_layout = QGridLayout()

        self.camera1 = CameraDisplay(cam1)

        self.image1 = QLabel()
        self.image1.setPixmap(QPixmap(get_asset('pic.png')))

        self.sidebar_button = QPushButton("Control")
        self.sidebar_button.setCheckable(True)
        self.sidebar_button.clicked.connect(toggle_sidebar)

        grid_layout.addWidget(self.camera1,0,1)
        grid_layout.addWidget(self.image1,1,1)
        grid_layout.addWidget(self.sidebar_button,2,2)

        self.setLayout(grid_layout)
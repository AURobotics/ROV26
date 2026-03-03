from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QLabel
from PySide6.QtGui import QPixmap
from gui.camera_display import CameraDisplay

class PilotTab(QWidget):
    def __init__(self, toggle_sidebar, cam1,cam2,cam3):
        super().__init__()

        self.grid_layout = QGridLayout()

        self.camera1 = CameraDisplay(cam1)
        self.camera2 = CameraDisplay(cam2)
        self.camera3 = CameraDisplay(cam3)

        self.image1 = QLabel()
        self.image1.setPixmap(QPixmap("pic.png"))

        self.image2 = QLabel()
        self.image2.setPixmap(QPixmap("pic.png"))

        self.image3 = QLabel()
        self.image3.setPixmap(QPixmap("pic.png"))

        self.sidebar_button = QPushButton("Control")
        self.sidebar_button.setCheckable(True)
        self.sidebar_button.clicked.connect(toggle_sidebar)

        self.grid_layout.addWidget(self.camera1,0,0)
        self.grid_layout.addWidget(self.camera2,0,1)
        self.grid_layout.addWidget(self.camera3,0,2)
        self.grid_layout.addWidget(self.image1,1,0)
        self.grid_layout.addWidget(self.image2,1,1)
        self.grid_layout.addWidget(self.image3,1,2)
        self.grid_layout.addWidget(self.sidebar_button,2,2)

        self.setLayout(self.grid_layout)
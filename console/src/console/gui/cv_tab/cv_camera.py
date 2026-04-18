from PySide6.QtWidgets import QPushButton, QWidget, QHBoxLayout, QVBoxLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Signal
from console.gui.common.camera_display import CameraDisplay
from hal.camera.camera import VideoStream

class CVCamera(CameraDisplay):
    captureClicked = Signal(QPixmap)

    def __init__(self, camera_device: VideoStream, parent: QWidget | None = None):
        super().__init__(camera_device, parent)

        self._ovelay = QWidget(self)
        
        self._capture_btn = QPushButton("Capture")
        self._capture_btn.clicked.connect(self._capture_clicked)

        self._h_layout = QHBoxLayout(self._ovelay)
        self._h_layout.addWidget(QWidget(), 1) # Horizontal Spacer
        self._v_layout = QVBoxLayout()
        self._v_layout.addWidget(self._capture_btn)
        self._v_layout.addWidget(QWidget(), 1) # Vertical Spacer
        self._h_layout.addLayout(self._v_layout)

    def getPixmap(self) -> QPixmap | None:
        pixmap = self._frame_view.pixmap()
        if pixmap is not None:
            return pixmap.copy()
        return None
    
    def _capture_clicked(self):
        self.captureClicked.emit(self.getPixmap())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._ovelay.setGeometry(self.rect())
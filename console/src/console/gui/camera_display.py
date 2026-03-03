from PySide6.QtWidgets import QWidget, QLabel, QSizePolicy, QHBoxLayout, QPushButton
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QPixmap, QResizeEvent
from console.core.vision.camera import Camera
import cv2

class CameraDisplay(QWidget):
    def __init__(self, camera_device, parent: QWidget | None = None):
        super().__init__(parent)
        
        self._camera_device = camera_device
        self._rotation_angle = 0
        self._is_flipped_h = False
        self._is_flipped_v = False

        self._frame_view = QLabel(self)
        self._frame_view.setScaledContents(True)

        self.update_view()
        self._camera_timer = QTimer()
        self._camera_timer.timeout.connect(self.update_view)
        self._camera_timer.setInterval(50)
        self._camera_timer.start()


        self.overlay = QWidget(self)

        self.overlay_layout = QHBoxLayout()

        self.rotate_r = QPushButton("R")
        self.rotate_r.setToolTip("Rotate ClockWise")
        self.rotate_l = QPushButton("L")
        self.rotate_l.setToolTip("Rotate Anit-ClockWise")
        self.flipH = QPushButton("FH")
        self.flipH.setToolTip("Flip Horizontally")
        self.flipV = QPushButton("FV")
        self.flipV.setToolTip("Flip Vertically")
        

        self.overlay_layout.addWidget(self.rotate_r)
        self.overlay_layout.addWidget(self.rotate_l)
        self.overlay_layout.addWidget(self.flipH)
        self.overlay_layout.addWidget(self.flipV)

        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 100);")
        self.overlay.setLayout(self.overlay_layout)

        self.overlay.hide()

        self.rotate_l.clicked.connect(self.toggle_rotate_l)
        self.rotate_r.clicked.connect(self.toggle_rotate_r)
        self.flipH.clicked.connect(self.toggle_flipH)
        self.flipV.clicked.connect(self.toggle_flipV)


    def toggle_rotate_l(self):
        self._rotation_angle = (self._rotation_angle + 1) % 360
    def toggle_rotate_r(self):
        self._rotation_angle = (self._rotation_angle - 1) % 360
    def toggle_flipH(self):
        self._is_flipped_h = not self._is_flipped_h
    def toggle_flipV(self):
        self._is_flipped_v = not self._is_flipped_v

    
    def enterEvent(self, event):
        self.overlay.show()
        self.overlay.raise_()
        super().enterEvent(event)
    def leaveEvent(self, event):
        self.overlay.hide()
        super().leaveEvent(event)


    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._frame_view.resize(event.size())

        overlay_height = 35
        self.overlay.setGeometry(0, self.height() - overlay_height, self.width(), overlay_height)
        return

    def update_view(self):
        frame = self._camera_device.frame

        if self._is_flipped_h:
            frame = cv2.flip(frame, 1)
        if self._is_flipped_v:
            frame = cv2.flip(frame, 0)
        if self._rotation_angle != 0:
            (h, w) = frame.shape[:2]
            center = (w // 2, h // 2)
            
            matrix = cv2.getRotationMatrix2D(center, -self._rotation_angle, 1.0)
            
            frame = cv2.warpAffine(frame, matrix, (w, h))


        image = QImage(frame.data, frame.shape[1], frame.shape[0], frame.strides[0], QImage.Format.Format_BGR888)
        self._frame_view.setPixmap(QPixmap.fromImage(image))
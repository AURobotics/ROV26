from PySide6.QtWidgets import QWidget, QLabel, QSizePolicy
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QPixmap, QResizeEvent
from cv import Camera

class CameraDisplay(QWidget):
    def __init__(self, camera_device, parent: QWidget | None = None):
        super().__init__(parent)
        
        self._camera_device = camera_device

        self._frame_view = QLabel(self)
        self._frame_view.setScaledContents(True)

        self.update_view()
        self._camera_timer = QTimer()
        self._camera_timer.timeout.connect(self.update_view)
        self._camera_timer.setInterval(50)
        self._camera_timer.start()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._frame_view.resize(event.size())
        return

    def update_view(self):
        frame = self._camera_device.frame
        image = QImage(frame.data, frame.shape[1], frame.shape[0], frame.strides[0], QImage.Format.Format_BGR888)
        self._frame_view.setPixmap(QPixmap.fromImage(image))
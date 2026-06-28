from PySide6.QtWidgets import QPushButton, QWidget, QComboBox
from PySide6.QtWidgets import QPushButton, QWidget, QComboBox
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Signal
from console.gui.common.camera_display import CameraDisplay

aspect_ratio = 16/9

class CVCamera(QWidget):
    captureClicked = Signal(QPixmap)

    def __init__(self, *cams: CameraDisplay, parent: QWidget | None = None):
        super().__init__(parent)

        self._cams = [CameraDisplay(), CameraDisplay(), CameraDisplay()]
        for i, cam in enumerate(self._cams):
            cam._stream = cams[i]._stream
            cam._camera_selector._last_known_url = cams[i]._camera_selector._last_known_url
        self._frame_view = self._cams[0]
        self._frame_view.setParent(self)

        self._cam_menu = QComboBox(self)
        self._cam_menu.addItems(["Camera 1", "Camera 2", "Camera 3"])
        self._cam_menu.currentIndexChanged.connect(self._switch_camera)
        self._capture_btn = QPushButton("Capture", self)
        self._capture_btn.clicked.connect(self._capture_clicked)

        self._resize_widgets()
        self._resize_widgets()
    
    def _capture_clicked(self):
        self.captureClicked.emit(self._frame_view.getPixmap())

    def _switch_camera(self, index):
        self._frame_view.hide()
        self._frame_view = self._cams[index]
        self._frame_view.setParent(self)
        self._frame_view.show()
        self._cam_menu.raise_()
        self._capture_btn.raise_()
        self._resize_widgets()
        self.captureClicked.emit(self._frame_view.getPixmap())

    def _switch_camera(self, index):
        self._frame_view.hide()
        self._frame_view = self._cams[index]
        self._frame_view.setParent(self)
        self._frame_view.show()
        self._cam_menu.raise_()
        self._capture_btn.raise_()
        self._resize_widgets()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_widgets()

    def _resize_widgets(self):
        if self._frame_view.getPixmap() is not None:
            total_size = self.size()

            total_width = total_size.width()
            total_height = total_size.height()

            if total_width > total_height*aspect_ratio:
                new_width = int(total_height*aspect_ratio)
                new_height = total_height
            else:
                new_width = total_width
                new_height = int(total_width/aspect_ratio)

            x_offset = (total_width - new_width)//2
            y_offset = (total_height - new_height)//2

            self._frame_view.setGeometry(x_offset, y_offset, new_width, new_height)
            self._cam_menu.move(x_offset + 10, y_offset + 10)
            self._capture_btn.move(x_offset + new_width - self._capture_btn.width() - 10, y_offset + 10)
        self._resize_widgets()

    def _resize_widgets(self):
        if self._frame_view.getPixmap() is not None:
            total_size = self.size()

            total_width = total_size.width()
            total_height = total_size.height()

            if total_width > total_height*aspect_ratio:
                new_width = int(total_height*aspect_ratio)
                new_height = total_height
            else:
                new_width = total_width
                new_height = int(total_width/aspect_ratio)

            x_offset = (total_width - new_width)//2
            y_offset = (total_height - new_height)//2

            self._frame_view.setGeometry(x_offset, y_offset, new_width, new_height)
            self._cam_menu.move(x_offset + 10, y_offset + 10)
            self._capture_btn.move(x_offset + new_width - self._capture_btn.width() - 10, y_offset + 10)
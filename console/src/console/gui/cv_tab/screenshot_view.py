from PySide6.QtWidgets import QHBoxLayout, QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QPixmap, Qt
from PySide6.QtCore import Signal

aspect_ratio = 4/3

class ScreenshotView(QWidget):
    analysisClicked = Signal(QPixmap)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)

        self._screenshot_label = QLabel(self)
        self._screenshot_label.setScaledContents(True)
        self._screenshot_label.setMinimumSize(1, 1)
        self._screenshot_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._main_layout.addWidget(self._screenshot_label)

        self._overlay = QWidget(self)

        self._analyse_btn = QPushButton("Analyse")
        self._discard_btn = QPushButton("Discard")
        self._analyse_btn.clicked.connect(self._analysis_clicked)
        self._discard_btn.clicked.connect(self.hide)

        self._h_btn_layout = QHBoxLayout(self._overlay)
        self._h_btn_layout.addWidget(QWidget(), 1) # Horizontal Spacer
        self._v_btn_layout = QVBoxLayout()
        self._v_btn_layout.addWidget(QWidget(), 1) # Vertical Spacer
        self._v_btn_layout.addWidget(self._analyse_btn)
        self._v_btn_layout.addWidget(self._discard_btn)
        self._h_btn_layout.addLayout(self._v_btn_layout)

        self.hide()

    def _analysis_clicked(self):
        self.analysisClicked.emit(self.getPixmap())
        self.hide()

    def setPixmap(self, pixmap: QPixmap):
        self._screenshot_label.setPixmap(pixmap)
        self.updateGeometry()
        self.show()
        self._overlay.show()
        self._overlay.raise_()

    def getPixmap(self) -> QPixmap | None:
        pixmap = self._screenshot_label.pixmap()
        if pixmap is not None:
            return pixmap.copy()
        return None

    def hide(self):
        super().hide()
        self._overlay.hide()
        self._screenshot_label.clear()

    def sizeHint(self):
        return self._screenshot_label.sizeHint()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self._screenshot_label.pixmap() is not None:
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

            self._screenshot_label.setGeometry(x_offset, y_offset, new_width, new_height)
        self._overlay.setGeometry(self.rect())
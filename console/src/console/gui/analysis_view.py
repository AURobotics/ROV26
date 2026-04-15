from PySide6.QtWidgets import (
    QWidget,
    QSizePolicy,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QStackedLayout,
)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt
from console.core.relative_path import get_base_path
from ultralytics import YOLO
import numpy as np
import cv2

model = YOLO(get_base_path() / "models" / "crab-counting-v1.0.pt")


def count_crabs(frame):
    results = model(frame)
    counts = {"green crab": 0, "red crab": 0, "brown crab": 0}
    for r in results:
        for cls in r.boxes.cls:
            name = model.names[int(cls)]
            if name in counts:
                counts[name] += 1
    return (
        counts["green crab"],
        counts["red crab"],
        counts["brown crab"],
        results[0].plot(),
    )


def to_cv2(pixmap: QPixmap) -> np.ndarray:
    img = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
    arr = np.array(img.bits(), dtype=np.uint8).reshape((img.height(), img.width(), 3))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)


def to_pixmap(frame: np.ndarray) -> QPixmap:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    return QPixmap.fromImage(
        QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
    )


class AnalysisView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_pixmap: QPixmap | None = None
        self._displayed_pixmap: QPixmap | None = None
        self._last_counts = (0, 0, 0)
        self._build()
        self.setVisible(False)

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        container = QWidget()
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        stack = QStackedLayout(container)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self._frame_view = QLabel()
        self._frame_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._frame_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._frame_view.setStyleSheet("background: #111;")

        self._frame_view.setMinimumSize(1, 1)  # Allow shrinking to almost nothing
        self._frame_view.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored
        )
        stack.addWidget(self._frame_view)

        overlay = QWidget()
        overlay.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        ol = QVBoxLayout(overlay)
        ol.setContentsMargins(0, 0, 8, 8)
        ol.addStretch()
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)

        self._run_btn = QPushButton("▶ Run")
        self._accept_btn = QPushButton("✔ Accept")
        self._reject_btn = QPushButton("✘ Reject")
        self._accept_btn.setEnabled(False)

        for btn in (self._run_btn, self._accept_btn, self._reject_btn):
            btn.setFixedSize(90, 28)
            btn_col.addWidget(btn)

        btn_row.addLayout(btn_col)
        ol.addLayout(btn_row)
        stack.addWidget(overlay)
        stack.setCurrentIndex(1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(container)
        left_layout.setContentsMargins(8, 8, 8, 8)
        root.addWidget(left, stretch=3)

        self._sep = QFrame()
        self._sep.setFrameShape(QFrame.Shape.VLine)
        self._sep.setFrameShadow(QFrame.Shadow.Sunken)
        self._sep.setVisible(False)

        self._results = QWidget()
        self._results.setFixedWidth(200)
        self._results.setVisible(False)
        rl = QVBoxLayout(self._results)
        rl.setContentsMargins(16, 16, 16, 16)
        rl.setSpacing(12)

        title = QLabel("Detection Results")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        self._count_label = QLabel("Green Crabs: —")
        self._count_label.setStyleSheet("font-size: 14px;")
        undo_btn = QPushButton(" Undo Accept")
        undo_btn.clicked.connect(self._hide_results)

        rl.addWidget(title)
        rl.addWidget(self._count_label)
        rl.addStretch()
        rl.addWidget(undo_btn)

        root.addWidget(self._sep)
        root.addWidget(self._results)

        self._run_btn.clicked.connect(self._on_run)
        self._accept_btn.clicked.connect(self._on_accept)
        self._reject_btn.clicked.connect(self._on_reject)

    def receive_from_screenshot(self, pixmap: QPixmap):
        self._original_pixmap = pixmap
        self._show_pixmap(pixmap)
        self._accept_btn.setEnabled(False)
        self._hide_results()
        self.setVisible(True)

    def _on_run(self):
        if self._original_pixmap is None:
            return
        g, r, b, annotated = count_crabs(to_cv2(self._original_pixmap))
        self._last_counts = (g, r, b)
        self._show_pixmap(to_pixmap(annotated))
        self._accept_btn.setEnabled(True)

    def _on_accept(self):
        self._count_label.setText(f" Green Crabs: {self._last_counts[0]}")
        self._results.setVisible(True)
        self._sep.setVisible(True)

    def _on_reject(self):
        if self._original_pixmap:
            self._show_pixmap(self._original_pixmap)
        self._accept_btn.setEnabled(False)
        self._hide_results()
        self.setVisible(False)

    def _show_pixmap(self, pixmap: QPixmap):
        self._displayed_pixmap = pixmap  # store it
        self._rescale_pixmap()

    def _rescale_pixmap(self):
        if self._displayed_pixmap:
            self._frame_view.setPixmap(
                self._displayed_pixmap.scaled(
                    self._frame_view.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale_pixmap()

    def _hide_results(self):
        self._results.setVisible(False)
        self._sep.setVisible(False)

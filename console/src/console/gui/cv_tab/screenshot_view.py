import time
from typing import cast

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
)
from PySide6.QtGui import QPixmap, Qt
from PySide6.QtCore import Qt, Signal

from console.env import pathing


class ScreenshotItemWidget(QWidget):
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)

        self.thumbnail = QLabel()
        self.pixmap = pixmap
        pixmap = pixmap.scaled(
            120,
            80,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.thumbnail.setPixmap(pixmap)
        self.thumbnail.setFixedSize(120, 80)
        self.thumbnail.setStyleSheet("border: 1px solid #555; border-radius: 4px;")

        self.info_layout = QVBoxLayout()
        self.name_label = QLabel(f"Screenshot-{time.time_ns() // 1_000_000}")
        self.name_label.setStyleSheet("font-weight: bold; font-size: 14px;")

        self.info_layout.addWidget(self.name_label)

        layout.addWidget(self.thumbnail)
        layout.addLayout(self.info_layout)
        layout.addStretch()


class ScreenshotView(QWidget):
    analysis_clicked = Signal(QPixmap)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.list_view = QListWidget()
        self.list_view.itemSelectionChanged.connect(
            lambda: self.button_strip.setEnabled(bool(self.list_view.selectedItems()))
        )

        self.button_strip = QWidget()
        self.button_strip.setEnabled(False)
        strip_layout = QHBoxLayout(self.button_strip)
        strip_layout.setContentsMargins(5, 2, 5, 5)
        self.analysis_button = QPushButton("Analyze")
        self.save_button = QPushButton("Save")
        self.delete_button = QPushButton("Delete")
        self.analysis_button.clicked.connect(
            lambda: self.analysis_clicked.emit(self.get_selected_pixmap())
        )
        self.delete_button.clicked.connect(self.delete_selected)
        self.save_button.clicked.connect(self.save_selected)
        strip_layout.addWidget(self.analysis_button)
        strip_layout.addWidget(self.save_button)
        strip_layout.addWidget(self.delete_button)

        layout.addWidget(self.list_view)
        layout.addWidget(self.button_strip)

    def add_screenshot(self, pixmap: QPixmap):
        item = QListWidgetItem(self.list_view)
        item_wigdet = ScreenshotItemWidget(pixmap)
        item.setSizeHint(item_wigdet.sizeHint())
        self.list_view.setItemWidget(item, item_wigdet)

    def get_selected_pixmap(self) -> QPixmap | None:
        selected = self.list_view.selectedItems()
        if len(selected) == 0:
            return None
        widget = cast(ScreenshotItemWidget, self.list_view.itemWidget(selected[0]))
        return widget.pixmap.copy()

    def delete_selected(self) -> None:
        selected = self.list_view.currentRow()
        if selected == -1:
            return
        self.list_view.takeItem(selected)

    def save_selected(self) -> None:
        selected = self.list_view.selectedItems()
        if len(selected) == 0:
            return None
        widget = cast(ScreenshotItemWidget, self.list_view.itemWidget(selected[0]))
        pixmap = widget.pixmap.copy()
        file_path = QFileDialog.getSaveFileName(
            self,
            "Save Image",
            str(pathing.get_base_path()),
            "PNG Files (*.png)",
        )[0]

        if file_path:
            pixmap.save(file_path, "PNG")

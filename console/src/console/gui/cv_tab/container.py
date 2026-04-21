from typing import Any

from console.env import Settings
from console.gui.common.tab import GuiTab
from PySide6.QtWidgets import (
    QDockWidget,
    QMainWindow,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
    QWidget,
    QMainWindow,
    QSizePolicy,
    QDockWidget,
)
from PySide6.QtCore import Qt
from console.gui.cv_tab.cv_camera import CVCamera
from console.gui.cv_tab.analysis_view import AnalysisView
from console.gui.cv_tab.screenshot_view import ScreenshotView
from pathlib import Path


class CvTab(GuiTab):
    def __init__(self, cam1, cam2, cam3, parent: QWidget | None = None):
        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.Widget)
        self.dock_host = QMainWindow()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.dock_host)
        self.dock_host.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.GroupedDragging
            | QMainWindow.DockOption.VerticalTabs
        )

        self.dock_host.setCorner(
            Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea
        )

        self._cam = CVCamera(cam1, cam2, cam3)
        self._cam.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        self.dock_host.setCentralWidget(self._cam)

        self._analysis_view = AnalysisView()
        self._analysis_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._analysis_dock = self._create_dock("Analysis", self._analysis_view)
        self.dock_host.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea, self._analysis_dock
        )

        self._screenshot_view = ScreenshotView()
        self._screenshot_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._screenshot_dock = self._create_dock("Screenshots", self._screenshot_view)
        self.dock_host.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea,
            self._screenshot_dock,
        )
        self._accepted_screenshot_view = ScreenshotView()
        self._accepted_screenshot_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._accepted_screenshot_dock = self._create_dock("Accepted Screenshots", self._accepted_screenshot_view)
        self.dock_host.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea,
            self._accepted_screenshot_dock,
        )

        self._cam.captureClicked.connect(self._screenshot_view.add_screenshot)
        self._screenshot_view.analysis_clicked.connect(
            self._analysis_view.receive_from_screenshot
        )
        self._analysis_view._on_accept
        model_path = Path(Settings().get("cv/model"))
        if model_path.exists():
            self._analysis_view.load_model(model_path)

    def _create_dock(self, title, widget):
        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        return dock

    def on_settings_changed(self, key: str, value: Any) -> None:
        if key != "cv/model":
            return
        path = Path(value)
        self._analysis_view.load_model(path)

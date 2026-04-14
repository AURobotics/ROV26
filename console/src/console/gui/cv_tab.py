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
from console.gui.camera_display import CameraDisplay
from console.gui.analysis_view import AnalysisView


class CVTab(GuiTab):
    # Placeholder for CVTab implementation
    def __init__(self, cam, parent: QWidget | None = None):
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

        self._cam = CameraDisplay(cam)
        self._cam.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred
        )
        self.dock_host.setCentralWidget(self._cam)

        self._analysis_view = AnalysisView()  # Placeholder for analysis view
        self._analysis_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._analysis_dock = self._create_dock("Analysis", self._analysis_view)
        self.dock_host.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea, self._analysis_dock
        )

        self._screenshot_view = QWidget()  # Placeholder for screenshot view
        self._screenshot_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._screenshot_dock = self._create_dock("Screenshots", self._screenshot_view)
        self.dock_host.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea, self._screenshot_dock
        )

    def _create_dock(self, title, widget):
        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        return dock

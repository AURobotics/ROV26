from PySide6.QtWidgets import QDockWidget, QMainWindow, QSizePolicy, QWidget
from PySide6.QtCore import Qt

from console.gui.camera_display import CameraDisplay

class CVTab(QMainWindow):
    # Placeholder for CVTab implementation
    def __init__(self, cam, parent: QWidget | None = None):
        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.Widget)
        self.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks
            | QMainWindow.DockOption.AnimatedDocks
            | QMainWindow.DockOption.AllowTabbedDocks
            | QMainWindow.DockOption.GroupedDragging
            | QMainWindow.DockOption.VerticalTabs
        )

        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)

        self._cam = CameraDisplay(cam)
        self._cam.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self.setCentralWidget(self._cam)

        self._analysis_view = QWidget()  # Placeholder for analysis view
        self._analysis_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._analysis_dock = self._create_dock("Analysis", self._analysis_view)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._analysis_dock)

        self._screenshot_view = QWidget()  # Placeholder for screenshot view
        self._screenshot_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._screenshot_dock = self._create_dock("Screenshots", self._screenshot_view)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._screenshot_dock)


    def _create_dock(self, title, widget):
        dock = QDockWidget(title, self)
        dock.setWidget(widget)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        return dock
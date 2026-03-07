from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtCore import QUrl, Qt
from console.assets import get_asset

class StatusWidget(QWidget):
    def __init__(self, data_bridge, widget_type: str, parent: QWidget | None = None):
        super().__init__(parent)

        self._data_bridge = data_bridge

        self._layout = QVBoxLayout(self)
        self._view = QQuickWidget()
        #self._view.setClearColor(Qt.GlobalColor.transparent)
        
        # 2. Pass the OBJECT, not just a number
        self._view.rootContext().setContextProperty("rov", self._data_bridge)
        
        if widget_type.lower() == "pitch_roll":
            self._view.setSource(QUrl.fromLocalFile(get_asset("pitchRoll.qml")))
        elif widget_type.lower() == "compass":
            self._view.setSource(QUrl.fromLocalFile(get_asset("compassWidget.qml")))
        elif widget_type.lower() == "thruster_layout":
            self._view.setSource(QUrl.fromLocalFile(get_asset("thrusterLayout.qml")))
        else:
            raise ValueError(f"Unknown widget type: {widget_type}")
        
        self._view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._layout.addWidget(self._view)

    def hideEvent(self, event):
        self._data_bridge.stop_timer()
        super().hideEvent(event)

    def showEvent(self, event):
        self._data_bridge.start_timer()
        super().showEvent(event)
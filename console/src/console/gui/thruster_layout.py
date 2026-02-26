from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtCore import QUrl
from console.assets import get_asset
from console.gui.model.thruster_status import ThrusterStatus

class ThrusterLayoutWidget(QWidget):
    def __init__(self):
        super().__init__()

        self.data_bridge = ThrusterStatus()

        self._layout = QVBoxLayout(self)
        self._view = QQuickWidget()
        #self._view.setClearColor(Qt.GlobalColor.transparent)
        
        # 2. Pass the OBJECT, not just a number
        self._view.rootContext().setContextProperty("rov", self.data_bridge)
        
        self._view.setSource(QUrl.fromLocalFile(get_asset("thrusterLayout.qml")))
        self._view.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self._layout.addWidget(self._view)
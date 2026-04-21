from PySide6.QtWidgets import (
    QGroupBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from console.env import Settings
from console.env.third_party import (
    CrabDetectionModelDownloader,
    StmProgrammerDownloader,
    VirtualHereClientDownloader,
)
from console.gui.common.combobox import QShowEvent
from console.gui.common.tab import GuiTab
from console.gui.settings_tab.file_setting import FileSetting


class SettingsTab(GuiTab):
    def __init__(self):
        super().__init__()

        self.settings = Settings()
        main_layout = QVBoxLayout(self)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        main_layout.addWidget(container)

        scrollable = QScrollArea()
        scrollable.setWidgetResizable(True)

        vh_grp = QGroupBox()
        vh_grp.setTitle("VirtualHere Client")
        vh_layout = QVBoxLayout(vh_grp)
        self.vh_widget = FileSetting(VirtualHereClientDownloader, "stm/vhusb", "exe")
        vh_layout.addWidget(self.vh_widget)

        prog_grp = QGroupBox()
        prog_grp.setTitle("STM Programmer")
        prog_layout = QVBoxLayout(prog_grp)
        self.prog_widget = FileSetting(StmProgrammerDownloader, "stm/programmer", "exe")
        prog_layout.addWidget(self.prog_widget)

        crab_grp = QGroupBox()
        crab_grp.setTitle("Crab Detection Model")
        crab_layout = QVBoxLayout(crab_grp)
        self.crab_widget = FileSetting(
            CrabDetectionModelDownloader, "cv/model", ["YOLO model files (*.pt)"]
        )
        crab_layout.addWidget(self.crab_widget)

        container_layout.addWidget(vh_grp)
        container_layout.addWidget(prog_grp)
        container_layout.addWidget(crab_grp)

        container_layout.addStretch()
        scrollable.setWidget(container)
        main_layout.addWidget(scrollable)

        self.refresh_all()

    def refresh_all(self) -> None:
        self.vh_widget.refresh()
        self.prog_widget.refresh()
        self.crab_widget.refresh()

    def showEvent(self, event: QShowEvent) -> None:
        self.refresh_all()
        return super().showEvent(event)

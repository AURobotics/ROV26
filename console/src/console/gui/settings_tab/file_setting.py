from pathlib import Path
from typing import Literal

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from console.env import Settings, pathing
from console.env.third_party import ThirdPartyDownloader
from core.concurrent.callback_worker import CallbackWorker


class FileSetting(QWidget):
    download_done = Signal()

    def __init__(
        self,
        downloader: type[ThirdPartyDownloader],
        settings_key: str,
        filters: Literal["exe"] | list[str] = ["All files (*)"],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = Settings()
        self.settings_key = settings_key
        self.downloader = downloader
        self.filters = filters
        layout = QVBoxLayout(self)
        self.path_label = QLabel()
        self.pickfile_btn = QPushButton("Choose File")
        self.pickfile_btn.clicked.connect(self.select_file)
        self.dlprogress = QProgressBar()
        self.dlprogress.setVisible(False)
        self.dl_label = QLabel()
        self.dl_label.setVisible(False)
        self.dlbtn = QPushButton("Download")
        self.dlbtn.clicked.connect(self.download)
        self.download_done.connect(self.on_download_done)
        self.dl_handle: ThirdPartyDownloader | None = None
        self.dl_timer = QTimer()
        self.dl_timer.timeout.connect(self.update_progress)
        layout.addWidget(self.path_label)
        layout.addWidget(self.pickfile_btn)
        layout.addWidget(self.dl_label)
        layout.addWidget(self.dlprogress)
        layout.addWidget(self.dlbtn)

    def select_file(self) -> None:
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        dialog.setDirectory(str(pathing.resolve(self.settings.get(self.settings_key)).parent))
        if self.filters == "exe":
            proxy = pathing.ExecutableFilterProxy()
            dialog.setProxyModel(proxy)
        else:
            dialog.setNameFilters(self.filters)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        file_path = None
        if dialog.exec() == QFileDialog.DialogCode.Accepted:
            selected = dialog.selectedFiles()
            if selected:
                file_path = Path(selected[0])
                self.settings.set(self.settings_key, str(file_path))

        self.refresh()

    def refresh(self) -> None:
        if self.dl_handle:
            self.dl_label.setText(self.dl_handle.status_message)
        else:
            self.dl_label.setVisible(False)
        path = pathing.resolve(self.settings.get(self.settings_key))
        if path.exists():
            self.path_label.setText(f"Using file at {path}")
        else:
            self.path_label.setText(f"File NOT found at {path}")

    def update_progress(self) -> None:
        if self.dl_handle:
            self.dlprogress.setValue(self.dl_handle.progress_percent)
            self.dl_label.setText(self.dl_handle.status_message)

    def on_download_done(self) -> None:
        self.dlbtn.setText("Download")
        self.dlprogress.setVisible(False)
        self.pickfile_btn.setEnabled(True)
        self.dl_timer.stop()
        if self.dl_handle is not None:
            if Path(self.dl_handle.destination).exists():
                self.settings.set(self.settings_key, str(self.dl_handle.destination))
        self.refresh()
        self.dl_handle = None

    def download(self) -> None:
        if self.dl_handle:
            self.dl_handle.cancel()
            return

        self.dlbtn.setText("Cancel")
        self.dlprogress.setVisible(True)
        self.dlprogress.setValue(0)
        self.pickfile_btn.setEnabled(False)
        self.dl_timer.setInterval(50)
        self.dl_timer.start()
        path = pathing.resolve(self.settings.get_default(self.settings_key))
        self.dl_handle = self.downloader(path)
        task = CallbackWorker(self.dl_handle.run, self.download_done.emit)
        task.run()
        self.dl_label.setVisible(True)

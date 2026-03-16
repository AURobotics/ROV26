from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QSplashScreen

from console.assets import get_asset


class LoadingSplash(QSplashScreen):
    def __init__(self) -> None:
        pixmap = QPixmap(get_asset("novideo.png"))
        super().__init__(pixmap)
        self.setEnabled(False)

    def update_progress(self, message: str, progress: int):
        self.showMessage(
            f'{message} [{progress}%]',
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
            Qt.GlobalColor.white,
        )

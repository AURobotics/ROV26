from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import QSplashScreen

from console.assets import get_asset


class LoadingSplash(QSplashScreen):
    def __init__(self) -> None:
        pixmap = QPixmap(get_asset("splashscreen.png")).scaled(
            620,
            480,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter = QPainter(pixmap)
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "Loading..")
        painter.end()
        super().__init__(pixmap)
        self.setEnabled(False)

    def update_progress(self, message: str, progress: int):
        self.showMessage(
            f"{message} [{progress}%]",
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
            Qt.GlobalColor.white,
        )

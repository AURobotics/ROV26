from PySide6.QtWidgets import QApplication
from console.gui.main_window import MainWindow
from sys import exit


def run() -> None:
    app = QApplication()
    window = MainWindow()
    window.show()
    ret_val = app.exec()
    exit(ret_val)
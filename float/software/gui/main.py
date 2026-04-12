import sys

from PyQt6.QtWidgets import QApplication

from gui.main_window import DemoWindow

def run_gui():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = DemoWindow()
    win.show()
    sys.exit(app.exec())
    print("hello")
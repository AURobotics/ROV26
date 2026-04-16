import sys

from PySide6.QtWidgets import QApplication

from gui.float_tab import DataViewerTab
from gui.main_window import DemoWindow

def run_gui():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = DemoWindow(DataViewerTab())
    win.show()
    sys.exit(app.exec())
    print("hello")
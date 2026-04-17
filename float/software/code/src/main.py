# main.py
import sys
from PySide6.QtWidgets import QApplication

from src.gui.main_window import MainWindow
from src.comms.comms import Comms


app = QApplication(sys.argv)
app.setStyle("Fusion")

win = MainWindow()
win.show()

exit_code = app.exec()
sys.exit(exit_code)
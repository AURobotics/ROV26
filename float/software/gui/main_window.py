from PyQt6.QtWidgets import QWidget, QMainWindow, QTabWidget
from PyQt6.QtCore import QTimer

from gui.pallete import PALETTE
from gui.float_tab import DataViewerTab


# for testing the float tab
class DemoWindow(QMainWindow):
    def __init__(self, tab):
        super().__init__()
        self.setWindowTitle("DataViewer — Standalone Demo")
        self.resize(1000, 680)
        self.setStyleSheet(f"background: {PALETTE['bg']};")

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: {PALETTE['bg']};
            }}
            QTabBar::tab {{
                background: {PALETTE['surface']};
                color: {PALETTE['text_muted']};
                border: 1px solid {PALETTE['border']};
                border-bottom: none;
                padding: 6px 16px;
                font: 700 9px 'Courier New';
                margin-right: 2px;
                border-radius: 4px 4px 0 0;
            }}
            QTabBar::tab:selected {{
                background: {PALETTE['bg']};
                color: {PALETTE['accent']};
                border-color: {PALETTE['accent']}55;
            }}
            QTabBar::tab:hover:!selected {{
                color: {PALETTE['text']};
            }}
        """)

        self._viewer = tab
        tabs.addTab(self._viewer, "Data Viewer")
        tabs.addTab(QWidget(), "Tab 2")   # placeholder sibling tab
        tabs.addTab(QWidget(), "Tab 3")

        self.setCentralWidget(tabs)

        # demo: push a few messages after startup
        QTimer.singleShot(800,  lambda: self._viewer.post_message("System initialised.", "INFO"))

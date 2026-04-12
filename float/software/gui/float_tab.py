import os
import csv

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QFrame,
)
from PyQt6.QtCore import Qt

# from gui.test import ColumnSelector
from gui.pallete import PALETTE
from gui.message_bar import MessageBarWidget
from gui.graph_viewer import GraphWidget
from gui.column_selector import ColumnSelector

class DataViewerTab(QWidget):
    """
    Drop-in tab widget.
    Use post_message(text, level) to push messages from external code.
    Call load_csv(path) programmatically to load a file.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._csv_data: list[dict] = []
        self._columns: list[str] = []
        self._col_selector: ColumnSelector | None = None
        self._build_ui()
        self.post_message("DataViewer ready — waiting for CSV data.", "INFO")

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.setStyleSheet(f"background: {PALETTE['bg']};")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # toolbar
        toolbar = self._make_toolbar()
        root.addWidget(toolbar)

        # column selector placeholder (populated after CSV load)
        self._selector_placeholder = QFrame()
        self._selector_placeholder.setFixedHeight(38)
        self._selector_placeholder.setStyleSheet("background:transparent;")
        root.addWidget(self._selector_placeholder)

        # graph
        self._graph = GraphWidget()
        graph_wrapper = QFrame()
        graph_wrapper.setStyleSheet(f"""
            QFrame {{
                background: {PALETTE['surface']};
                border: 1px solid {PALETTE['border']};
                border-radius: 8px;
                margin: 0 8px 8px 8px;
            }}
        """)
        gw_layout = QVBoxLayout(graph_wrapper)
        gw_layout.setContentsMargins(4, 4, 4, 4)
        gw_layout.addWidget(self._graph)
        root.addWidget(graph_wrapper, stretch=1)

        # message bar
        self._msg_bar = MessageBarWidget()
        root.addWidget(self._msg_bar)

    def _make_toolbar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(44)
        bar.setStyleSheet(f"""
            QFrame {{
                background: {PALETTE['surface']};
                border-bottom: 1px solid {PALETTE['border']};
            }}
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)

        title = QLabel("DATA VIEWER")
        title.setStyleSheet(f"color:{PALETTE['text']}; font:700 11px 'Courier New'; background:transparent;")
        layout.addWidget(title)

        self._file_label = QLabel("No file loaded")
        self._file_label.setStyleSheet(f"color:{PALETTE['text_muted']}; font:9px 'Courier New'; background:transparent;")
        layout.addWidget(self._file_label, stretch=1)

        self._load_btn = self._tool_btn("Load CSV", PALETTE["accent"])
        self._load_btn.clicked.connect(self._on_load_clicked)
        layout.addWidget(self._load_btn)

        self._clear_btn = self._tool_btn("Clear", PALETTE["msg_err"])
        self._clear_btn.clicked.connect(self._on_clear_clicked)
        layout.addWidget(self._clear_btn)

        return bar

    def _tool_btn(self, text: str, color: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(28)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {color}1A;
                color: {color};
                border: 1px solid {color}55;
                border-radius: 5px;
                padding: 0 12px;
                font: 700 9px 'Courier New';
            }}
            QPushButton:hover {{
                background: {color}33;
                border-color: {color};
            }}
            QPushButton:pressed {{
                background: {color}55;
            }}
        """)
        return btn

    # ── CSV loading ───────────────────────────────────────────────────────────
    def _on_load_clicked(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV file", "", "CSV files (*.csv);;All files (*)"
        )
        if path:
            self.load_csv(path)

    def load_csv(self, path: str):
        """Public API: load a CSV file by path."""
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                data = list(reader)
                if not data:
                    self.post_message(f"CSV is empty: {path}", "WARN")
                    return
                columns = list(data[0].keys())

            self._csv_data = data
            self._columns = columns
            self._file_label.setText(os.path.basename(path))
            self.post_message(
                f"Loaded {len(data)} rows × {len(columns)} columns from '{os.path.basename(path)}'", "OK"
            )
            self._setup_column_selector(columns)
        except Exception as e:
            self.post_message(f"Failed to load CSV: {e}", "ERROR")

    def _setup_column_selector(self, columns: list[str]):
        # remove old selector if any
        if self._col_selector:
            self._col_selector.deleteLater()
            self._col_selector = None

        sel = ColumnSelector(columns, self._selector_placeholder)
        sel_layout = QHBoxLayout(self._selector_placeholder)
        sel_layout.setContentsMargins(8, 4, 8, 4)
        sel_layout.addWidget(sel)
        self._col_selector = sel
        sel.selection_changed.connect(self._on_selection_changed)

        # initial plot: first col = x, rest = y
        x_key = columns[0]
        y_keys = columns[1:]
        self._graph.load(self._csv_data, x_key, y_keys)
        self.post_message(f"Plotting: x={x_key}  y={', '.join(y_keys)}", "INFO")

    def _on_selection_changed(self, x_key: str, y_keys: list[str]):
        if not y_keys:
            self.post_message("Select at least one Y column to plot.", "WARN")
            self._graph.clear()
            return
        self._graph.load(self._csv_data, x_key, y_keys)
        self.post_message(f"Re-plotted: x={x_key}  y={', '.join(y_keys)}", "INFO")

    def _on_clear_clicked(self):
        self._csv_data = []
        self._columns = []
        self._file_label.setText("No file loaded")
        self._graph.clear()
        if self._col_selector:
            self._col_selector.deleteLater()
            self._col_selector = None
            # reset placeholder layout
            old = self._selector_placeholder.layout()
            if old:
                QWidget().setLayout(old)
        self.post_message("Data cleared.", "INFO")

    # ── Message API ───────────────────────────────────────────────────────────
    def post_message(self, text: str, level: str = "INFO"):
        """Public API: push a message into the message bar."""
        self._msg_bar.post(text, level)


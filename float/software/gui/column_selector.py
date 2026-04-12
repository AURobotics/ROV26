from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QFrame
from PyQt6.QtCore import pyqtSignal

from gui.pallete import PALETTE

class ColumnSelector(QFrame):
    selection_changed = pyqtSignal(str, list)   # x_key, [y_keys]

    def __init__(self, columns: list[str], parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {PALETTE['surface']};
                border: 1px solid {PALETTE['border']};
                border-radius: 6px;
            }}
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        layout.addWidget(self._muted("X-AXIS:"))
        self._x_btns: list[QPushButton] = []
        self._y_btns: list[QPushButton] = []
        self._x_key = columns[0] if columns else ""
        self._y_keys = columns[1:] if len(columns) > 1 else []

        for col in columns:
            btn = self._col_btn(col)
            btn.setProperty("col", col)
            btn.setProperty("role", "x" if col == self._x_key else "y")
            btn.clicked.connect(lambda _, c=col: self._toggle(c))
            layout.addWidget(btn)
            if col == self._x_key:
                self._x_btns.append(btn)
            else:
                self._y_btns.append(btn)

        layout.addStretch()
        self._all_btns = {col: b for col, b in
                          zip(columns, self._x_btns + self._y_btns)}
        self._columns = columns
        self._refresh_styles()

    def _muted(self, t):
        l = QLabel(t)
        l.setStyleSheet(f"color:{PALETTE['text_muted']}; font:700 8px 'Courier New'; background:transparent; border:none;")
        return l

    def _col_btn(self, text):
        btn = QPushButton(text)
        btn.setFixedHeight(22)
        btn.setCheckable(True)
        return btn

    def _toggle(self, col):
        # clicking x-axis col → move it; clicking y col → toggle it
        if col == self._x_key:
            return
        if col in self._y_keys:
            self._y_keys.remove(col)
        else:
            self._y_keys.append(col)
        self._refresh_styles()
        self.selection_changed.emit(self._x_key, list(self._y_keys))

    def _refresh_styles(self):
        for col, btn in self._all_btns.items():
            if col == self._x_key:
                style = f"background:{PALETTE['accent']}22; color:{PALETTE['accent']}; border:1px solid {PALETTE['accent']}; border-radius:4px; font:700 9px 'Courier New';"
            elif col in self._y_keys:
                idx = self._y_keys.index(col)
                colors = [PALETTE["accent2"], PALETTE["accent3"], PALETTE["accent4"], PALETTE["accent"]]
                c = colors[idx % len(colors)]
                style = f"background:{c}22; color:{c}; border:1px solid {c}; border-radius:4px; font:700 9px 'Courier New';"
            else:
                style = f"background:transparent; color:{PALETTE['text_muted']}; border:1px solid {PALETTE['border']}; border-radius:4px; font:9px 'Courier New';"
            btn.setStyleSheet(style)

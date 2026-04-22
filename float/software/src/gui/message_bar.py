from datetime import datetime
from collections import deque

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame,
    QScrollArea
)
from PySide6.QtCore import Qt, QTimer

from .pallete import PALETTE
from enum import Enum

class MessageLevel(Enum):
    INFO = PALETTE["msg_info"]
    OK = PALETTE["msg_ok"]
    RECEIVED = PALETTE["msg_ok"]
    WARN = PALETTE["msg_warn"]
    ERROR = PALETTE["msg_err"]
class MessageEntry:
    def __init__(self, text: str, level: MessageLevel = MessageLevel.INFO):
        self.text = text
        self.level: MessageLevel = level
        self.ts = datetime.now().strftime("%H:%M:%S")
        self.color = self.level.value


class MessageBarWidget(QWidget):
    """Compact scrollable message log strip at the bottom of the window."""

    def __init__(self, max_messages: int = 200, parent=None):
        super().__init__(parent)
        self._messages: deque[MessageEntry] = deque(maxlen=max_messages)
        self.setFixedHeight(180)
        self.setStyleSheet(f"""
            background: {PALETTE['msg_bg']};
            border-top: 1px solid {PALETTE['border']};
        """)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # header strip
        hdr = QFrame()
        hdr.setFixedHeight(22)
        hdr.setStyleSheet(f"background: {PALETTE['border']};")
        hdr_layout = QHBoxLayout(hdr)
        hdr_layout.setContentsMargins(8, 0, 8, 0)
        lbl = QLabel("● MESSAGES")
        lbl.setStyleSheet(f"color: {PALETTE['text_muted']}; font: 700 9px 'Courier New';")
        hdr_layout.addWidget(lbl)
        hdr_layout.addStretch()

        clr_btn = QPushButton("CLEAR")
        clr_btn.setFixedSize(44, 16)
        clr_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {PALETTE['text_muted']};
                border: 1px solid {PALETTE['border']};
                border-radius: 2px;
                font: 700 8px 'Courier New';
            }}
            QPushButton:hover {{
                color: {PALETTE['text']};
                border-color: {PALETTE['accent']};
            }}
        """)
        clr_btn.clicked.connect(self.clear)
        hdr_layout.addWidget(clr_btn)
        root.addWidget(hdr)

        # scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: {PALETTE['msg_bg']}; }}
            QScrollBar:vertical {{
                background: {PALETTE['surface']};
                width: 6px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {PALETTE['border']};
                border-radius: 3px;
            }}
        """)

        self._msg_container = QWidget()
        self._msg_container.setStyleSheet(f"background: {PALETTE['msg_bg']};")
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setContentsMargins(6, 2, 6, 2)
        self._msg_layout.setSpacing(1)
        self._msg_layout.addStretch()

        scroll.setWidget(self._msg_container)
        root.addWidget(scroll)
        self._scroll = scroll

    # public API ---------------------------------------------------------------
    def post(self, text: str, level: MessageLevel = MessageLevel.INFO):
        entry = MessageEntry(text, level)
        self._messages.append(entry)
        self._add_label(entry)
        # auto-scroll to bottom
        QTimer.singleShot(30, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def clear(self):
        self._messages.clear()
        while self._msg_layout.count() > 1:
            item = self._msg_layout.takeAt(0)
            if item.widget(): # type: ignore
                item.widget().deleteLater() # type: ignore

    # internal -----------------------------------------------------------------
    def _add_label(self, entry: MessageEntry):
        lbl = QLabel(f"[{entry.ts}] [{entry.level.name:<5}] {entry.text}")
        lbl.setStyleSheet(f"""
            color: {entry.color};
            font: 10px 'Courier New';
            padding: 1px 2px;
            background: transparent;
        """)
        lbl.setWordWrap(True)
        # insert before the stretch
        self._msg_layout.insertWidget(self._msg_layout.count() - 1, lbl)

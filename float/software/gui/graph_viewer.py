from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath
)
from PyQt6.QtCore import QPointF

from gui.pallete import PALETTE

class GraphWidget(QWidget):
    """Renders one or more series from a list of dicts, auto-scaled."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data: list[dict] = []       # rows from CSV
        self.x_key: str = ""             # column used for x-axis
        self.y_keys: list[str] = []      # columns plotted as series
        self.setMinimumHeight(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background: {PALETTE['surface']}; border-radius: 8px;")

        # series colours
        self._series_colors = [
            PALETTE["accent"], PALETTE["accent2"],
            PALETTE["accent3"], PALETTE["accent4"],
        ]

        self._anim_alpha = 0.0
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._tick_fade)

    # public API ---------------------------------------------------------------
    def load(self, data: list[dict], x_key: str, y_keys: list[str]):
        self.data = data
        self.x_key = x_key
        self.y_keys = y_keys
        self._anim_alpha = 0.0
        self._fade_timer.start(16)
        self.update()

    def clear(self):
        self.data = []
        self.x_key = ""
        self.y_keys = []
        self.update()

    # internal -----------------------------------------------------------------
    def _tick_fade(self):
        self._anim_alpha = min(1.0, self._anim_alpha + 0.04)
        self.update()
        if self._anim_alpha >= 1.0:
            self._fade_timer.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        W, H = rect.width(), rect.height()

        # background
        bg = QColor(PALETTE["surface"])
        painter.fillRect(rect, bg)

        if not self.data or not self.y_keys:
            self._draw_placeholder(painter, W, H)
            return

        # margins
        ml, mr, mt, mb = 60, 20, 20, 50

        # collect numeric y values
        all_y = []
        series_vals: list[list[float | None]] = []
        for yk in self.y_keys:
            vals = []
            for row in self.data:
                try:
                    vals.append(float(row.get(yk, "")))
                    all_y.append(vals[-1])
                except (ValueError, TypeError):
                    vals.append(None)
            series_vals.append(vals)

        if not all_y:
            self._draw_placeholder(painter, W, H)
            return

        y_min, y_max = min(all_y), max(all_y)
        if y_min == y_max:
            y_min -= 1; y_max += 1
        y_range = y_max - y_min

        n = len(self.data)
        plot_w = W - ml - mr
        plot_h = H - mt - mb

        def px(i):  return ml + (i / max(n - 1, 1)) * plot_w
        def py(v):  return mt + (1 - (v - y_min) / y_range) * plot_h

        # grid
        grid_color = QColor(PALETTE["grid"])
        grid_pen = QPen(grid_color, 1)
        painter.setPen(grid_pen)
        for k in range(5):
            yv = y_min + k * y_range / 4
            gy = py(yv)
            painter.drawLine(int(ml), int(gy), int(W - mr), int(gy))
            painter.setPen(QColor(PALETTE["text_muted"]))
            painter.setFont(QFont("Courier New", 8))
            painter.drawText(2, int(gy) + 4, f"{yv:.2g}")
            painter.setPen(grid_pen)

        # x-axis labels
        label_step = max(1, n // 8)
        painter.setFont(QFont("Courier New", 8))
        painter.setPen(QColor(PALETTE["text_muted"]))
        for i in range(0, n, label_step):
            lx = int(px(i))
            label = str(self.data[i].get(self.x_key, i))[:10]
            painter.drawText(lx - 20, H - 10, 40, 16,
                             Qt.AlignmentFlag.AlignCenter, label)

        # axes
        axis_pen = QPen(QColor(PALETTE["border"]), 1)
        painter.setPen(axis_pen)
        painter.drawLine(ml, mt, ml, H - mb)
        painter.drawLine(ml, H - mb, W - mr, H - mb)

        # series
        for si, (yk, vals) in enumerate(zip(self.y_keys, series_vals)):
            color = QColor(self._series_colors[si % len(self._series_colors)])
            color.setAlphaF(self._anim_alpha)

            # filled area
            fill_color = QColor(color)
            fill_color.setAlphaF(0.08 * self._anim_alpha)

            path = QPainterPath()
            first = True
            for i, v in enumerate(vals):
                if v is None:
                    first = True; continue
                x_, y_ = px(i), py(v)
                if first:
                    path.moveTo(x_, y_)
                    first = False
                else:
                    path.lineTo(x_, y_)

            # fill
            fill_path = QPainterPath(path)
            fill_path.lineTo(px(n - 1), H - mb)
            fill_path.lineTo(px(0), H - mb)
            fill_path.closeSubpath()
            painter.fillPath(fill_path, QBrush(fill_color))

            # line
            painter.setPen(QPen(color, 2))
            painter.drawPath(path)

            # dots at data points (only for small datasets)
            if n <= 60:
                dot_color = QColor(color)
                dot_color.setAlphaF(self._anim_alpha)
                painter.setBrush(QBrush(dot_color))
                painter.setPen(Qt.PenStyle.NoPen)
                for i, v in enumerate(vals):
                    if v is not None:
                        painter.drawEllipse(QPointF(px(i), py(v)), 3, 3)

        # legend
        lx = ml + 8
        for si, yk in enumerate(self.y_keys):
            color = QColor(self._series_colors[si % len(self._series_colors)])
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(lx, mt + 6, 10, 10, 2, 2)
            painter.setPen(QColor(PALETTE["text"]))
            painter.setFont(QFont("Courier New", 9))
            painter.drawText(lx + 14, mt + 16, yk)
            lx += len(yk) * 7 + 30

    def _draw_placeholder(self, painter: QPainter, W: int, H: int):
        painter.setPen(QColor(PALETTE["text_muted"]))
        painter.setFont(QFont("Courier New", 11))
        painter.drawText(
            self.rect(), Qt.AlignmentFlag.AlignCenter,
            "No data loaded\nDrop a CSV file or click  Load CSV"
        )
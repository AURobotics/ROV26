from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QTimer

import matplotlib
matplotlib.use("QtAgg")  # Use the Qt backend
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from .pallete import PALETTE


def _hex_to_rgb01(hex_color: str) -> tuple[float, float, float]:
    """Convert '#RRGGBB' or '#RRGGBBAA' to (r, g, b) floats in [0, 1]."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return r / 255, g / 255, b / 255


class GraphWidget(QWidget):
    """Renders one or more series from a list of dicts using Matplotlib.
    
    Each series is drawn as a continuous line with X markers at every data point.
    """

    # Series accent colours pulled from the app palette
    _SERIES_KEYS = ["accent", "accent2", "accent3", "accent4"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(300)

        self.data: list[dict] = []
        self.x_key: str = ""
        self.y_keys: list[str] = []

        # ── Matplotlib figure ────────────────────────────────────────────────
        bg = _hex_to_rgb01(PALETTE["surface"])
        self._fig = Figure(tight_layout=True, facecolor=bg)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvas(self._fig)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._canvas)

        # Fade-in animation
        self._anim_alpha = 0.0
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._tick_fade)

        self._style_axes()
        # self._draw_placeholder()

    # ── Public API ────────────────────────────────────────────────────────────

    def load(self, data: list[dict], x_key: str, y_keys: list[str]):
        """Load data and trigger a fade-in redraw."""
        self.data = data
        self.x_key = x_key
        self.y_keys = y_keys
        self._anim_alpha = 0.0
        self._fade_timer.start(16)   # ~60 fps
        self._redraw()

    def clear(self):
        """Remove all series and show the placeholder."""
        self.data = []
        self.x_key = ""
        self.y_keys = []
        self._fade_timer.stop()
        self._ax.cla()
        self._style_axes()
        # self._draw_placeholder()
        self._canvas.draw()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _tick_fade(self):
        self._anim_alpha = min(1.0, self._anim_alpha + 0.05)
        self._redraw()
        if self._anim_alpha >= 1.0:
            self._fade_timer.stop()

    def _style_axes(self):
        """Apply the app colour palette to the Matplotlib axes."""
        bg   = _hex_to_rgb01(PALETTE["surface"])
        grid = _hex_to_rgb01(PALETTE["grid"])
        text = _hex_to_rgb01(PALETTE["text_muted"])
        border = _hex_to_rgb01(PALETTE["border"])

        ax = self._ax
        ax.set_facecolor(bg)
        ax.tick_params(colors=text, labelsize=8)
        ax.xaxis.label.set_color(text)
        ax.yaxis.label.set_color(text)

        for spine in ax.spines.values():
            spine.set_edgecolor(border)

        ax.grid(
            True,
            color=grid,
            linestyle="--",
            linewidth=0.6,
            alpha=0.6,
        )
        ax.set_axisbelow(True)

        # Monospace tick labels to match the app's Courier New aesthetic
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontfamily("monospace")
            label.set_fontsize(8)

    def _redraw(self):
        if not self.data or not self.y_keys:
            return

        ax = self._ax
        ax.cla()
        self._style_axes()

        # Build x-axis values (numeric index or raw string labels)
        x_labels = [str(row.get(self.x_key, i))[:12] for i, row in enumerate(self.data)]
        x_idx = list(range(len(self.data)))

        alpha = self._anim_alpha

        for si, yk in enumerate(self.y_keys):
            palette_key = self._SERIES_KEYS[si % len(self._SERIES_KEYS)]
            color = _hex_to_rgb01(PALETTE[palette_key])

            y_vals_raw = []
            for row in self.data:
                try:
                    y_vals_raw.append(float(row.get(yk, "")))
                except (ValueError, TypeError):
                    y_vals_raw.append(None)

            # Split into contiguous segments so None gaps break the line
            xs_seg, ys_seg = [], []
            for xi, yv in zip(x_idx, y_vals_raw):
                if yv is None:
                    if xs_seg:
                        ax.plot(
                            xs_seg, ys_seg,
                            color=color,
                            linewidth=1.8,
                            alpha=alpha,
                            marker="x",
                            markersize=6,
                            markeredgewidth=1.8,
                            label=yk if not xs_seg or xs_seg[0] == x_idx[0] else "_",
                        )
                        # filled area under segment
                        ax.fill_between(
                            xs_seg, ys_seg,
                            alpha=0.07 * alpha,
                            color=color,
                        )
                        xs_seg, ys_seg = [], []
                else:
                    xs_seg.append(xi)
                    ys_seg.append(yv)

            if xs_seg:
                ax.plot(
                    xs_seg, ys_seg,
                    color=color,
                    linewidth=1.8,
                    alpha=alpha,
                    marker="x",
                    markersize=6,
                    markeredgewidth=1.8,
                    label=yk,
                )
                ax.fill_between(
                    xs_seg, ys_seg,
                    alpha=0.07 * alpha,
                    color=color,
                )

        # x-axis tick labels — show at most 8 evenly spaced labels
        n = len(x_idx)
        step = max(1, n // 8)
        ax.set_xticks(x_idx[::step])
        ax.set_xticklabels(x_labels[::step], rotation=30, ha="right")

        # Legend
        text_color = _hex_to_rgb01(PALETTE["text"])
        bg_color   = _hex_to_rgb01(PALETTE["surface"])
        border_color = _hex_to_rgb01(PALETTE["border"])
        legend = ax.legend(
            loc="upper left",
            fontsize=8,
            framealpha=0.85,
            facecolor=bg_color,
            edgecolor=border_color,
            labelcolor=text_color,
            prop={"family": "monospace", "size": 8},
        )

        self._canvas.draw()

    def _draw_placeholder(self):
        """Show a centred hint when no data is loaded."""
        text_color = _hex_to_rgb01(PALETTE["text_muted"])
        self._ax.text(
            0.5, 0.5,
            "No data loaded\nDrop a CSV file or click  Load CSV",
            transform=self._ax.transAxes,
            ha="center", va="center",
            fontsize=11,
            fontfamily="monospace",
            color=text_color,
            alpha=0.7,
        )
        self._ax.set_xticks([])
        self._ax.set_yticks([])
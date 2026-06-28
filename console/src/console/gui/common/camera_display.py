from __future__ import annotations
import enum

from PySide6.QtWidgets import QWidget, QLabel, QPushButton
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QPixmap
from console.assets import get_asset
from console.gui.common.combobox import QShowEvent
from console.gui.serial_tab.container import QHideEvent
from hal.camera.camera import CapMetadata, CapType, ConnectionStatus, VideoStream
from functools import partial
from typing import Optional, Callable, cast

from PySide6.QtCore import Qt, QSize, Signal, QObject
from PySide6.QtGui import (
    QImage,
    QPixmap,
    QIcon,
    QAction,
    QGuiApplication,
    QPainter,
    QPen,
    QTransform,
)
from PySide6.QtWidgets import (
    QLabel,
    QWidget,
    QGridLayout,
    QPushButton,
    QInputDialog,
    QLineEdit,
    QMenu,
    QToolButton,
    QSizePolicy,
)


class CameraPopupWindow(QWidget):
    def __init__(self, close_callback: Callable):
        super().__init__()
        self.setWindowFlag(Qt.WindowType.Window)
        self._notify_parent_of_close = close_callback
        width, height = cast(
            tuple[int, int], QGuiApplication.primaryScreen().size().toTuple()
        )
        width //= 2
        height //= 2
        self._view = QLabel(self)
        self.resize(width, height)
        self._view.setScaledContents(True)
        self.setWindowTitle("Video Stream")
        self.show()

    def resizeEvent(self, event):
        self._view.resize(event.size())

    def update_(self, pix):
        self._view.setPixmap(pix)

    def closeEvent(self, event) -> None:
        super().closeEvent(event)
        self._notify_parent_of_close()


class CameraSelection(QToolButton):
    def __init__(
        self,
        initial_value: str | int,
        change_cam_callback: Callable,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._change_cam = change_cam_callback
        self.setText("No Camera Connected")
        self._menu = QMenu(self)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setMenu(self._menu)
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        self._last_known_url = initial_value
        self._qactions_cache = []
        self._slots_cache = {}
        self._cameras_cache = []

        self._nocam_indicator = QAction("No Camera Devices Found")
        self._nocam_indicator.setEnabled(False)
        self._menu.addAction(self._nocam_indicator)
        self._devicelist_separator = self._menu.addSeparator()
        self._connect_to_url = self._menu.addAction("Custom URL")
        self._connect_to_url.triggered.connect(self._prompt_custom_source)

    @property
    def selection_inprogress(self):
        return self._menu.isVisible()

    def _insert_option_for_cameras(
        self, cameras: list[CapMetadata] | CapMetadata, position: QAction
    ):
        if isinstance(cameras, dict):
            cameras = [cameras]
        for cam in cameras:
            option = QAction(f"{cam['name']}")
            self._menu.insertAction(position, option)
            f = partial(self._change_cam, cam["descriptor"])
            self._slots_cache.update({cam["descriptor"]: f})
            option.triggered.connect(f)
            self._qactions_cache.append(option)
            self._cameras_cache.append(cam)

    def populate(self, devices, current):
        cameras = [
            CapMetadata(descriptor=cam, name=devices[cam], type=CapType.DEVICE)
            for cam in devices
        ]
        old_custom = None
        for cam in self._cameras_cache:
            if cam not in cameras:
                old_custom = cam
                break
        chosen = current
        new_custom = chosen if chosen not in cameras and chosen != old_custom else None
        if new_custom is not None:
            self._last_known_url = new_custom["descriptor"]
        new_cameras = [cam for cam in cameras if cam not in self._cameras_cache]
        old_cameras = [
            cam
            for cam in self._cameras_cache
            if cam not in cameras and cam != old_custom
        ]

        if len(cameras) == 0:
            if len(old_cameras) != 0:
                self._menu.insertAction(
                    self._devicelist_separator, self._nocam_indicator
                )
        else:
            self._menu.removeAction(self._nocam_indicator)

        if chosen != old_custom and old_custom is not None:
            old_cameras.append(old_custom)

        self._insert_option_for_cameras(new_cameras, self._devicelist_separator)
        if new_custom is not None:
            self._insert_option_for_cameras(new_custom, self._connect_to_url)

        for cam in old_cameras:
            for option in self._qactions_cache:
                if option.text() == f"{cam['name']}":
                    f = self._slots_cache.pop(cam["descriptor"])
                    option.triggered.disconnect(f)
                    self._menu.removeAction(option)
                    self._qactions_cache.remove(option)
                    self._cameras_cache.remove(cam)

        for option in self._qactions_cache:
            if chosen is not None:
                if chosen["name"] == option.text():
                    option.setCheckable(True)
                    option.setChecked(True)
                    self.setText(f"{chosen['name']}")
                else:
                    option.setChecked(False)
                    option.setCheckable(False)
            else:
                self.setText("No Camera Selected")
                option.setChecked(False)
                option.setCheckable(False)

    def _prompt_custom_source(self):
        text, ok = QInputDialog.getText(
            self,
            "Choose Camera by URL",
            "URL:",
            QLineEdit.EchoMode.Normal,
            str(self._last_known_url),
        )
        if ok:
            self._change_cam(text)


class CameraWidgetPosition(enum.Enum):
    RIGHT = enum.auto()
    LEFT = enum.auto()


class CaptureSignal(QObject):
    signal = Signal()


class CameraDisplay(QWidget):
    _stream: VideoStream
    _view: QLabel
    _empty_frame: QPixmap
    _mirror_h: bool
    _mirror_v: bool
    _grid: QGridLayout
    _camera_selector: CameraSelection
    _popup_view: Optional[CameraPopupWindow]
    _toolbar_buttons: dict[str, QPushButton]
    _position: CameraWidgetPosition | None

    def __init__(
        self,
        descriptor: int | str | None = None,
        parent: QWidget | None = None,
        position: CameraWidgetPosition | None = None,
        main_widget_ref: CameraDisplay | None = None,
    ):
        super().__init__(parent)
        self._stream = VideoStream(descriptor)
        self._view = QLabel(self)
        self._view.setAlignment(
            Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
        )
        self._mirror_h = False
        self._mirror_v = False
        self._photosphere_on = False

        self.setAttribute(Qt.WidgetAttribute.WA_Hover)
        self._grid = QGridLayout()
        self.setLayout(self._grid)

        toolbar_buttons = {
            "hflip": {
                "icon": QIcon(get_asset("flip-horizontal.svg")),
                "function": self.hflip,
                "tooltip": "Flip Horizontally",
            },
            "vflip": {
                "icon": QIcon(get_asset("flip-vertical.svg")),
                "function": self.vflip,
                "tooltip": "Flip Vertically",
            },
            "maximize": {
                "icon": QIcon(get_asset("maximize.svg")),
                "function": self._launch_popup_view,
                "tooltip": "Maximize the Stream View",
            },
            "r-left": {
                "icon": QIcon(get_asset("r-left.svg")),
                "function": lambda: self._rotate(-90),
                "tooltip": "Rotate 1 degree anti-clockwise",
            },
            "r-right": {
                "icon": QIcon(get_asset("r-right.svg")),
                "function": lambda: self._rotate(90),
                "tooltip": "Rotate 1 degree clockwise",
            },
        }

        self._toolbar_buttons = {}

        for i in range(0, 9):
            self._grid.setRowStretch(i, 1)
        col = 0
        for b in toolbar_buttons:
            pb = QPushButton(toolbar_buttons[b]["icon"], "")
            pb.setIconSize(QSize(24, 24))
            pb.clicked.connect(toolbar_buttons[b]["function"])
            pb.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            pb.setVisible(False)
            pb.setToolTip(toolbar_buttons[b]["tooltip"])
            self._toolbar_buttons.update({b: pb})
            self._grid.addWidget(pb, 9, col, 1, 1)
            col += 1

        self._position = position

        if self._position:
            self._swap_button = QPushButton(QIcon(get_asset("swap.svg")), "")
            self._swap_button.setVisible(False)
            self._swap_button.setIconSize(QSize(24, 24))
            self._swap_button.clicked.connect(self._swap)
            self._swap_button.setSizePolicy(
                QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding
            )
            if self._position == CameraWidgetPosition.RIGHT:
                self._grid.addWidget(self._swap_button, 4, 0, 1, 1)
            if self._position == CameraWidgetPosition.LEFT:
                self._grid.addWidget(
                    self._swap_button, 4, 10, 1, 1, Qt.AlignmentFlag.AlignRight
                )

        self._camera_selector = CameraSelection(descriptor, self.change_cam)
        self._camera_selector.setVisible(False)

        self._grid.addWidget(self._camera_selector, 9, col, 1, 1)
        self.setLayout(self._grid)

        self._popup_view = None

        self._rotation = 0
        self._camera_timer = QTimer()
        self._camera_timer.timeout.connect(self._update)
        self._camera_timer.setInterval(15)
        self._camera_timer.start()
        self._main_widget_ref = main_widget_ref

    def _swap(self):
        if self._main_widget_ref:
            main_src = self._main_widget_ref._stream.source
            my_src = self._stream.source
            if main_src == my_src:
                return
            self._main_widget_ref._stream.source = my_src
            self._stream.source = main_src

    def _rotate(self, deg: int):
        self._rotation += deg

    def _popup_closed(self):
        self._popup_view = None

    def closeEvent(self, event):
        super().closeEvent(event)
        if self._popup_view is not None:
            self._popup_view.close()

    def hflip(self):
        self._mirror_h = not self._mirror_h

    def vflip(self):
        self._mirror_v = not self._mirror_v

    def _launch_popup_view(self):
        if self._popup_view is None:
            self._popup_view = CameraPopupWindow(self._popup_closed)
        else:
            self._popup_view.activateWindow()

    def enterEvent(self, event):
        for i in range(self._grid.count()):
            item = self._grid.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(True)

    def leaveEvent(self, event):
        if self._camera_selector.selection_inprogress:
            return
        for i in range(self._grid.count()):
            item = self._grid.itemAt(i)
            if item and item.widget():
                item.widget().setVisible(False)

    def _pixmap_from_stream(self):
        frame = self._stream.frame
        if frame is None:
            return self._empty_frame
        q_image = QImage(
            frame.data,
            frame.shape[1],
            frame.shape[0],
            frame.strides[0],
            QImage.Format.Format_BGR888,
        ).mirrored(horizontally=self._mirror_h, vertically=self._mirror_v)
        if self._rotation != 0:
            rotation = QTransform().rotate(self._rotation)
            q_image = q_image.transformed(rotation)
        return QPixmap.fromImage(q_image)

    def resizeEvent(self, event):
        self._view.resize(event.size())

    def change_cam(self, cam):
        current_cam = self._stream.source
        if current_cam is not None:
            if current_cam["descriptor"] == cam:
                self._stream.source = None
                return
        self._stream.source = cam

    def _update(self):
        frame_pixmap = self._pixmap_from_stream()
        frame_pixmap = frame_pixmap.scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio
        )
        if self._photosphere_on:
            painter = QPainter(frame_pixmap)
            painter.setPen(QPen(Qt.GlobalColor.green, 4))
            painter.drawRect(frame_pixmap.rect())
            painter.end()
        self._view.setPixmap(frame_pixmap)

        if self._popup_view is not None:
            if self._popup_view.isVisible():
                self._popup_view.update_(frame_pixmap)

        self._camera_selector.populate(
            self._stream.available_cameras, self._stream.source
        )
        if self._stream.connection_status == ConnectionStatus.IN_PROGRESS:
            self._camera_selector.setText("Connecting..")

    def heightForWidth(self, arg__1: int) -> int:
        return int(arg__1 * 3 / 4)

    def hasHeightForWidth(self) -> bool:
        return True

    def getPixmap(self) -> QPixmap | None:
        return self._pixmap_from_stream()

    def showEvent(self, event: QShowEvent) -> None:
        self._camera_timer.setInterval(15)
        self._camera_timer.start()
        return super().showEvent(event)

    def hideEvent(self, event: QHideEvent) -> None:
        self._camera_timer.stop()
        return super().hideEvent(event)

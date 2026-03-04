"""
Fault-tolerant video stream handler using opencv.
"""

from __future__ import annotations

from enum import Enum, auto
from os import name as os_name
from pathlib import Path
from threading import Thread
from time import sleep
from typing import TypedDict, Optional, Union
from console.assets import get_asset

import cv2
import requests
from cv2_enumerate_cameras import enumerate_cameras


class ConnectionStatus(Enum):
    CONNECTED = auto()
    DISCONNECTED = auto()
    IN_PROGRESS = auto()
    MIRRORING = auto()


class DisconnectReason(Enum):
    DESIRED_DISCONNECT = auto()
    RESOURCE_BUSY = auto()
    READ_ERROR = auto()
    INVALID_DESCRIPTOR = auto()
    RESOURCE_UNREACHABLE = auto()


class CapType(str, Enum):
    DEVICE = "device"
    IP = "ip"
    FILE = "file"


class CapMetadata(TypedDict):
    type: Optional[CapType]
    descriptor: Optional[Union[str, int]]
    name: Optional[str]


_ENUMERATION_APIS = {"nt": cv2.CAP_MSMF, "posix": cv2.CAP_GSTREAMER}
_ENUM_API = _ENUMERATION_APIS[os_name]


class VideoStream:
    EMPTY_FRAME = cv2.imread(get_asset("novideo.png"))

    _cap: cv2.VideoCapture
    _connection_status: ConnectionStatus
    _frame_thread: Thread
    _killswitch: bool
    _downstreams: list[VideoStream]
    _upstream: Optional[
        VideoStream
    ]  # VideoStream to mirror while ConnectionStatus.MIRRORING
    _cap_meta: CapMetadata
    _disconnect_reason: DisconnectReason
    _disconnect_cam_name: Optional[Union[str, int]]

    # CLASS-ONLY ATTRIBUTES
    _pool: list[VideoStream] = []
    _connections_queue: list[
        tuple[VideoStream, Optional[Union[int, str]], Optional[DisconnectReason]]
    ] = []
    _disconnect_in_progress: bool = False
    _connections_thread: Optional[Thread] = None

    def __init__(self, descriptor: Optional[Union[int, str]] = None):
        self._cap = cv2.VideoCapture()
        self._cap_meta = CapMetadata(type=None, descriptor=None, name=None)
        self._upstream = None
        self._downstreams = []
        self._connection_status = ConnectionStatus.DISCONNECTED
        self.__class__._register_stream(self)
        self._frame = None
        self._killswitch = False
        self._disconnect_reason = DisconnectReason.DESIRED_DISCONNECT
        self._disconnect_cam_name = None
        if descriptor is not None:
            self.source = descriptor
        self._frame_thread = Thread(target=self._frame_loop, daemon=True)
        self._frame_thread.start()

    @classmethod
    def _enqueue_connection(
        cls,
        obj: VideoStream,
        descriptor,
        disconnect_reason=DisconnectReason.DESIRED_DISCONNECT,
    ):
        cls._connections_queue.append((obj, descriptor, disconnect_reason))
        if cls._connections_thread is None or not cls._connections_thread.is_alive():
            cls._connections_thread = Thread(
                target=cls._connections_manager, daemon=True
            )
            cls._connections_thread.start()

    @classmethod
    def _connections_manager(cls):
        while True:
            if len(cls._connections_queue) > 0 and not cls._disconnect_in_progress:
                vs, desc, reason = cls._connections_queue.pop(0)
                if desc is not None:
                    vs._connect(descriptor=desc)
                else:
                    vs._disconnect(reason=reason)
            else:
                sleep(0.01)

    @classmethod
    def _register_stream(cls, obj: VideoStream):
        cls._pool.append(obj)

    @classmethod
    def mirror(cls, obj: VideoStream, descriptor: int | str) -> Optional[VideoStream]:
        upstream = None
        cap_type = cls._resolve_cap_type(descriptor)

        if cap_type == CapType.FILE:
            descriptor = str(Path(str(descriptor)).resolve())

        for s in cls._pool:
            if s == obj or s._upstream is not None:
                continue
            if s._cap_meta["descriptor"] == descriptor:
                upstream = s

        return upstream

    @staticmethod
    def get_available_cameras():
        return {cam.index: cam.name for cam in enumerate_cameras(_ENUM_API)}

    @property
    def available_cameras(self):
        return self.get_available_cameras()

    @property
    def disconnect_message(self):
        message = ""
        if self._disconnect_reason == DisconnectReason.DESIRED_DISCONNECT:
            return message
        if self._disconnect_cam_name is None:
            message = "One of the cameras disconnected unexpectedly"
        elif self._disconnect_reason == DisconnectReason.RESOURCE_BUSY:
            message = (
                f"Camera '{self._disconnect_cam_name}' failed to connect or read; in use by other object or "
                f"process."
            )
        elif self._disconnect_reason == DisconnectReason.INVALID_DESCRIPTOR:
            message = f"Camera '{self._disconnect_cam_name}' failed to connect. Invalid descriptor provided."
        elif self._disconnect_reason == DisconnectReason.RESOURCE_UNREACHABLE:
            message = f"'{self._disconnect_cam_name}': unreachable URL provided."
        self._disconnect_reason = DisconnectReason.DESIRED_DISCONNECT
        return message

    @property
    def connection_status(self):
        me = self
        if self._upstream is not None:
            me = self._upstream
        return me._connection_status

    @property
    def disconnect_reason(self) -> DisconnectReason:
        return self._disconnect_reason

    @disconnect_reason.setter
    def disconnect_reason(self, value: None = None):
        self._disconnect_reason = DisconnectReason.DESIRED_DISCONNECT

    @staticmethod
    def _resolve_cap_type(descriptor: CapMetadata | int | str) -> Optional[CapType]:
        if type(descriptor) is int:
            if descriptor not in VideoStream.get_available_cameras():
                return None
            return CapType.DEVICE
        elif type(descriptor) is str:
            filepath = Path(descriptor).resolve()
            if filepath.exists():
                return CapType.FILE
            else:
                return CapType.IP
        if isinstance(descriptor, dict):
            return descriptor["type"]
        return None

    @property
    def source(self) -> Optional[CapMetadata]:
        me = self
        if self._upstream is not None:
            me = self._upstream
        if me._cap_meta["descriptor"] is None:
            return None
        return me._cap_meta.copy()

    @source.setter
    def source(self, descriptor: Optional[CapMetadata | int | str]):
        if isinstance(descriptor, dict):
            descriptor = descriptor["descriptor"]
        if self._upstream is not None:
            if descriptor == self._upstream._cap_meta["descriptor"]:
                return
        elif descriptor == self._cap_meta["descriptor"]:
            return
        if self._connection_status == ConnectionStatus.IN_PROGRESS:
            return
        self._connection_status = ConnectionStatus.IN_PROGRESS
        self.__class__._enqueue_connection(self, descriptor)

    def _connect(self, descriptor: int | str):
        cap_type = self._resolve_cap_type(descriptor)

        if cap_type is None:
            self._disconnect(
                reason=DisconnectReason.INVALID_DESCRIPTOR, cam_name=descriptor
            )
            return
        possible_upstream = self.__class__.mirror(self, descriptor)
        if possible_upstream is not None:
            self._disconnect(reason=DisconnectReason.DESIRED_DISCONNECT)
            self._upstream = possible_upstream
            self._connection_status = ConnectionStatus.MIRRORING
            possible_upstream._downstreams.append(self)
            return

        if self._upstream is not None or len(self._downstreams) > 0:
            self._disconnect(reason=DisconnectReason.DESIRED_DISCONNECT)

        if cap_type == CapType.DEVICE and isinstance(descriptor, int):
            ok = self._cap.open(descriptor)
            if not ok:
                self._disconnect(
                    reason=DisconnectReason.RESOURCE_BUSY, cam_name=descriptor
                )
                return
            self._cap_meta["type"] = cap_type
            self._cap_meta["descriptor"] = descriptor
            self._cap_meta["name"] = self.available_cameras[descriptor]
            self._connection_status = ConnectionStatus.CONNECTED

        elif cap_type == CapType.FILE and isinstance(descriptor, str):
            filepath = Path(descriptor).resolve()
            ok = self._cap.open(str(filepath))
            if not ok:
                self._disconnect(
                    reason=DisconnectReason.RESOURCE_BUSY, cam_name=descriptor
                )
                return
            self._cap_meta["type"] = cap_type
            self._cap_meta["name"] = filepath.name
            self._cap_meta["descriptor"] = str(filepath)
            self._connection_status = ConnectionStatus.CONNECTED

        elif cap_type == CapType.IP and isinstance(descriptor, str):
            reachable = False
            try:
                response = requests.get(descriptor, timeout=3, stream=True)
                if response.status_code == 200:
                    reachable = True
                    response.close()
                    sleep(2)
            except requests.RequestException:
                reachable = False
            if not reachable:
                self._disconnect(
                    reason=DisconnectReason.RESOURCE_UNREACHABLE, cam_name=descriptor
                )
                return
            elif not self._cap.open(descriptor):
                self._disconnect(
                    reason=DisconnectReason.RESOURCE_BUSY, cam_name=descriptor
                )
            else:
                self._connection_status = ConnectionStatus.CONNECTED
                self._cap_meta["name"] = descriptor
                self._cap_meta["descriptor"] = descriptor
                self._cap_meta["type"] = cap_type

    def _disconnect(
        self,
        reason: Optional[DisconnectReason],
        part_of_disconnect_chain=False,
        cam_name: Optional[Union[str, int]] = None,
    ) -> None:
        if reason is None:
            reason = DisconnectReason.DESIRED_DISCONNECT
        if not part_of_disconnect_chain:
            self.__class__._disconnect_in_progress = True
        self._connection_status = ConnectionStatus.DISCONNECTED
        while self._frame is not None:
            sleep(0.15)
        self._cap.release()
        self._disconnect_reason = reason
        self._disconnect_cam_name = cam_name

        if self._upstream is not None:
            self._upstream._downstreams.remove(self)
            self._upstream = None

        descriptor = self._cap_meta["descriptor"]
        self._cap_meta["descriptor"] = None
        self._cap_meta["type"] = None
        self._cap_meta["name"] = None

        if len(self._downstreams) > 0:
            downstreams = self._downstreams.copy()
            for d in downstreams:
                d._disconnect(
                    reason=DisconnectReason.DESIRED_DISCONNECT,
                    part_of_disconnect_chain=True,
                )
            if reason == DisconnectReason.DESIRED_DISCONNECT:
                for d in downstreams:
                    d.source = descriptor
        if not part_of_disconnect_chain:
            self.__class__._disconnect_in_progress = False

    @property
    def frame(self):
        return self._frame if self._frame is not None else self.EMPTY_FRAME

    def _frame_loop(self):
        try:
            while not self._killswitch:
                sleep(0.015)
                if self._connection_status == ConnectionStatus.DISCONNECTED:
                    self._frame = None
                    continue
                if self._upstream is not None:
                    self._frame = self._upstream._frame
                    continue
                if self._connection_status == ConnectionStatus.CONNECTED:
                    ok, f = self._cap.read()
                    if not self._cap.isOpened() or not ok:
                        self._connection_status = ConnectionStatus.DISCONNECTED
                        desc = self._cap_meta["descriptor"]
                        self.__class__._enqueue_connection(
                            self, None, DisconnectReason.RESOURCE_BUSY
                        )
                        self.__class__._enqueue_connection(self, desc)
                        self._frame = None
                        continue
                    self._frame = f
                    continue
                self._frame = None
        except SystemExit:
            return self.kill()

    def kill(self):
        self._killswitch = True
        if self._frame_thread.is_alive():
            self._frame_thread.join()
        if self._cap.isOpened():
            self._cap.release()

    def __del__(self):
        self._killswitch = True
        if self._frame_thread.is_alive():
            self._frame_thread.join()
        if self._cap.isOpened():
            self._cap.release()

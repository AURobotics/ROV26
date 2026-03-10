"""
Wrapper for PyGame joysticks.
Manages the following:
   - Choosing one or none of the currently connected gamepads
   - Regularly checking for, presenting and managing connection changes
   - Providing an event-based interface for tracking
"""

from __future__ import annotations
import sys
import threading
import time
from enum import IntEnum, StrEnum
from typing import (
    Dict,
    Optional,
    Callable,
    Self,
    Tuple,
    TypedDict,
    List,
    Union,
    Annotated,
)
from annotated_types import Ge, Le
import os

if "PYGAME_HIDE_SUPPORT_PROMPT" not in os.environ:
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import pygame
from pygame._sdl2 import controller as sdl_controller


class ConnectionUpdate(TypedDict):
    name: str
    id: int
    open: bool


class NotAGamepadError(AttributeError): ...


class UnsupportedFeatureError(AttributeError, ValueError): ...


class IndexOutOfRangeError(ValueError): ...


class GamepadButton(StrEnum):
    SOUTH = "a"
    NORTH = "y"
    EAST = "b"
    WEST = "x"
    DPAD_UP = "dpup"
    DPAD_DOWN = "dpdown"
    DPAD_RIGHT = "dpright"
    DPAD_LEFT = "dpleft"
    RIGHT_STICK = "rightstick"
    LEFT_STICK = "leftstick"
    RIGHT_SHOULDER = "rightshoulder"
    LEFT_SHOULDER = "leftshoulder"
    START = "start"
    BACK = "back"
    GUIDE = "guide"
    TOUCHPAD = "touchpad"


class GamepadTrigger(StrEnum):
    RIGHT_TRIGGER = "righttrigger"
    LEFT_TRIGGER = "lefttrigger"


class GamepadStick(StrEnum):
    LEFT_X = "leftx"
    LEFT_Y = "lefty"
    RIGHT_X = "rightx"
    RIGHT_Y = "righty"


_CONNECTION_EVENT_TYPES = (pygame.JOYDEVICEADDED, pygame.JOYDEVICEREMOVED)
# Hats grouped with buttons since their events are discrete
_BUTTON_EVENT_TYPES = (pygame.JOYBUTTONUP, pygame.JOYBUTTONDOWN, pygame.JOYHATMOTION)


class _KnownJoystick(TypedDict):
    mapping: dict
    is_standard: bool


class JoystickManager:
    _joysticks: List[pygame.joystick.JoystickType]
    _known_joysticks: Dict[int, _KnownJoystick]
    _running: bool
    _initialized: bool
    _button_listeners: List[Callable]
    _connection_listeners: List[Callable]
    _event_worker_thread: threading.Thread

    _instance = None
    _creation_lock = threading.Lock()

    def __new__(cls, *args, **kwargs) -> Self:
        # Double-checked locking pattern
        if not cls._instance:
            with cls._creation_lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return

        pygame.init()
        pygame.joystick.init()
        self._initialized = True
        self._connection_listeners = []
        self._button_listeners = []
        self._running = True
        self._joysticks = []
        self._known_joysticks = {}
        pygame.event.pump()
        self._event_worker_thread = threading.Thread(
            target=self._event_worker, daemon=True
        )

    @property
    def num_connected(self) -> int:
        return pygame.joystick.get_count()

    @property
    def joysticks(self) -> Joystick: ...

    # def is_standard_gamepad(self, int)
    def _on_connection_event(self, event: pygame.event.EventType): ...

    def _on_button_event(self, event: pygame.event.EventType): ...

    def _event_worker(self):
        while self._running:
            time.sleep(0.15)
            try:
                for event in pygame.event.get():
                    if event.type in _CONNECTION_EVENT_TYPES:
                        self._on_connection_event(event)
                    elif event.type in _BUTTON_EVENT_TYPES:
                        self._on_button_event(event)
                    elif event.type == pygame.QUIT:
                        pygame.quit()
                        self._running = False
                        break
            except Exception:
                if not self._running:
                    break


class Joystick:
    _joystick: pygame.joystick.JoystickType
    _gamepad: Optional[sdl_controller.Controller]
    _stick_deadzone: int
    _manager: JoystickManager
    _connected: bool

    def __init__(
        self, joystick: pygame.joystick.JoystickType, manager: JoystickManager
    ) -> None:
        self._manager = manager
        self._connected = True
        self._joystick = joystick
        try:
            self._gamepad = sdl_controller.Controller.from_joystick(joystick)
        except pygame.error:
            self._gamepad = None

    @property
    def is_standard_gamepad(self) -> bool:
        return self._gamepad is not None and self._gamepad.attached()

    def get_gpbutton(self, button: GamepadButton) -> bool:
        if not self.is_standard_gamepad:
            raise NotAGamepadError()
        if button == GamepadButton.TOUCHPAD:
            mapping = self._gamepad.get_mapping()
            touchpad = mapping.get("touchpad")
            if touchpad is None:
                return False
            return self._joystick.get_button(int(touchpad[1:]))
        return self._gamepad.get_button(button)

    def get_gpstick(self, axis: GamepadStick) -> Annotated[float, Ge(-1.0), Le(1.0)]:
        if not self.is_standard_gamepad:
            raise NotAGamepadError()
        return self._gamepad.get_axis(axis)

    def get_gptrigger(self, trigger: GamepadTrigger) -> Annotated[float, Ge(0), Le(1.0)]:
        if not self.is_standard_gamepad:
            raise NotAGamepadError()
        

    def get_button(self, button_idx: int) -> bool:
        if self._joystick.get_numbuttons() < button_idx:
            raise IndexOutOfRangeError()
        return self._joystick.get_button(button_idx)

    def get_axis(self, axis_idx: int) -> Annotated[float, Ge(-1.0), Le(1.0)]:
        if self._joystick.get_numaxes() < axis_idx:
            raise IndexOutOfRangeError()
        return self._joystick.get_axis(axis_idx)

    def get_hat(self, hat_idx: int) -> Tuple[float, float]:
        if self._joystick.get_numhats() < hat_idx:
            raise IndexOutOfRangeError()
        return self._joystick.get_hat(hat_idx)

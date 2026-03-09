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
from enum import IntEnum
from typing import Dict, Optional, Callable, Self, TypedDict, List, Union
import os

if "PYGAME_HIDE_SUPPORT_PROMPT" not in os.environ:
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
import pygame
from pygame._sdl2 import controller as sdl_controller


class ConnectionUpdate(TypedDict):
    name: str
    id: int
    open: bool


class StandardButtons(IntEnum):
    SOUTH = pygame.CONTROLLER_BUTTON_A
    NORTH = pygame.CONTROLLER_BUTTON_Y
    EAST = pygame.CONTROLLER_BUTTON_B
    WEST = pygame.CONTROLLER_BUTTON_X
    DPAD_UP = pygame.CONTROLLER_BUTTON_DPAD_UP
    DPAD_DOWN = pygame.CONTROLLER_BUTTON_DPAD_DOWN
    DPAD_RIGHT = pygame.CONTROLLER_BUTTON_DPAD_RIGHT
    DPAD_LEFT = pygame.CONTROLLER_BUTTON_DPAD_LEFT
    RIGHT_STICK = pygame.CONTROLLER_BUTTON_RIGHTSTICK
    LEFT_STICK = pygame.CONTROLLER_BUTTON_LEFTSTICK
    RIGHT_SHOULDER = pygame.CONTROLLER_BUTTON_RIGHTSHOULDER
    LEFT_SHOULDER = pygame.CONTROLLER_BUTTON_LEFTSHOULDER
    START = pygame.CONTROLLER_BUTTON_START
    BACK = pygame.CONTROLLER_BUTTON_BACK
    GUIDE = pygame.CONTROLLER_BUTTON_GUIDE
    TOUCHPAD = -1


class StandardAxes(IntEnum): ...


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
        return self._gamepad is not None

"""
    Wrapper for PyGame joysticks.
    Manages the following:
       - Choosing one or none of the currently connected gamepads
       - Regularly presenting the state of the buttons
       - Regularly checking for, presenting and managing connection changes
       - Providing an event-based interface for tracking
    TODO: support DS4, DS5, XBox 360 mappings - currently supports DS4 only,
    see: https://github.com/libsdl-org/SDL/blob/SDL2/src/joystick/SDL_gamecontrollerdb.h
"""

import time
from enum import Enum
from threading import Event, Thread
from typing import Dict, Optional, Callable

import pygame


class Mappings(dict[str, list[str]], Enum):
    DS4 = {
        'buttons':  [
            'CROSS',
            'CIRCLE',
            'SQUARE',
            'TRIANGLE',
            'SHARE',
            'PS',
            'OPTIONS',
            'L3',
            'R3',
            'L1',
            'R1',
            'D-UP',
            'D-DOWN',
            'D-LEFT',
            'D-RIGHT',
            'TOUCHPAD',
            ],
        'axes':     ['LS-H', 'LS-V', 'RS-H', 'RS-V'],
        'triggers': ['L2', 'R2'],
        }


class GamepadTypes(Enum):
    DS4 = 'PS4 Controller'


class Controller:
    """
        Manages gamepad connection & selection, and updates key states by polling the chosen gamepad at an interval.
    """
    _gamepads: list[pygame.joystick.JoystickType]
    _gamepad: pygame.joystick.JoystickType | None
    _type: str | None
    _gamepad_guid: str | None
    _bindings_state: dict[str, int | float]
    _killswitch: bool
    _handler_thread: Thread
    _STICK_DEADZONE = 0.2

    def __init__(self) -> None:
        pygame.init()
        self._gamepad = None
        self._gamepad_guid = None
        self._type = None
        pygame.event.pump()
        self._refresh_gamepads(connect_if_only_device=True)
        self._killswitch = False

        self._bindings_state: Dict[str, float | int] = {}
        self._last_sent_state: Dict[str, float | int] = {}
        self._state_changed = Event()
        self._listeners: list[Dict] = []

        self._handler_thread = Thread(target=self._handler_loop, daemon=True)
        self._handler_thread.start()

    def _disconnect(self) -> None:
        self._gamepad = None
        self._gamepad_guid = None
        self._type = None
        self._gamepads = []
        self._bindings_state = {}
        self._last_sent_state = {}
        self._state_changed.set()

    def _connect(self, i: int) -> None:
        self._gamepad = self._gamepads[i]
        self._gamepad.init()
        self._gamepad_guid = self._gamepad.get_guid()
        for t in GamepadTypes:
            if t.value == self._gamepad.get_name():
                self._type = t.name

    def _refresh_gamepads(self, connect_if_only_device=False) -> None:
        gamepad_count = pygame.joystick.get_count()
        if gamepad_count == 0:
            self._disconnect()
            return
        self._gamepads = [pygame.joystick.Joystick(i) for i in range(gamepad_count)]
        for gamepad in self._gamepads:
            if gamepad.get_guid() == self._gamepad_guid:
                self._gamepad = gamepad
                return
        if connect_if_only_device:
            self._connect(0)

    @property
    def bindings_state(self):
        return self._bindings_state.copy()

    @property
    def gamepads(self) -> list[str]:
        self._refresh_gamepads()
        return [
            f"{gamepad.get_id()}: {gamepad.get_name()}" for gamepad in self._gamepads
            ]

    @property
    def connected(self):
        return self._gamepad is not None

    @property
    def gamepad(self) -> str | None:
        if self._gamepad is not None:
            return f"{self._gamepad.get_id()}: {self._gamepad.get_name()}"
        return None

    @gamepad.setter
    def gamepad(self, index: int | None) -> None:
        if index is None or index > len(self._gamepads):
            self._disconnect()
            return
        self._refresh_gamepads()
        n = self._gamepads[index].get_name()
        for i in GamepadTypes:
            if i.value == n:
                self._connect(index)

    def register_listener(self, callback: Callable, button: Optional[str | list[str]] = None, send_buttons=False):
        self._listeners.append({'callback': callback, 'buttons': button, 'send_buttons': send_buttons})

    def has_state_changed(self) -> bool:
        return self._state_changed.is_set()

    def mark_data_sent(self) -> None:
        self._last_sent_state = self.bindings_state.copy()
        self._state_changed.clear()

    def get_changed_data(self) -> Dict[str, float | int]:
        return {k: v for k, v in self._bindings_state.items()
                if self._last_sent_state.get(k) != v}

    def _handler_loop(self):
        try:
            while not self._killswitch:
                time.sleep(0.015)
                try:
                    for event in pygame.event.get():
                        if event.type == pygame.JOYDEVICEADDED:
                            self._refresh_gamepads(connect_if_only_device=True)
                        elif event.type == pygame.JOYDEVICEREMOVED:
                            self._refresh_gamepads()
                        elif event.type == pygame.JOYBUTTONDOWN:
                            if self._gamepad is None:
                                continue
                            if self._gamepad.get_instance_id() != event.instance_id:
                                continue
                            if len(self._listeners) == 0:
                                continue
                            for listener in self._listeners:
                                if listener['buttons'] is None \
                                        or Mappings.DS4['buttons'][event.button] in listener['buttons']:
                                    if listener['send_buttons']:
                                        listener['callback'](Mappings.DS4['buttons'][event.button])
                                    else:
                                        listener['callback']()
                        elif event.type == pygame.QUIT:
                            pygame.quit()
                            self._killswitch = True
                            break
                except Exception:
                    if self._killswitch:
                        break

                if self._gamepad is None:
                    continue

                buttons = {
                    k: self._gamepad.get_button(i)
                    for i, k in enumerate(Mappings[self._type]['buttons'])
                    }
                axes = {
                    a: (
                        self._gamepad.get_axis(i)
                        if abs(self._gamepad.get_axis(i)) > self._STICK_DEADZONE
                        else 0
                    )
                    for i, a in enumerate(Mappings[self._type]['axes'])
                    }
                triggers = {
                    t: (
                               self._gamepad.get_axis(
                                   i + len(Mappings[self._type]['axes'])
                                   )
                               + 1
                       )
                       / 2
                    for i, t in enumerate(Mappings[self._type]['triggers'])
                    }
                new_state = {**buttons, **axes, **triggers}

                if new_state != self._bindings_state:
                    self._bindings_state = new_state
                    self._state_changed.set()

                if self._state_changed.is_set():
                    time.sleep(0.005)
                else:
                    time.sleep(0.02)

        except SystemExit:
            return self.kill()

    def kill(self):
        self._killswitch = True
        if self._handler_thread.is_alive():
            self._handler_thread.join()
        self._disconnect()
        pygame.quit()

    def __del__(self) -> None:
        self._killswitch = True
        if self._handler_thread.is_alive():
            self._handler_thread.join()
        self._disconnect()
        pygame.quit()
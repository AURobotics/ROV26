"""
Wrapper for PyGame joysticks.
Manages the following:
   - Choosing one or none of the currently connected gamepads
   - Regularly presenting the state of the buttons
   - Regularly checking for, presenting and managing connection changes
   - Providing an event-based interface for tracking
TODO: support DS5, XBox 360 mappings - currently supports DS4 on Windows and Linux
see: https://github.com/libsdl-org/SDL/blob/SDL2/src/joystick/SDL_gamecontrollerdb.h
"""

import sys
import time
from enum import Enum
from threading import Thread
from typing import Dict, Optional, Callable, TypedDict, List, Union

import pygame


class ConnectionUpdate(TypedDict):
    name: str
    id: int
    open: bool


class Mappings(dict[str, list[str]], Enum):
    DS4 = {
        "buttons": [
            "CROSS",
            "CIRCLE",
            "SQUARE",
            "TRIANGLE",
            "SHARE",
            "PS",
            "OPTIONS",
            "L3",
            "R3",
            "L1",
            "R1",
            "D-UP",
            "D-DOWN",
            "D-LEFT",
            "D-RIGHT",
            "TOUCHPAD",
        ],
        "axes": ["LS-H", "LS-V", "RS-H", "RS-V"],
        "triggers": ["L2", "R2"],
    }
    # Linux mapping for DualShock 4
    DS4_LINUX = {
        "buttons": [
            "CROSS",
            "CIRCLE",
            "TRIANGLE",
            "SQUARE",  # 0-3
            "L1",
            "R1",
            "L2",
            "R2",  # 4-7
            "SHARE",
            "OPTIONS",
            "PS",  # 8-10
            "L3",
            "R3",  # 11-12
        ],
        "axes": ["LS-H", "LS-V", "UNUSED", "RS-H", "RS-V"],
        "triggers": ["UNUSED", "UNUSED", "L2", "UNUSED", "UNUSED", "R2"],
    }


class GamepadTypes(Enum):
    DS4 = "PS4 Controller"


class Controller:
    """
    Manages gamepad connection & selection, and updates key states by polling the chosen gamepad at an interval.
    """

    # Use Union for older Python compatibility or if Joystick/None pipe fails
    _gamepads: List[pygame.joystick.JoystickType]
    _gamepad: Optional[pygame.joystick.JoystickType]
    _type: Optional[str]
    _gamepad_guid: Optional[str]
    _bindings_state: Dict[str, Union[int, float]]
    _killswitch: bool
    _handler_thread: Thread
    _STICK_DEADZONE = 0.2

    def __init__(self) -> None:
        pygame.init()
        self._gamepad = None
        self._gamepad_guid = None
        self._type = None
        pygame.event.pump()

        self._bindings_state = {}
        self._listeners: List[Dict] = []
        self._connection_listeners: List[Callable] = []

        self._refresh_gamepads(connect_if_only_device=True)
        self._killswitch = False

        self._handler_thread = Thread(target=self._handler_loop, daemon=True)
        self._handler_thread.start()

    def _disconnect(self) -> None:
        self._gamepad = None
        self._gamepad_guid = None
        self._type = None
        self._gamepads = []
        self._bindings_state = {}
        self._notify_connection_listeners()

    def _connect(self, i: int) -> None:
        self._gamepad = self._gamepads[i]
        self._gamepad.init()
        self._gamepad_guid = self._gamepad.get_guid()

        # Determine mapping based on platform
        if sys.platform.startswith("linux"):
            self._type = "DS4_LINUX"
        else:
            self._type = "DS4"

        self._notify_connection_listeners()

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

    def _notify_connection_listeners(self):
        if len(self._connection_listeners) == 0:
            return
        connections: List[ConnectionUpdate] = [
            {
                "id": gp.get_id(),
                "name": gp.get_name(),
                "open": (
                    self._gamepad is not None and self._gamepad.get_id() == gp.get_id()
                ),
            }
            for gp in self._gamepads
        ]
        for l in self._connection_listeners:
            l(connections)

    @property
    def bindings_state(self):
        return self._bindings_state.copy()

    @property
    def gamepads(self) -> List[str]:
        self._refresh_gamepads()
        return [
            f"{gamepad.get_id()}: {gamepad.get_name()}" for gamepad in self._gamepads
        ]

    @property
    def connected(self):
        return self._gamepad is not None

    @property
    def gamepad(self) -> Optional[str]:
        if self._gamepad is not None:
            return f"{self._gamepad.get_id()}: {self._gamepad.get_name()}"
        return None

    @gamepad.setter
    def gamepad(self, index: Optional[int]) -> None:
        if index is None or index >= len(self._gamepads):
            self._disconnect()
            return
        self._refresh_gamepads()
        self._connect(index)

    def register_listener(
        self,
        callback: Callable,
        button: Optional[Union[str, List[str]]] = None,
        send_buttons=False,
    ):
        self._listeners.append(
            {"callback": callback, "buttons": button, "send_buttons": send_buttons}
        )

    def register_connection_listener(self, callback: Callable):
        self._connection_listeners.append(callback)

    def _handler_loop(self):
        try:
            while not self._killswitch:
                time.sleep(0.015)
                try:
                    for event in pygame.event.get():
                        if event.type == pygame.JOYDEVICEADDED:
                            self._refresh_gamepads(connect_if_only_device=True)
                            self._notify_connection_listeners()
                        elif event.type == pygame.JOYDEVICEREMOVED:
                            self._refresh_gamepads()
                            self._notify_connection_listeners()
                        elif event.type == pygame.JOYBUTTONDOWN:
                            if self._gamepad is None or self._type is None:
                                continue
                            if self._gamepad.get_instance_id() != event.instance_id:
                                continue

                            # Safety check for button index
                            if event.button >= len(Mappings[self._type]["buttons"]):
                                continue

                            btn_name = Mappings[self._type]["buttons"][event.button]
                            for listener in self._listeners:
                                if (
                                    listener["buttons"] is None
                                    or btn_name in listener["buttons"]
                                ):
                                    if listener["send_buttons"]:
                                        listener["callback"](btn_name)
                                    else:
                                        listener["callback"]()
                        elif event.type == pygame.QUIT:
                            pygame.quit()
                            self._killswitch = True
                            break
                except Exception:
                    if self._killswitch:
                        break

                if self._gamepad is None or self._type is None:
                    continue

                # Get counts to avoid "Invalid joystick button/axis" errors
                num_btns = self._gamepad.get_numbuttons()
                num_axes = self._gamepad.get_numaxes()

                buttons = {
                    k: self._gamepad.get_button(i)
                    for i, k in enumerate(Mappings[self._type]["buttons"])
                    if k != "UNUSED" and i < num_btns
                }
                axes = {
                    a: (
                        self._gamepad.get_axis(i)
                        if abs(self._gamepad.get_axis(i)) > self._STICK_DEADZONE
                        else 0
                    )
                    for i, a in enumerate(Mappings[self._type]["axes"])
                    if a != "UNUSED" and i < num_axes
                }
                triggers = {
                    t: (self._gamepad.get_axis(i) + 1) / 2
                    for i, t in enumerate(Mappings[self._type]["triggers"])
                    if t != "UNUSED" and i < num_axes
                }

                # Support D-Pad for Linux (Hats)
                if self._type == "DS4_LINUX" and self._gamepad.get_numhats() > 0:
                    hat_x, hat_y = self._gamepad.get_hat(0)
                    buttons.update(
                        {
                            "D-UP": 1 if hat_y == 1 else 0,
                            "D-DOWN": 1 if hat_y == -1 else 0,
                            "D-LEFT": 1 if hat_x == -1 else 0,
                            "D-RIGHT": 1 if hat_x == 1 else 0,
                        }
                    )

                self._bindings_state = {**buttons, **axes, **triggers}

        except SystemExit:
            return self.kill()

    def kill(self):
        self._killswitch = True
        if self._handler_thread.is_alive():
            self._handler_thread.join()
        self._disconnect()
        pygame.quit()

    def __del__(self) -> None:
        self.kill()

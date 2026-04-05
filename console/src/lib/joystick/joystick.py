from __future__ import annotations
import threading
from typing import Callable, Annotated, TYPE_CHECKING, overload
from annotated_types import Ge, Le

if TYPE_CHECKING:
    # only use the following in type hints
    # use [Joystick]._manager in expressions
    from lib.joystick.manager import _BaseJoystickManager
    import pygame

from lib.joystick.inputs import (
    GamepadButton,
    GamepadStick,
    GamepadTrigger,
    HatDirection,
)

from lib.joystick.exceptions import NotAGamepadError, UnsupportedFeatureError


class Joystick:
    _joystick: pygame.joystick.JoystickType
    _mapping: dict[str, str] | None
    _connected: bool
    _hat_motion_cache: tuple[int, int]
    _lock: threading.Lock

    def __init__(
        self,
        joystick: pygame.joystick.JoystickType,
        manager: _BaseJoystickManager,
        mapping: dict[str, str] | None,
    ) -> None:
        self._connected = True
        self._joystick = joystick
        self._manager = manager
        self._mapping = mapping
        self._hat_motion_cache = (0, 0)
        self._lock = threading.Lock()

    @property
    def connected(self) -> bool:
        return self._check_connection()

    def _check_connection(self) -> bool:
        if not self._connected:
            return False
        if not self._manager._pg.joystick.get_init():
            return False
        try:
            self._joystick.get_instance_id()
        except self._manager._pg.error:
            self._connected = False
            return False
        return True

    @property
    def is_gamepad(self) -> bool:
        return self._mapping is not None

    @property
    def guid(self) -> str:
        with self._lock:
            if not self.connected:
                return ""
            try:
                return self._joystick.get_guid()
            except self._manager._pg.error:
                self._check_connection()
                return ""

    @property
    def id(self) -> int:
        with self._lock:
            if not self.connected:
                return -1
            try:
                return self._joystick.get_instance_id()
            except self._manager._pg.error:
                self._check_connection()
                return -1

    @property
    def name(self) -> str:
        with self._lock:
            if not self.connected:
                return "Disconnected Joystick"
            try:
                return self._joystick.get_name()
            except self._manager._pg.error:
                self._check_connection()
                return "Disconnected Joystick"

    @property
    def power(self) -> str:
        with self._lock:
            if not self.connected:
                return "unkown"
            try:
                return self._joystick.get_power_level()
            except self._manager._pg.error:
                self._check_connection()
                return "unknown"

    def rumble(self, low: float, high: float, duration: int) -> bool:
        with self._lock:
            if not self.connected:
                return False
            try:
                return self._joystick.rumble(low, high, duration)
            except self._manager._pg.error:
                self._check_connection()
                return False

    def stop_rumble(self):
        with self._lock:
            if not self.connected:
                return
            try:
                self._joystick.stop_rumble()
            except self._manager._pg.error:
                self._check_connection()

    def _value_from_hwid(self, mapping: str) -> float:
        if mapping.startswith("h"):
            # Format: h<index>.<maskValue>
            parts = mapping[1:].split(".")
            hat_idx = int(parts[0])
            mask = int(parts[1])
            hat_val = self._joystick.get_hat(hat_idx)  # Returns (x, y)

            # SDL2 Hat Masks: 1=Up, 2=Right, 4=Down, 8=Left
            match mask:
                case 1:
                    return 1.0 if hat_val[1] == 1 else 0.0
                case 4:
                    return 1.0 if hat_val[1] == -1 else 0.0
                case 2:
                    return 1.0 if hat_val[0] == 1 else 0.0
                case 8:
                    return 1.0 if hat_val[0] == -1 else 0.0
            return 0.0

        if mapping.startswith("b"):
            btn_idx = int(mapping[1:])
            return 1.0 if self._joystick.get_button(btn_idx) else 0.0

        if "a" in mapping:
            # Check for sign prefix on the hardware side
            modifier = ""
            if mapping.startswith(("-", "+")):
                modifier = mapping[0]
                axis_idx = int(mapping[2:])  # Skip the sign and the 'a'
            else:
                axis_idx = int(mapping[1:])

            raw = self._joystick.get_axis(axis_idx)

            # Apply Hardware-side filtering
            if modifier == "-":
                return -raw
            if modifier == "+":
                return raw
            return raw

        return 0.0

    def _key_type_from_mapping(self, key: str) -> str:
        if self._mapping is None:
            raise NotAGamepadError()
        key_type = ""
        if key in self._mapping:
            key_type = "full"
        else:
            if "+" + key in self._mapping:
                key_type += "+"
            if "-" + key in self._mapping:
                key_type += "-"
        return key_type

    def _value_from_mapping(self, key: str, key_type: str) -> float:
        if self._mapping is None:
            raise NotAGamepadError()

        if len(key_type) == 0:
            raise UnsupportedFeatureError()

        value = 0.0
        if key_type in ("full", "+-"):
            hwid = self._mapping[key]
            value = self._value_from_hwid(hwid)
        if "+" in key_type:
            hwid = self._mapping["+" + key]
            value += max(0.0, self._value_from_hwid(hwid))
        if "-" in key_type:
            hwid = self._mapping["-" + key]
            value -= max(0.0, -self._value_from_hwid(hwid))
        return value

    def get_gpinput(
        self, inp: GamepadButton | GamepadTrigger | GamepadStick
    ) -> bool | float:
        with self._lock:
            value: float
            key_type: str
            try:
                if not self.connected:
                    raise UnsupportedFeatureError()
                key_type = self._key_type_from_mapping(inp.value)
                value = self._value_from_mapping(inp.value, key_type)
            except (self._manager._pg.error, UnsupportedFeatureError):
                self._check_connection()
                match inp:
                    case GamepadButton():
                        return False
                    case GamepadTrigger():
                        return 0.0
                    case GamepadStick():
                        return -1.0
            match inp:
                case GamepadButton():
                    return abs(value) > 0.5
                case GamepadTrigger():
                    if key_type in ("full", "+-"):
                        value = (value + 1.0) / 2.0
                    return max(0.0, min(1.0, value))
                case GamepadStick():
                    return value

    def get_button(self, button_idx: int) -> bool:
        with self._lock:
            if not self.connected:
                return False
            try:
                if self._joystick.get_numbuttons() <= button_idx:
                    raise IndexError()
                return self._joystick.get_button(button_idx)
            except self._manager._pg.error:
                return False

    def get_axis(self, axis_idx: int) -> Annotated[float, Ge(-1.0), Le(1.0)]:
        with self._lock:
            if not self.connected:
                return -1.0
            try:
                if self._joystick.get_numaxes() <= axis_idx:
                    raise IndexError()
                return self._joystick.get_axis(axis_idx)
            except self._manager._pg.error:
                return -1.0

    def get_hat(self, hat_idx: int) -> tuple[int, int]:
        with self._lock:
            if not self.connected:
                return (0, 0)
            try:
                if self._joystick.get_numhats() <= hat_idx:
                    raise IndexError()
                x, y = self._joystick.get_hat(hat_idx)
                return (int(x), int(y))
            except self._manager._pg.error:
                return (0, 0)

    def get_ball(self, ball_idx: int) -> tuple[float, float]:
        with self._lock:
            if not self.connected:
                return (0, 0)
            try:
                if self._joystick.get_numballs() <= ball_idx:
                    raise IndexError()
                return self._joystick.get_ball(ball_idx)
            except self._manager._pg.error:
                return (0, 0)

    @property
    def num_buttons(self) -> int:
        with self._lock:
            if not self.connected:
                return 0
            try:
                return self._joystick.get_numbuttons()
            except self._manager._pg.error:
                self._check_connection()
                return 0

    @property
    def num_balls(self) -> int:
        with self._lock:
            if not self.connected:
                return 0
            try:
                return self._joystick.get_numballs()
            except self._manager._pg.error:
                self._check_connection()
                return 0

    @property
    def num_axes(self) -> int:
        with self._lock:
            if not self.connected:
                return 0
            try:
                return self._joystick.get_numaxes()
            except self._manager._pg.error:
                self._check_connection()
                return 0

    @property
    def num_hats(self) -> int:
        with self._lock:
            if not self.connected:
                return 0
            try:
                return self._joystick.get_numhats()
            except self._manager._pg.error:
                self._check_connection()
                return 0

    def remove_button_listeners(self, button: int) -> None:
        self._manager.remove_button_listeners(self, button)

    def remove_hat_listeners(self, hat: int) -> None:
        self._manager.remove_hat_listeners(self, hat)

    def remove_gp_button_listeners(self, button: GamepadButton) -> None:
        self._manager.remove_gp_button_listeners(self, button)

    def disconnect_button_callback(self, callback: Callable) -> None:
        self._manager.disconnect_button_callback(self, callback)

    def disconnect_hat_callback(self, callback: Callable) -> None:
        self._manager.disconnect_hat_callback(self, callback)

    def disconnect_gp_button_callback(self, callback: Callable) -> None:
        self._manager.disconnect_gp_button_callback(self, callback)

    def remove_button_listener(self, callback: Callable, button: int) -> None:
        self._manager.remove_button_listener(self, callback, button)

    def remove_hat_listener(self, callback: Callable, hat: int) -> None:
        self._manager.remove_hat_listener(self, callback, hat)

    def remove_gp_button_listener(
        self, callback: Callable, button: GamepadButton
    ) -> None:
        self._manager.remove_gp_button_listener(self, callback, button)

    def add_hat_listener(
        self,
        callback: Callable[[Joystick, int, HatDirection], None],
        hat: int,
    ) -> None:
        self._manager.add_hat_listener(self, callback, hat)

    def add_hat_direction_listener(
        self,
        callback: Callable[[Joystick, int, bool], None],
        hat: int,
        direction: HatDirection,
    ) -> None:
        self._manager.add_hat_direction_listener(self, callback, hat, direction)

    def add_button_listener(
        self,
        callback: Callable[[Joystick, int, bool], None],
        button: int,
    ) -> None:
        self._manager.add_button_listener(self, callback, button)

    def add_gamepad_button_listener(
        self,
        callback: Callable[[Joystick, GamepadButton, bool], None],
        button: GamepadButton,
    ) -> None:
        self._manager.add_gamepad_button_listener(self, callback, button)

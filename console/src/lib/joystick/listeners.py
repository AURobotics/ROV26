from __future__ import annotations
from dataclasses import dataclass
import inspect
import weakref
from typing import Any, Callable, cast
from abc import ABC, abstractmethod

from lib.joystick.joystick import Joystick

from lib.joystick.exceptions import NotAGamepadError, UnsupportedFeatureError
from lib.joystick.inputs import GamepadButton, HatDirection


class CallbackFactory:
    @staticmethod
    def create_callback_ref(
        callback: Callable,
    ) -> weakref.WeakMethod | weakref.ReferenceType:
        if inspect.ismethod(callback) and not inspect.isbuiltin(callback):
            return weakref.WeakMethod(callback)
        else:
            return weakref.ref(callback)

    @staticmethod
    def create_connection_callback(
        callback: Callable[[Joystick, bool], None],
    ) -> ConnectionCallback:
        callback_ref = CallbackFactory.create_callback_ref(callback)
        return ConnectionCallback(callback_ref)

    @staticmethod
    def create_button_callback(
        joystick: Joystick, callback: Callable[[Joystick, int, bool], None], hwid: int
    ) -> ButtonCallback:
        callback_ref = CallbackFactory.create_callback_ref(callback)
        return ButtonCallback(joystick=joystick, hwid=hwid, callback_ref=callback_ref)

    @staticmethod
    def create_gamepad_button_callback(
        joystick: Joystick,
        callback: Callable[[Joystick, GamepadButton, bool], None],
        button: GamepadButton,
    ) -> GamepadButtonCallback | GamepadHatCallback:
        if joystick._mapping is None:
            raise NotAGamepadError()
        elif not button.value in joystick._mapping:
            raise UnsupportedFeatureError()
        hwid_str = joystick._mapping[button.value]
        assert hwid_str.startswith("b") or hwid_str.startswith("h")
        callback_ref = CallbackFactory.create_callback_ref(callback)
        if hwid_str.startswith("b"):
            hwid = int(hwid_str[1:])
            return GamepadButtonCallback(
                joystick=joystick, hwid=hwid, callback_ref=callback_ref, button=button
            )
        else:
            parts = hwid_str[1:].split(".")
            hwid = int(parts[0])
            direction = HatDirection(int(parts[1]))
            return GamepadHatCallback(
                joystick=joystick,
                hwid=hwid,
                callback_ref=callback_ref,
                hat_direction=direction,
                button=button,
            )

    @staticmethod
    def create_hat_motion_callback(
        joystick: Joystick,
        callback: Callable[[Joystick, int, HatDirection], None],
        hwid: int,
    ) -> HatMotionCallback:
        callback_ref = CallbackFactory.create_callback_ref(callback)
        return HatMotionCallback(
            joystick=joystick, hwid=hwid, callback_ref=callback_ref
        )

    @staticmethod
    def create_directed_hat_motion_callback(
        joystick: Joystick,
        callback: Callable[[Joystick, int, bool], None],
        hwid: int,
        direction: HatDirection,
    ) -> DirectedHatCallback:
        if direction == HatDirection.ANY:
            raise ValueError()
        callback_ref = CallbackFactory.create_callback_ref(callback)
        return DirectedHatCallback(
            joystick=joystick,
            hwid=hwid,
            callback_ref=callback_ref,
            hat_direction=direction,
        )


@dataclass(slots=True, frozen=True)
class Callback(ABC):
    callback_ref: weakref.WeakMethod | weakref.ref

    @property
    def callback_alive(self) -> bool:
        return self.callback_ref() is not None

    @abstractmethod
    def dispatch(self, *args, **kwargs) -> bool: ...


@dataclass(slots=True, frozen=True)
class ConnectionCallback(Callback):
    def dispatch(self, joystick: Joystick, connected: bool) -> bool:
        callback = self.callback_ref()
        if callback is None:
            return False
        try:
            callback(joystick, connected)
        except Exception as e:
            print(f"Connection Callback Error: {e}")
        return True


@dataclass(slots=True, frozen=True)
class InputCallback(Callback, ABC):
    joystick: Joystick
    hwid: int

    @abstractmethod
    def dispatch(self, state: Any, /) -> bool: ...

    @abstractmethod
    def matches(self, hwid: int, state: Any, /) -> bool: ...


@dataclass(slots=True, frozen=True)
class ButtonCallback(InputCallback):
    def dispatch(self, is_pressed: bool) -> bool:
        callback = self.callback_ref()
        if callback is None:
            return False
        try:
            callback = cast(Callable[[Joystick, int, bool], None], callback)
            callback(self.joystick, self.hwid, is_pressed)
        except Exception as e:
            print(f"Callback Error: {e}")
        return True

    def matches(self, hwid: int, state: bool | None = None) -> bool:
        return self.hwid == hwid


@dataclass(slots=True, frozen=True)
class HatMotionCallback(InputCallback):
    joystick: Joystick

    def _hat_direction(self, values) -> HatDirection:
        direction = HatDirection.CENTERED
        if values[1] == 1:
            direction |= HatDirection.UP
        if values[0] == 1:
            direction |= HatDirection.RIGHT
        if values[1] == -1:
            direction |= HatDirection.DOWN
        if values[0] == -1:
            direction |= HatDirection.LEFT
        return direction

    def dispatch(self, state: tuple[int, int]) -> bool:
        callback = self.callback_ref()
        if callback is None:
            return False
        callback = cast(Callable[[Joystick, int, HatDirection], None], callback)
        callback(self.joystick, self.hwid, self._hat_direction(state))
        return True

    def matches(self, hwid: int, values: tuple[int, int]) -> bool:
        if not hwid == self.hwid:
            return False
        return not values == self.joystick._hat_motion_cache


@dataclass(slots=True, frozen=True)
class DirectedHatCallback(HatMotionCallback):
    joystick: Joystick
    hat_direction: HatDirection

    def _is_pressed(self, values: tuple[int, int]) -> bool:
        direction = self._hat_direction(values)
        return (direction & self.hat_direction) == self.hat_direction

    def dispatch(self, state: tuple[int, int]) -> bool:
        callback = self.callback_ref()
        if callback is None:
            return False
        try:
            callback = cast(Callable[[Joystick, int, bool], None], callback)
            is_pressed = self._is_pressed(state)
            callback(self.joystick, self.hwid, is_pressed)
        except Exception as e:
            print(f"Callback Error: {e}")
        return True

    def matches(self, hwid: int, values: tuple[int, int]) -> bool:
        if not hwid == self.hwid:
            return False
        return not self._is_pressed(
            self.joystick._hat_motion_cache
        ) == self._is_pressed(values)


@dataclass(slots=True, frozen=True)
class GamepadButtonCallback(ButtonCallback):
    button: GamepadButton

    def dispatch(self, is_pressed: bool) -> bool:
        callback = self.callback_ref()
        if callback is None:
            return False
        try:
            callback = cast(Callable[[Joystick, GamepadButton, bool], None], callback)
            callback(self.joystick, self.button, is_pressed)
        except Exception as e:
            print(f"Callback Error: {e}")
        return True


@dataclass(slots=True, frozen=True)
class GamepadHatCallback(DirectedHatCallback):
    button: GamepadButton

    def dispatch(self, state: tuple[int, int]) -> bool:
        callback = self.callback_ref()
        if callback is None:
            return False
        try:
            callback = cast(Callable[[Joystick, GamepadButton, bool], None], callback)
            is_pressed = self._is_pressed(state)
            callback(self.joystick, self.button, is_pressed)
        except Exception as e:
            print(f"Callback Error: {e}")
        return True

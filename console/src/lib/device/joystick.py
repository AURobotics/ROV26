from __future__ import annotations
import inspect
from collections import defaultdict
from dataclasses import dataclass, replace
import threading
import weakref
from enum import Enum, IntFlag
from typing import (
    Dict,
    Optional,
    Callable,
    Self,
    Tuple,
    List,
    TypeAlias,
    Union,
    Annotated,
    cast,
)
from annotated_types import Ge, Le
import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
os.environ["SDL_NO_SIGNAL_HANDLERS"] = "1"

import pygame
from pygame._sdl2 import controller as sdl_controller


class NotAGamepadError(AttributeError): ...


class UnsupportedFeatureError(AttributeError, ValueError): ...


class IndexOutOfRangeError(ValueError): ...


class GamepadButton(Enum):
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


class GamepadTrigger(Enum):
    RIGHT_TRIGGER = "righttrigger"
    LEFT_TRIGGER = "lefttrigger"


class GamepadStick(Enum):
    LEFT_X = "leftx"
    LEFT_Y = "lefty"
    RIGHT_X = "rightx"
    RIGHT_Y = "righty"


class HatDirection(IntFlag):
    ANY = -1
    CENTERED = pygame.HAT_CENTERED
    UP = pygame.HAT_UP
    DOWN = pygame.HAT_DOWN
    LEFT = pygame.HAT_LEFT
    RIGHT = pygame.HAT_RIGHT
    UP_RIGHT = UP | RIGHT
    UP_LEFT = UP | LEFT
    DOWN_RIGHT = DOWN | RIGHT
    DOWN_LEFT = DOWN | LEFT

    def __str__(self):
        return (
            f"{self.__class__.__name__}.{self.name}"
            if self.name
            else f"{self.__class__.__name__}({self.value})"
        )


GamepadButtonCallback: TypeAlias = Callable[["Joystick", GamepadButton, bool], None]
JoystickButtonCallback: TypeAlias = Callable[["Joystick", int, bool], None]
_ButtonCallback: TypeAlias = Union[GamepadButtonCallback, JoystickButtonCallback]
HatMotionCallback: TypeAlias = Callable[["Joystick", int, HatDirection], None]
DirectedHatMotionCallback: TypeAlias = Callable[["Joystick", int, bool], None]
_HatCallback: TypeAlias = Union[
    GamepadButtonCallback, HatMotionCallback, DirectedHatMotionCallback
]

ConnectionCallback: TypeAlias = Callable[["Joystick", bool], None]


@dataclass(slots=True, frozen=True)
class _ConnectionListener:
    callback_ref: Union[weakref.WeakMethod, weakref.ref]

    @property
    def callback_alive(self) -> bool:
        return self.callback_ref() is not None

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
class _HatListener:
    joystick: Joystick
    hat: int
    hat_direction: int
    callback_ref: Union[weakref.WeakMethod, weakref.ref]
    dpad_button: Optional[GamepadButton] = None

    @property
    def callback_alive(self) -> bool:
        return self.callback_ref() is not None

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

    def _is_pressed(self, values: Tuple[int, int]) -> bool:
        direction = self._hat_direction(values)
        return (direction & self.hat_direction) == self.hat_direction

    def dispatch(self, values: Tuple[int, int]) -> bool:
        callback = self.callback_ref()

        if callback is None:
            return False  # prune dead callback

        try:
            if self.hat_direction == HatDirection.ANY:
                callback = cast(HatMotionCallback, callback)
                callback(self.joystick, self.hat, self._hat_direction(values))
            elif self.dpad_button is None:
                callback = cast(DirectedHatMotionCallback, callback)
                is_pressed = self._is_pressed(values)
                callback(self.joystick, self.hat, is_pressed)
            else:
                callback = cast(GamepadButtonCallback, callback)
                is_pressed = self._is_pressed(values)
                callback(self.joystick, self.dpad_button, is_pressed)
        except Exception as e:
            # We log but keep the listener; one crash shouldn't
            # necessarily unregister the button event.
            print(f"Callback Error: {e}")

        return True

    def matches(self, hat: int, values: Tuple[int, int]) -> bool:
        if not hat == self.hat:
            return False
        if self.hat_direction == HatDirection.ANY:
            return not values == self.joystick._hat_motion_cache
        return not self._is_pressed(
            self.joystick._hat_motion_cache
        ) == self._is_pressed(values)


@dataclass(slots=True, frozen=True)
class _ButtonListener:
    joystick: Joystick
    button: int
    callback_ref: Union[weakref.WeakMethod, weakref.ref]
    gamepad_button: Optional[GamepadButton] = None

    @property
    def callback_alive(self) -> bool:
        return self.callback_ref() is not None

    def dispatch(self, is_pressed: bool) -> bool:
        callback = self.callback_ref()

        if callback is None:
            return False  # prune dead callback

        try:
            if self.gamepad_button is None:
                callback(self.joystick, self.button, is_pressed)
            else:
                callback(self.joystick, self.gamepad_button, is_pressed)
        except Exception as e:
            # We log but keep the listener; one crash shouldn't
            # necessarily unregister the button event.
            print(f"Callback Error: {e}")

        return True

    def matches(self, button: int) -> bool:
        return self.button == button


class JoystickManager:
    _joysticks: Dict[int, Joystick]
    _running: bool
    _initialized: bool
    _button_listeners: dict[Joystick, list[_ButtonListener]]
    _hat_listeners: dict[Joystick, list[_HatListener]]
    _connection_listeners: List[_ConnectionListener]
    _event_worker_thread: threading.Thread
    _lock: threading.RLock

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
        self._initialized = True
        pygame.display.init()
        pygame.joystick.init()
        sdl_controller.init()
        self._connection_listeners = []
        self._button_listeners = defaultdict(list)
        self._hat_listeners = defaultdict(list)
        self._running = True
        self._joysticks = {}
        self._lock = threading.RLock()
        for i in range(pygame.joystick.get_count()):
            self._on_connection_event(
                pygame.event.Event(pygame.JOYDEVICEADDED, {"device_index": i})
            )
        self._event_worker_thread = threading.Thread(target=self._event_worker)
        self._event_worker_thread.start()

    @property
    def num_connected(self) -> int:
        return len(self.joysticks)

    def joystick_by_id(self, joystick_id: int) -> Optional[Joystick]:
        return self._joysticks.get(joystick_id)

    @property
    def joysticks(self) -> List[Joystick]:
        return list(self._joysticks.values())

    def remove_connection_listener(self, callback: ConnectionCallback) -> None:
        with self._lock:
            # Rebuild the list filtering out the specific callback
            self._connection_listeners = [
                l for l in self._connection_listeners if l.callback_ref() != callback
            ]

    def remove_button_listener(
        self,
        callback: _ButtonCallback,
        joystick: Joystick,
        button: Optional[Union[GamepadButton, int]] = None,
    ) -> None:
        with self._lock:
            bucket = self._button_listeners.get(joystick)
            if not bucket:
                return

            # Inline Index Resolution
            target_idx: int = -1
            if button is not None:
                if isinstance(button, int):
                    target_idx = button
                elif joystick._mapping and button.value in joystick._mapping:
                    hwid = joystick._mapping[button.value]
                    if hwid.startswith("b"):
                        target_idx = int(hwid[1:])
                    elif hwid.startswith("h"):
                        # If they pass a GamepadButton that maps to a hat,
                        # redirect to hat removal logic
                        return self.remove_hat_listener(callback, joystick, button)

            # Filter the bucket
            self._button_listeners[joystick] = [
                l
                for l in bucket
                if not (
                    l.callback_ref() == callback
                    and (button is None or l.button == target_idx)
                )
            ]

    def remove_hat_listener(
        self,
        callback: _HatCallback,
        joystick: Joystick,
        hat: Optional[Union[GamepadButton, int]] = None,
    ) -> None:
        with self._lock:
            bucket = self._hat_listeners.get(joystick)
            if not bucket:
                return

            # Inline Index Resolution
            target_idx: int = -1
            if hat is not None:
                if isinstance(hat, int):
                    target_idx = hat
                elif joystick._mapping and hat.value in joystick._mapping:
                    hwid = joystick._mapping[hat.value]
                    if hwid.startswith("h"):
                        target_idx = int(hwid[1:].split(".")[0])
                    elif hwid.startswith("b"):
                        # Redirect if the GamepadButton maps to a physical button
                        callback = cast(GamepadButtonCallback, callback)
                        return self.remove_button_listener(callback, joystick, hat)

            self._hat_listeners[joystick] = [
                l
                for l in bucket
                if not (
                    l.callback_ref() == callback
                    and (hat is None or l.hat == target_idx)
                )
            ]

    def add_hat_listener(
        self,
        callback: _HatCallback,
        joystick: Joystick,
        hat: Union[GamepadButton, int],
        direction: int = HatDirection.ANY,
    ) -> None:
        with self._lock:
            if joystick.id not in self._joysticks:
                return
        if isinstance(hat, GamepadButton) and not joystick.is_gamepad:
            raise NotAGamepadError()
        assert isinstance(joystick._mapping, dict)
        hat_idx: int
        if isinstance(hat, int):
            hat_idx = hat
        else:
            if not hat.value in joystick._mapping:
                raise UnsupportedFeatureError()
            hwid = joystick._mapping[hat.value]
            if hwid.startswith("b"):
                callback = cast(GamepadButtonCallback, callback)
                return self.add_button_listener(callback, joystick, button=hat)
            parts = hwid[1:].split(".")
            hat_idx = int(parts[0])
            direction = int(parts[1])

        dpad_button = hat if isinstance(hat, GamepadButton) else None
        callback_ref = (
            weakref.WeakMethod(callback)
            if inspect.ismethod(callback) and not inspect.isbuiltin(callback)
            else weakref.ref(callback)
        )
        listener = _HatListener(
            callback_ref=callback_ref,
            hat=hat_idx,
            joystick=joystick,
            dpad_button=dpad_button,
            hat_direction=direction,
        )
        with self._lock:
            bucket = self._hat_listeners[joystick]

            # 1. Try to find an existing listener for this callback and button
            # We resolve the weakrefs inside the generator to compare the actual objects
            existing = next(
                (
                    l
                    for l in bucket
                    if l.callback_ref() == callback and l.hat == hat_idx
                ),
                None,
            )

            if existing:
                # 2. Update the treatment if it changed (e.g., switched from int to Enum)
                if existing.dpad_button != dpad_button:
                    idx = bucket.index(existing)
                    bucket[idx] = replace(existing, dpad_button=dpad_button)
                return  # Successfully deduplicated

            # 3. If no existing match, add the new one
            bucket.append(listener)

    def add_button_listener(
        self,
        callback: _ButtonCallback,
        joystick: Joystick,
        button: Union[GamepadButton, int],
    ) -> None:
        with self._lock:
            if joystick.id not in self._joysticks:
                return
        if isinstance(button, GamepadButton) and not joystick.is_gamepad:
            raise NotAGamepadError()
        assert isinstance(joystick._mapping, dict)
        btn_idx: int
        if isinstance(button, int):
            btn_idx = button
        else:
            if not button.value in joystick._mapping:
                raise UnsupportedFeatureError()
            hwid = joystick._mapping[button.value]
            if hwid.startswith("h"):
                callback = cast(GamepadButtonCallback, callback)
                return self.add_hat_listener(callback, joystick, hat=button)
            btn_idx = int(hwid[1:])

        gamepad_button = button if isinstance(button, GamepadButton) else None
        callback_ref = (
            weakref.WeakMethod(callback)
            if inspect.ismethod(callback) and not inspect.isbuiltin(callback)
            else weakref.ref(callback)
        )
        listener = _ButtonListener(
            callback_ref=callback_ref,
            button=btn_idx,
            joystick=joystick,
            gamepad_button=gamepad_button,
        )

        with self._lock:
            bucket = self._button_listeners[joystick]

            # 1. Try to find an existing listener for this callback and button
            # We resolve the weakrefs inside the generator to compare the actual objects
            existing = next(
                (
                    l
                    for l in bucket
                    if l.callback_ref() == callback and l.button == btn_idx
                ),
                None,
            )

            if existing:
                # 2. Update the treatment if it changed (e.g., switched from int to Enum)
                if existing.gamepad_button != gamepad_button:
                    idx = bucket.index(existing)
                    bucket[idx] = replace(existing, gamepad_button=gamepad_button)
                return  # Successfully deduplicated

            # 3. If no existing match, add the new one
            bucket.append(listener)

    def add_connection_listener(self, callback: ConnectionCallback):
        callback_ref = (
            weakref.WeakMethod(callback)
            if inspect.ismethod(callback) and not inspect.isbuiltin(callback)
            else weakref.ref(callback)
        )
        new_listener = _ConnectionListener(callback_ref)

        with self._lock:
            # Deduplicate: don't add the same callback twice
            if not any(
                l.callback_ref() == callback for l in self._connection_listeners
            ):
                self._connection_listeners.append(new_listener)

    def _on_connection_event(self, event: pygame.event.Event):
        devid = event.device_index
        mapping: dict[str, str] | None = None
        pg_joystick = pygame.joystick.Joystick(devid)
        with self._lock:
            if pg_joystick.get_instance_id() in self._joysticks:
                return
        if sdl_controller.is_controller(devid):
            controller = sdl_controller.Controller.from_joystick(pg_joystick)
            mapping = controller.get_mapping()

        joystick = Joystick(pg_joystick, self, mapping)
        with self._lock:
            self._joysticks[pg_joystick.get_instance_id()] = joystick
            # Snapshot of wrappers
            listeners = list(self._connection_listeners)

        needs_cleanup = False
        for listener in listeners:
            if not listener.dispatch(joystick, True):
                needs_cleanup = True

        if needs_cleanup:
            with self._lock:
                self._connection_listeners = [
                    l for l in self._connection_listeners if l.callback_alive
                ]

    def _on_disconnection_event(self, event: pygame.event.Event):
        instance_id = event.instance_id

        with self._lock:
            # 1. Remove from manager immediately
            joystick = self._joysticks.pop(instance_id, None)
            if joystick:
                self._button_listeners.pop(joystick, None)
                self._hat_listeners.pop(joystick, None)
            callbacks = list(self._connection_listeners)

        if joystick:
            with joystick._lock:  # Acquisition is safe now
                joystick._connected = False
                try:
                    joystick._joystick.quit()
                except pygame.error:
                    pass

            # 3. Fire callbacks
            needs_cleanup = False
            for listener in callbacks:
                if not listener.dispatch(joystick, False):
                    needs_cleanup = True

            if needs_cleanup:
                with self._lock:
                    self._connection_listeners = [
                        l for l in self._connection_listeners if l.callback_alive
                    ]

    def _on_button_event(self, event: pygame.event.Event):
        with self._lock:
            joy = self._joysticks.get(event.instance_id)
            if joy is None:
                return
            listeners = self._button_listeners.get(joy)
            if listeners is None:
                return

            listeners = list(listeners)

        needs_cleanup = False
        button_state = event.type == pygame.JOYBUTTONDOWN

        for listener in listeners:
            if listener.matches(event.button):
                if listener.dispatch(button_state) == False:
                    needs_cleanup = True

        # PULSE 2: Quick Cleanup (Only if necessary)
        if needs_cleanup:
            with self._lock:
                # Prune ONLY the specific joystick's bucket
                self._button_listeners[joy] = [
                    l for l in self._button_listeners[joy] if l.callback_alive
                ]

    def _on_hat_event(self, event: pygame.event.Event):
        with self._lock:
            joy = self._joysticks.get(event.instance_id)
            if joy is None:
                return
            listeners = self._hat_listeners.get(joy)
            if listeners is None:
                return

            listeners = list(listeners)

        needs_cleanup = False
        hat = event.hat
        values = event.value
        for listener in listeners:
            if listener.matches(hat, values):
                if listener.dispatch(values) == False:
                    needs_cleanup = True

        joy._hat_motion_cache = values

        if needs_cleanup:
            with self._lock:
                # Prune ONLY the specific joystick's bucket
                self._hat_listeners[joy] = [
                    l for l in self._hat_listeners[joy] if l.callback_alive
                ]

    def _prune_all_listeners(self):
        with self._lock:
            for joy in list(self._button_listeners.keys()):
                self._button_listeners[joy] = [
                    l for l in self._button_listeners[joy] if l.callback_alive
                ]
                # If a joystick has NO listeners left, remove the bucket entirely
                if not self._button_listeners[joy]:
                    del self._button_listeners[joy]

            for joy in list(self._hat_listeners.keys()):
                self._hat_listeners[joy] = [
                    l for l in self._hat_listeners[joy] if l.callback_alive
                ]
                if not self._hat_listeners[joy]:
                    del self._hat_listeners[joy]

    def _event_worker(self):
        last_prune_time = pygame.time.get_ticks()
        PRUNE_INTERVAL = 30000  # 30 seconds in milliseconds
        clock = pygame.time.Clock()
        while self._running:
            if not pygame.joystick.get_init() or not sdl_controller.get_init():
                break

            for event in pygame.event.get():
                if event.type == pygame.JOYDEVICEADDED:
                    self._on_connection_event(event)
                elif event.type == pygame.JOYDEVICEREMOVED:
                    self._on_disconnection_event(event)
                elif event.type in (pygame.JOYBUTTONUP, pygame.JOYBUTTONDOWN):
                    self._on_button_event(event)
                elif event.type == pygame.JOYHATMOTION:
                    self._on_hat_event(event)
                elif event.type == pygame.QUIT:
                    self._running = False
                    return

            current_time = pygame.time.get_ticks()
            if current_time - last_prune_time > PRUNE_INTERVAL:
                self._prune_all_listeners()
                last_prune_time = current_time

            clock.tick(120)

    def shutdown(self):
        self._running = False
        # Only join if we aren't currently inside the worker thread
        if (
            self._event_worker_thread.is_alive()
            and threading.current_thread() != self._event_worker_thread
        ):
            self._event_worker_thread.join(timeout=1.0)

        # Final cleanup of the subsystems
        sdl_controller.quit()
        pygame.joystick.quit()


class Joystick:
    _joystick: pygame.joystick.JoystickType
    _mapping: dict[str, str] | None
    _connected: bool
    _hat_motion_cache: Tuple[int, int]
    _lock: threading.Lock

    def __init__(
        self,
        joystick: pygame.joystick.JoystickType,
        manager: JoystickManager,
        mapping: Optional[dict[str, str]],
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
        if not pygame.joystick.get_init():
            return False
        try:
            self._joystick.get_instance_id()
        except pygame.error:
            self._connected = False
            return False
        return True

    @property
    def is_gamepad(self) -> bool:
        return self._mapping is not None

    def add_button_listener(
        self,
        callback: _ButtonCallback,
        button: Union[GamepadButton, int],
    ) -> None:
        self._manager.add_button_listener(callback, self, button)

    def add_hat_listener(
        self,
        callback: _HatCallback,
        hat: Union[GamepadButton, int],
        direction: int = HatDirection.ANY,
    ) -> None:
        self._manager.add_hat_listener(callback, self, hat, direction)

    def remove_hat_listener(
        self,
        callback: _HatCallback,
        hat: Optional[Union[GamepadButton, int]] = None,
    ) -> None:
        self._manager.remove_hat_listener(callback, self, hat)

    def remove_button_listener(
        self,
        callback: _ButtonCallback,
        button: Optional[Union[GamepadButton, int]] = None,
    ) -> None:
        self._manager.remove_button_listener(callback, self, button)

    @property
    def guid(self) -> str:
        with self._lock:
            if not self.connected:
                return ""
            try:
                return self._joystick.get_guid()
            except pygame.error:
                self._check_connection()
                return ""

    @property
    def id(self) -> int:
        with self._lock:
            if not self.connected:
                return -1
            try:
                return self._joystick.get_instance_id()
            except pygame.error:
                self._check_connection()
                return -1

    @property
    def name(self) -> str:
        with self._lock:
            if not self.connected:
                return "Disconnected Joystick"
            try:
                return self._joystick.get_name()
            except pygame.error:
                self._check_connection()
                return "Disconnected Joystick"

    @property
    def power(self) -> str:
        with self._lock:
            if not self.connected:
                return "unkown"
            try:
                return self._joystick.get_power_level()
            except pygame.error:
                self._check_connection()
                return "unknown"

    def rumble(self, low: float, high: float, duration: int) -> bool:
        with self._lock:
            if not self.connected:
                return False
            try:
                return self._joystick.rumble(low, high, duration)
            except pygame.error:
                self._check_connection()
                return False

    def stop_rumble(self):
        with self._lock:
            if not self.connected:
                return
            try:
                self._joystick.stop_rumble()
            except pygame.error:
                self._check_connection()

    def _value_from_hwid(self, mapping: str) -> float:
        # 1. Handle Hats (e.g., h0.1, h0.4)
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

        # 2. Handle Buttons (e.g., b5)
        if mapping.startswith("b"):
            btn_idx = int(mapping[1:])
            return 1.0 if self._joystick.get_button(btn_idx) else 0.0

        # 3. Handle Axes (e.g., a2, -a2, +a2)
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
        self, inp: Union[GamepadButton, GamepadTrigger, GamepadStick]
    ) -> Union[bool, float]:
        with self._lock:
            value: float
            key_type: str
            try:
                if not self.connected:
                    raise UnsupportedFeatureError()
                key_type = self._key_type_from_mapping(inp.value)
                value = self._value_from_mapping(inp.value, key_type)
            except (pygame.error, UnsupportedFeatureError):
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
                    raise IndexOutOfRangeError()
                return self._joystick.get_button(button_idx)
            except pygame.error:
                return False

    def get_axis(self, axis_idx: int) -> Annotated[float, Ge(-1.0), Le(1.0)]:
        with self._lock:
            if not self.connected:
                return -1.0
            try:
                if self._joystick.get_numaxes() <= axis_idx:
                    raise IndexOutOfRangeError()
                return self._joystick.get_axis(axis_idx)
            except pygame.error:
                return -1.0

    def get_hat(self, hat_idx: int) -> Tuple[int, int]:
        with self._lock:
            if not self.connected:
                return (0, 0)
            try:
                if self._joystick.get_numhats() <= hat_idx:
                    raise IndexOutOfRangeError()
                x, y = self._joystick.get_hat(hat_idx)
                return (int(x), int(y))
            except pygame.error:
                return (0, 0)

    def get_ball(self, ball_idx: int) -> Tuple[float, float]:
        with self._lock:
            if not self.connected:
                return (0, 0)
            try:
                if self._joystick.get_numballs() <= ball_idx:
                    raise IndexOutOfRangeError()
                return self._joystick.get_ball(ball_idx)
            except pygame.error:
                return (0, 0)

    @property
    def num_buttons(self) -> int:
        with self._lock:
            if not self.connected:
                return 0
            try:
                return self._joystick.get_numbuttons()
            except pygame.error:
                self._check_connection()
                return 0

    @property
    def num_balls(self) -> int:
        with self._lock:
            if not self.connected:
                return 0
            try:
                return self._joystick.get_numballs()
            except pygame.error:
                self._check_connection()
                return 0

    @property
    def num_axes(self) -> int:
        with self._lock:
            if not self.connected:
                return 0
            try:
                return self._joystick.get_numaxes()
            except pygame.error:
                self._check_connection()
                return 0

    @property
    def num_hats(self) -> int:
        with self._lock:
            if not self.connected:
                return 0
            try:
                return self._joystick.get_numhats()
            except pygame.error:
                self._check_connection()
                return 0

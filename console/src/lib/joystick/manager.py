from __future__ import annotations
from collections import defaultdict
from contextlib import nullcontext
from pathlib import Path
import threading
from typing import Callable, Self, TYPE_CHECKING, cast

from lib.joystick.inputs import GamepadButton, HatDirection

from lib.joystick.joystick import Joystick
import os

if TYPE_CHECKING:
    import pygame as _

    pygame = _
    from pygame._sdl2 import controller as _

    sdl_controller = _

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"
os.environ["SDL_NO_SIGNAL_HANDLERS"] = "1"
_IS_VIRTUALIZED = os.environ.get("VIRTUALIZED_UDEV")

from lib.joystick.listeners import (
    CallbackFactory,
    GamepadHatCallback,
    GamepadButtonCallback,
    ButtonCallback,
    HatMotionCallback,
    ConnectionCallback,
)
from lib.joystick.exceptions import NotAGamepadError, UnsupportedFeatureError


class JoystickManager:
    _joysticks: dict[int, Joystick]
    _initialized: bool
    _button_listeners: dict[Joystick, list[ButtonCallback]]
    _hat_listeners: dict[Joystick, list[HatMotionCallback]]
    _connection_listeners: list[ConnectionCallback]
    _running: bool
    _lock: threading.RLock | nullcontext
    _event_worker_thread: threading.Thread | None
    _threaded: bool
    _last_virtualized_sync_time: int

    _instance: JoystickManager | None = None
    _creation_lock: threading.Lock = threading.Lock()
    _pg = pygame if TYPE_CHECKING else None
    _sdl_c = sdl_controller if TYPE_CHECKING else None

    def __new__(cls, *args, **kwargs) -> Self:
        if not JoystickManager._instance:
            with JoystickManager._creation_lock:
                if not JoystickManager._instance:
                    JoystickManager._instance = super().__new__(cls)
        return cast(Self, JoystickManager._instance)

    def __init__(self, threaded: bool = True) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._connection_listeners = []
        self._button_listeners = defaultdict(list)
        self._hat_listeners = defaultdict(list)
        self._joysticks = {}
        self._threaded = threaded
        if self._threaded:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"
        import pygame
        from pygame._sdl2 import controller as sdl_controller

        JoystickManager._pg = pygame
        JoystickManager._sdl_c = sdl_controller
        self._pg.display.init()
        self._pg.joystick.init()
        self._sdl_c.init()
        self._last_virtualized_sync_time = 0
        if self._threaded:
            self._lock = threading.RLock()
            self._running = True
            self._event_worker_thread = threading.Thread(target=self._event_worker)
            self._event_worker_thread.start()
        else:
            self._lock = nullcontext()
            self._event_worker_thread = None

    @property
    def num_connected(self) -> int:
        with self._lock:
            return len(self.joysticks)

    def joystick_by_id(self, joystick_id: int) -> Joystick | None:
        with self._lock:
            return self._joysticks.get(joystick_id)

    @property
    def joysticks(self) -> list[Joystick]:
        with self._lock:
            return list(self._joysticks.values())

    def _unregister_button_listener(
        self,
        joystick: Joystick,
        callback: Callable | None = None,
        hwid: int | None = None,
    ) -> None:
        if callback is None and hwid is None:
            return
        with self._lock:
            bucket = self._button_listeners.get(joystick)
            if not bucket:
                return

            self._button_listeners[joystick] = [
                l
                for l in bucket
                if not (
                    (callback is None or l.callback_ref() == callback)
                    and (hwid is None or l.hwid == hwid)
                )
            ]

    def _unregister_hat_listener(
        self,
        joystick: Joystick,
        callback: Callable | None = None,
        hwid: int | None = None,
    ) -> None:
        if callback is None and hwid is None:
            return

        with self._lock:
            bucket = self._hat_listeners.get(joystick)
            if not bucket:
                return

            self._hat_listeners[joystick] = [
                l
                for l in bucket
                if not (
                    (callback is None or l.callback_ref() == callback)
                    and (hwid is None or l.hwid == hwid)
                )
            ]

    def remove_button_listeners(self, joystick: Joystick, button: int) -> None:
        self._unregister_button_listener(joystick, hwid=button)

    def remove_hat_listeners(self, joystick: Joystick, hat: int) -> None:
        self._unregister_hat_listener(joystick, hwid=hat)

    def remove_gp_button_listeners(
        self, joystick: Joystick, button: GamepadButton
    ) -> None:
        if joystick._mapping is None:
            raise NotAGamepadError()
        elif button.value not in joystick._mapping:
            return
        hwid_str = joystick._mapping[button.value]
        if hwid_str.startswith("b"):
            self._unregister_button_listener(joystick, hwid=int(hwid_str[1:]))
        elif hwid_str.startswith("h"):
            self._unregister_hat_listener(
                joystick, hwid=int(hwid_str[1:].split(".")[0])
            )

    def disconnect_button_callback(
        self, joystick: Joystick, callback: Callable
    ) -> None:
        self._unregister_button_listener(joystick, callback=callback)

    def disconnect_hat_callback(self, joystick: Joystick, callback: Callable) -> None:
        self._unregister_hat_listener(joystick, callback=callback)

    def disconnect_gp_button_callback(
        self, joystick: Joystick, callback: Callable
    ) -> None:
        with self._lock:
            if joystick in self._hat_listeners:
                self._hat_listeners[joystick] = [
                    l
                    for l in self._hat_listeners[joystick]
                    if not (l.callback_ref() == callback)
                ]
            if joystick in self._button_listeners:
                self._button_listeners[joystick] = [
                    l
                    for l in self._button_listeners[joystick]
                    if not (l.callback_ref() == callback)
                ]

    def remove_button_listener(
        self, joystick: Joystick, callback: Callable, button: int
    ) -> None:
        self._unregister_button_listener(joystick, callback, button)

    def remove_hat_listener(
        self, joystick: Joystick, callback: Callable, hat: int
    ) -> None:
        self._unregister_hat_listener(joystick, callback, hat)

    def remove_gp_button_listener(
        self, joystick: Joystick, callback: Callable, button: GamepadButton
    ) -> None:
        if joystick._mapping is None:
            raise NotAGamepadError()
        elif button.value not in joystick._mapping:
            return
        hwid_str = joystick._mapping[button.value]
        if hwid_str.startswith("b"):
            self._unregister_button_listener(
                joystick, callback=callback, hwid=int(hwid_str[1:])
            )
        elif hwid_str.startswith("h"):
            self._unregister_hat_listener(
                joystick, callback=callback, hwid=int(hwid_str[1:].split(".")[0])
            )

    def _register_hat_listener(self, listener: HatMotionCallback) -> None:
        with self._lock:
            joystick = listener.joystick
            if joystick.id not in self._joysticks:
                return
            self._hat_listeners[joystick] = [
                l
                for l in self._hat_listeners[joystick]
                if not (
                    l.callback_ref() == listener.callback_ref()
                    and l.hwid == listener.hwid
                )
            ]  # deduplication for different subtypes of hat callbacks
            self._hat_listeners[joystick].append(listener)

    def _register_button_listener(self, listener: ButtonCallback) -> None:
        with self._lock:
            joystick = listener.joystick
            if joystick.id not in self._joysticks:
                return
            self._button_listeners[joystick] = [
                l
                for l in self._button_listeners[joystick]
                if not (
                    l.callback_ref() == listener.callback_ref()
                    and l.hwid == listener.hwid
                )
            ]  # deduplication for different subtypes of button callbacks
            self._button_listeners[joystick].append(listener)

    def add_hat_listener(
        self,
        joystick: Joystick,
        callback: Callable[[Joystick, int, HatDirection], None],
        hat: int,
    ) -> None:
        listener = CallbackFactory.create_hat_motion_callback(
            joystick=joystick, callback=callback, hwid=hat
        )
        self._register_hat_listener(listener)

    def add_hat_direction_listener(
        self,
        joystick: Joystick,
        callback: Callable[[Joystick, int, bool], None],
        hat: int,
        direction: HatDirection,
    ) -> None:
        listener = CallbackFactory.create_directed_hat_motion_callback(
            joystick=joystick, callback=callback, hwid=hat, direction=direction
        )
        self._register_hat_listener(listener)

    def add_button_listener(
        self,
        joystick: Joystick,
        callback: Callable[[Joystick, int, bool], None],
        button: int,
    ) -> None:
        listener = CallbackFactory.create_button_callback(
            joystick=joystick, callback=callback, hwid=button
        )
        self._register_button_listener(listener)

    def add_gamepad_button_listener(
        self,
        joystick: Joystick,
        callback: Callable[[Joystick, GamepadButton, bool], None],
        button: GamepadButton,
    ) -> None:
        listener = CallbackFactory.create_gamepad_button_callback(
            joystick=joystick, callback=callback, button=button
        )
        if isinstance(listener, GamepadHatCallback):
            self._register_hat_listener(listener)
        elif isinstance(listener, GamepadButtonCallback):
            self._register_button_listener(listener)

    def add_connection_listener(self, callback: Callable[[Joystick, bool], None]):
        new_listener = CallbackFactory.create_connection_callback(callback=callback)

        with self._lock:
            if not any(
                l.callback_ref() == callback for l in self._connection_listeners
            ):
                self._connection_listeners.append(new_listener)

    def remove_connection_listener(
        self, callback: Callable[[Joystick, bool], None]
    ) -> None:
        with self._lock:
            self._connection_listeners = [
                l for l in self._connection_listeners if l.callback_ref() != callback
            ]

    def _on_connection_event(self, event: JoystickManager._pg.event.Event):
        devid = event.device_index
        mapping: dict[str, str] | None = None
        try:
            pg_joystick = self._pg.joystick.Joystick(devid)
            print(devid)
        except pygame.error:
            return
        with self._lock:
            if pg_joystick.get_instance_id() in self._joysticks:
                return
        if self._sdl_c.is_controller(devid):
            controller = self._sdl_c.Controller.from_joystick(pg_joystick)
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

    def _on_disconnection_event(self, event: JoystickManager._pg.event.Event):
        instance_id = event.instance_id

        with self._lock:
            joystick = self._joysticks.pop(instance_id, None)
            if joystick:
                self._button_listeners.pop(joystick, None)
                self._hat_listeners.pop(joystick, None)
            callbacks = list(self._connection_listeners)

        if joystick:
            with joystick._lock:
                joystick._connected = False
                try:
                    joystick._joystick.quit()
                except self._pg.error:
                    pass

            needs_cleanup = False
            for listener in callbacks:
                if not listener.dispatch(joystick, False):
                    needs_cleanup = True

            if needs_cleanup:
                with self._lock:
                    self._connection_listeners = [
                        l for l in self._connection_listeners if l.callback_alive
                    ]

    def _on_button_event(self, event: JoystickManager._pg.event.Event):
        with self._lock:
            joy = self._joysticks.get(event.instance_id)
            if joy is None:
                return
            listeners = self._button_listeners.get(joy)
            if listeners is None:
                return

            listeners = list(listeners)

        needs_cleanup = False
        button_state = event.type == self._pg.JOYBUTTONDOWN

        for listener in listeners:
            if listener.matches(event.button):
                if listener.dispatch(button_state) == False:
                    needs_cleanup = True

        if needs_cleanup:
            with self._lock:
                if joy not in self._button_listeners:
                    return
                self._button_listeners[joy] = [
                    l for l in self._button_listeners[joy] if l.callback_alive
                ]

    def _on_hat_event(self, event: JoystickManager._pg.event.Event):
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
                if joy not in self._button_listeners:
                    return
                self._hat_listeners[joy] = [
                    l for l in self._hat_listeners[joy] if l.callback_alive
                ]

    def prune_all_listeners(self):
        with self._lock:
            for joy in list(self._button_listeners.keys()):
                self._button_listeners[joy] = [
                    l for l in self._button_listeners[joy] if l.callback_alive
                ]
                if not self._button_listeners[joy]:
                    del self._button_listeners[joy]

            for joy in list(self._hat_listeners.keys()):
                self._hat_listeners[joy] = [
                    l for l in self._hat_listeners[joy] if l.callback_alive
                ]
                if not self._hat_listeners[joy]:
                    del self._hat_listeners[joy]

    def _event_worker(self):
        last_prune_time = self._pg.time.get_ticks()
        PRUNE_INTERVAL = 30000  # 30 seconds in milliseconds
        clock = self._pg.time.Clock()
        while self._running:
            self._event_handler()

            current_time = self._pg.time.get_ticks()
            if current_time - last_prune_time > PRUNE_INTERVAL:
                self.prune_all_listeners()
                last_prune_time = current_time

            clock.tick(120)

    def _event_handler(self):
        if not self._pg.joystick.get_init() or not self._sdl_c.get_init():
            return

        for event in self._pg.event.get():
            if event.type == self._pg.JOYDEVICEADDED:
                self._on_connection_event(event)
            elif event.type == self._pg.JOYDEVICEREMOVED:
                self._on_disconnection_event(event)
            elif event.type in (
                self._pg.JOYBUTTONUP,
                self._pg.JOYBUTTONDOWN,
            ):
                self._on_button_event(event)
            elif event.type == self._pg.JOYHATMOTION:
                self._on_hat_event(event)
            elif event.type == self._pg.QUIT:
                self._running = False
                return

        if _IS_VIRTUALIZED:
            SYNC_INTERVAL = 1000  # 1 seconds
            current_time = self._pg.time.get_ticks()
            if current_time - self._last_virtualized_sync_time > SYNC_INTERVAL:
                self._last_virtualized_sync_time = current_time
                with self._lock:
                    new_count = len(list(Path("/dev/input/").glob("js*")))
                    if self._pg.joystick.get_count() < new_count:
                        for instance_id in list(self._joysticks.keys()):
                                self._on_disconnection_event(
                                    self._pg.event.Event(
                                        self._pg.JOYDEVICEREMOVED,
                                        {"instance_id": instance_id},
                                    )
                                )
                        while self._pg.joystick.get_count() < len(list(Path("/dev/input/").glob("js*"))):
                            self._pg.event.clear()
                            self._pg.joystick.quit()
                            self._sdl_c.quit()
                            self._pg.time.wait(100)
                            self._pg.joystick.init()
                            self._sdl_c.init()


    def spin(self) -> None:
        self._event_handler()

    def shutdown(self):
        self._running = False
        if self._threaded and self._event_worker_thread is not None:
            if (
                self._event_worker_thread.is_alive()
                and threading.current_thread() != self._event_worker_thread
            ):
                self._event_worker_thread.join(timeout=1.0)
        self._sdl_c.quit()
        self._pg.joystick.quit()

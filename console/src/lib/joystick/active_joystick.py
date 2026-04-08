import threading
import weakref

from lib.joystick.joystick import Joystick
from typing import TYPE_CHECKING, Callable

from lib.joystick.listeners import CallbackFactory


class _ActiveJoystick:
    _selected_joystick: Joystick | None
    _on_select_listeners: list[weakref.WeakMethod | weakref.ReferenceType]
    _listeners_lock: threading.RLock
    _dispatch_worker_thread: threading.Thread
    _fallback_joystick: Joystick | None

    def __init__(self, joystick: Joystick | None = None, strict_mode: bool = False):
        self._selected_joystick = joystick
        self._on_select_listeners = []
        self._listeners_lock = threading.RLock()
        if not strict_mode:
            self._fallback_joystick = Joystick(None, None, None)  # type: ignore
            self._fallback_joystick._connected = False
        else:
            self._fallback_joystick = None

    @property
    def selected(self) -> Joystick | None:
        return self._selected_joystick

    @selected.setter
    def selected(self, joy: Joystick | None) -> None:
        self._selected_joystick = joy
        thread = threading.Thread(target=self._dispatch_listeners, daemon=True)
        thread.start()

    def _dispatch_listeners(self) -> None:
        with self._listeners_lock:
            listeners = list(self._on_select_listeners)
        needs_cleaup = False
        for l in listeners:
            callback = l()
            if callback is None:
                needs_cleaup = True
            else:
                try:
                    callback()
                except Exception as e:
                    print(f"ActiveJoystick Listener Error: {e}")

        if needs_cleaup:
            with self._listeners_lock:
                self._on_select_listeners = [
                    l for l in self._on_select_listeners if l()
                ]

    def add_on_select_listener(self, callback: Callable) -> None:
        with self._listeners_lock:
            if any(l() == callback for l in self._on_select_listeners):
                return
            else:
                listener = CallbackFactory.create_callback_ref(callback)
                self._on_select_listeners.append(listener)

    def __getattr__(self, name):
        if self._selected_joystick:
            return getattr(self._selected_joystick, name)
        elif self._fallback_joystick:
            return getattr(self._fallback_joystick, name)
        else:
            raise AttributeError("No joystick currently selected.")


if TYPE_CHECKING:

    class ActiveJoystick(_ActiveJoystick, Joystick): ...
else:
    ActiveJoystick = _ActiveJoystick

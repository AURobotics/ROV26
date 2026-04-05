from lib.joystick.joystick import Joystick
from typing import TYPE_CHECKING


class _ActiveJoystick:
    _selected_joystick: Joystick | None

    def __init__(self, joystick: Joystick | None = None):
        self._selected_joystick = joystick

    @property
    def selected(self) -> Joystick | None:
        return self._selected_joystick

    @selected.setter
    def selected(self, joy: Joystick | None) -> None:
        self._selected_joystick = joy

    def __getattr__(self, name):
        if self._selected_joystick:
            return getattr(self._selected_joystick, name)
        raise AttributeError("No joystick currently selected.")


if TYPE_CHECKING:

    class ActiveJoystick(_ActiveJoystick, Joystick): ...
else:
    ActiveJoystick = _ActiveJoystick

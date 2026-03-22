from typing import Optional

from lib.device.joystick import Joystick


class ActiveJoystick:
    _joystick: Optional[Joystick]

    def __init__(self, joystick: Optional[Joystick] = None):
        self._joystick = joystick

    @property
    def selected(self) -> Optional[Joystick]:
        return self._joystick

    @selected.setter
    def selected(self, joy: Optional[Joystick]) -> None:
        self._joystick = joy

    def __getattr__(self, name):
        if self._joystick:
            return getattr(self._joystick, name)
        raise AttributeError("No joystick currently selected.")
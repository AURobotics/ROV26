from typing import Optional

from lib.device.joystick import Joystick

class ActiveJoystick(Joystick):
    _joystick: Optional[Joystick]

    def __init__(self, joystick: Optional[Joystick] = None): ...
    @property
    def selected(self) -> Optional[Joystick]: ...
    @selected.setter
    def selected(self, joy: Optional[Joystick]) -> None: ...

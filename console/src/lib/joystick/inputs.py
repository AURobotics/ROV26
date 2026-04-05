from enum import Enum, IntFlag


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
    CENTERED = 0
    UP = 1
    RIGHT = 2
    DOWN = 4
    LEFT = 8
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

"""
Wrapper for PyGame joysticks.
Manages the following:
   - Choosing one or none of the currently connected gamepads
   - Regularly checking for, presenting and managing connection changes
   - Providing an event-based interface for tracking
"""

from enum import IntFlag, Enum
from typing import (
    List,
    Optional,
    Callable,
    Tuple,
    Annotated,
    TypeAlias,
    overload,
)
from annotated_types import Ge, Le
import pygame

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

    def __str__(self) -> str: ...

GamepadButtonCallback: TypeAlias = Callable[[Joystick, GamepadButton, bool], None]
JoystickButtonCallback: TypeAlias = Callable[[Joystick, int, bool], None]
HatMotionCallback: TypeAlias = Callable[[Joystick, int, HatDirection], None]
DirectedHatMotionCallback: TypeAlias = Callable[[Joystick, int, bool], None]
ConnectionCallback: TypeAlias = Callable[[Joystick, bool], None]

class JoystickManager:
    @property
    def num_connected(self) -> int: ...
    def joystick_by_id(self, joystick_id: int) -> Optional[Joystick]: ...
    @property
    def joysticks(self) -> List[Joystick]: ...
    def remove_connection_listener(self, callback: ConnectionCallback): ...
    @overload
    def remove_button_listener(
        self,
        callback: GamepadButtonCallback,
        joystick: Joystick,
        button: Optional[GamepadButton] = None,
    ): ...
    @overload
    def remove_button_listener(
        self,
        callback: JoystickButtonCallback,
        joystick: Joystick,
        button: Optional[int] = None,
    ): ...
    @overload
    def remove_hat_listener(
        self,
        callback: GamepadButtonCallback,
        joystick: Joystick,
        hat: Optional[GamepadButton] = None,
    ): ...
    @overload
    def remove_hat_listener(
        self, callback: HatMotionCallback, joystick: Joystick, hat: Optional[int] = None
    ): ...
    @overload
    def remove_hat_listener(
        self,
        callback: DirectedHatMotionCallback,
        joystick: Joystick,
        hat: Optional[int] = None,
    ): ...
    @overload
    def add_hat_listener(
        self,
        callback: GamepadButtonCallback,
        joystick: Joystick,
        hat: GamepadButton,
    ): ...
    @overload
    def add_hat_listener(
        self,
        callback: HatMotionCallback,
        joystick: Joystick,
        hat: int,
    ): ...
    @overload
    def add_hat_listener(
        self,
        callback: DirectedHatMotionCallback,
        joystick: Joystick,
        hat: int,
        direction: HatDirection,
    ): ...
    @overload
    def add_hat_listener(
        self,
        callback: HatMotionCallback,
        joystick: Joystick,
        hat: int,
        direction: int,
    ): ...
    @overload
    def add_button_listener(
        self,
        callback: JoystickButtonCallback,
        joystick: Joystick,
        button: int,
    ): ...
    @overload
    def add_button_listener(
        self,
        callback: GamepadButtonCallback,
        joystick: Joystick,
        button: GamepadButton,
    ): ...
    def add_connection_listener(self, callback: ConnectionCallback): ...
    def shutdown(self): ...

class Joystick:
    @property
    def connected(self) -> bool: ...
    @property
    def is_gamepad(self) -> bool: ...
    @property
    def guid(self) -> str: ...
    @property
    def id(self) -> int: ...
    @property
    def name(self) -> str: ...
    @property
    def power(self) -> str: ...
    def rumble(self, low: float, high: float, duration: int) -> bool: ...
    def stop_rumble(self): ...
    @overload
    def get_gpinput(self, inp: GamepadButton) -> bool: ...
    @overload
    def get_gpinput(self, inp: GamepadStick) -> Annotated[float, Ge(-1.0), Le(1.0)]: ...
    @overload
    def get_gpinput(
        self, inp: GamepadTrigger
    ) -> Annotated[float, Ge(0.0), Le(1.0)]: ...
    def get_button(self, button_idx: int) -> bool: ...
    def get_axis(self, axis_idx: int) -> Annotated[float, Ge(-1.0), Le(1.0)]: ...
    def get_hat(self, hat_idx: int) -> Tuple[int, int]: ...
    def get_ball(self, ball_idx: int) -> Tuple[float, float]: ...
    @property
    def num_buttons(self) -> int: ...
    @property
    def num_balls(self) -> int: ...
    @property
    def num_axes(self) -> int: ...
    @property
    def num_hats(self) -> int: ...
    @overload
    def remove_button_listener(
        self,
        callback: GamepadButtonCallback,
        button: Optional[GamepadButton] = None,
    ): ...
    @overload
    def remove_button_listener(
        self,
        callback: JoystickButtonCallback,
        button: Optional[int] = None,
    ): ...
    @overload
    def remove_hat_listener(
        self,
        callback: GamepadButtonCallback,
        hat: Optional[GamepadButton] = None,
    ): ...
    @overload
    def remove_hat_listener(
        self, callback: HatMotionCallback, hat: Optional[int] = None
    ): ...
    @overload
    def remove_hat_listener(
        self,
        callback: DirectedHatMotionCallback,
        hat: Optional[int] = None,
    ): ...
    @overload
    def add_hat_listener(
        self,
        callback: GamepadButtonCallback,
        hat: GamepadButton,
    ): ...
    @overload
    def add_hat_listener(
        self,
        callback: HatMotionCallback,
        hat: int,
    ): ...
    @overload
    def add_hat_listener(
        self,
        callback: DirectedHatMotionCallback,
        hat: int,
        direction: HatDirection,
    ): ...
    @overload
    def add_hat_listener(
        self,
        callback: HatMotionCallback,
        hat: int,
        direction: int,
    ): ...
    @overload
    def add_button_listener(
        self,
        callback: JoystickButtonCallback,
        button: int,
    ): ...
    @overload
    def add_button_listener(
        self,
        callback: GamepadButtonCallback,
        button: GamepadButton,
    ): ...

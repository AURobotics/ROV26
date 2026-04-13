import threading
from dataclasses import dataclass
from time import sleep
from typing import Any, cast
from console.comms.stm32 import Stm32
from core.math.exponential_filter import ExponentialFilter
from hal.joystick.inputs import GamepadButton, GamepadStick, GamepadTrigger
from hal.joystick.joystick import Joystick
from hal.joystick.active_joystick import ActiveJoystick
from console.comms.messages import (
    CommandData,
    MessageType,
    SensorsData,
)

ToggleButtons = {
    GamepadButton.SOUTH: "led",
    GamepadButton.NORTH: "gripper",
    GamepadButton.EAST: "arm",
}


@dataclass(slots=True)
class CommandState:
    led: bool = False
    gripper: bool = False
    arm: bool = False
    force_x: ExponentialFilter = ExponentialFilter(setting_time=0.5)
    force_y: ExponentialFilter = ExponentialFilter(setting_time=0.5)
    force_z: ExponentialFilter = ExponentialFilter(setting_time=0.5)
    yaw: ExponentialFilter = ExponentialFilter(setting_time=0.5)
    pitch: ExponentialFilter = ExponentialFilter(setting_time=0.5)
    roll: ExponentialFilter = ExponentialFilter(setting_time=0.5)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key) -> Any:
        return getattr(self, key)


_empty_sensors = SensorsData(0, 0, 0, 0, 0, [0, 0, 0, 0, 0, 0, 0, 0])


class CommunicationManager:
    _stm: Stm32
    _joystick: ActiveJoystick
    _sensor_cache: SensorsData
    _command_cache: CommandState
    _data_ready_event: threading.Event
    _killswitch: bool
    _incoming_thread: threading.Thread
    _outgoing_thread: threading.Thread

    def __init__(self, stm: Stm32, joystick: ActiveJoystick):
        self._stm = stm
        self._joystick = joystick
        self._sensor_cache = _empty_sensors
        self._command_cache = CommandState()
        self._data_ready_event = threading.Event()
        self._killswitch = False
        self._incoming_thread = threading.Thread(
            target=self._incoming_loop, daemon=True
        )
        self._incoming_thread.start()
        self._outgoing_thread = threading.Thread(
            target=self._outgoing_loop, daemon=True
        )
        self._outgoing_thread.start()
        if self._joystick.selected:
            self._register_button_listeners()
        self._joystick.add_on_select_listener(self._register_button_listeners)

    def _register_button_listeners(self):
        for btn in ToggleButtons.keys():
            self._joystick.add_gamepad_button_listener(self._on_joystick_button, btn)

    def _on_joystick_button(self, _: Joystick, button: GamepadButton, is_pressed: bool):
        if self._stm.connected:
            if is_pressed:
                toggle: str = ToggleButtons[button]
                self._command_cache[toggle] = not self._command_cache[toggle]

    @property
    def sensor_cache(self) -> SensorsData:
        return self._sensor_cache

    def _outgoing_loop(self):
        while not self._killswitch:
            self._data_ready_event.wait()
            if self._stm.has_incoming and self._joystick.selected:
                print("Sending")
                payload = self._controller_payload()
                self._stm.send(payload)
                self._data_ready_event.clear()

    def _incoming_loop(self):
        while not self._killswitch:
            sleep(0.015)

            if not self._stm.connected:
                self._sensor_cache = _empty_sensors
                continue

            if not self._stm.has_incoming:
                continue

            incoming = self._stm.receive()
            if not incoming:
                continue

            message_type = MessageType.from_payload(incoming)
            if message_type == MessageType.READY:
                self._data_ready_event.set()
            elif message_type == MessageType.SENSORS:
                incoming = cast(SensorsData, incoming)
                self._sensor_cache = incoming

    def _controller_payload(self):
        # Toggle-based controls
        control_word = int(self._command_cache.led) << 0
        control_word |= int(self._command_cache.gripper) << 1
        control_word |= int(self._command_cache.arm) << 2

        # Event-based controls
        joy = self._joystick
        control_word |= int(joy.get_gpinput(GamepadButton.DPAD_UP)) << 3
        control_word |= int(joy.get_gpinput(GamepadButton.DPAD_DOWN)) << 4
        force_x = self._command_cache.force_x.filter_step(
            -joy.get_gpinput(GamepadStick.LEFT_Y)
        )
        force_y = self._command_cache.force_y.filter_step(
            joy.get_gpinput(GamepadStick.LEFT_X)
        )
        force_z = self._command_cache.force_z.filter_step(
            joy.get_gpinput(GamepadTrigger.LEFT_TRIGGER)
            - joy.get_gpinput(GamepadTrigger.RIGHT_TRIGGER)
        )
        yaw = self._command_cache.roll.filter_step(
            joy.get_gpinput(GamepadStick.RIGHT_X)
        )
        pitch = self._command_cache.pitch.filter_step(
            joy.get_gpinput(GamepadStick.RIGHT_Y)
        )
        roll = self._command_cache.yaw.filter_step(
            joy.get_gpinput(GamepadButton.RIGHT_SHOULDER)
            - joy.get_gpinput(GamepadButton.LEFT_SHOULDER)
        )

        payload = CommandData(
            control=control_word,
            x=force_x,
            y=force_y,
            z=force_z,
            roll=roll,
            pitch=pitch,
            yaw=yaw,
        )
        print(payload)
        return payload

    def __del__(self):
        self._killswitch = True
        if self._incoming_thread.is_alive():
            self._incoming_thread.join()
        if self._outgoing_thread.is_alive():
            self._outgoing_thread.join()

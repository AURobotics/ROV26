import struct
import threading
from dataclasses import dataclass, field
from time import sleep
from typing import Any, Annotated, cast
from core.math.exponential_filter import ExponentialFilter
from hal.serial.stm32 import STM32
from hal.joystick.inputs import GamepadButton, GamepadStick, GamepadTrigger
from hal.joystick.joystick import Joystick
from hal.joystick.active_joystick import ActiveJoystick
from console.comms.messages import (
    CommandData,
    MessageType,
    Constants,
    Message,
    SensorsData,
)

ToggleButtons = {
    GamepadButton.SOUTH: "led",
    GamepadButton.NORTH: "gripper",
    GamepadButton.EAST: "arm",
}


@dataclass(slots=True)
class SensorCache:
    led: bool = False
    gripper: bool = False
    arm: bool = False
    yaw: float = 0.0
    pitch: float = 0.0
    roll: float = 0.0
    depth: float = 0.0
    thrusters: Annotated[list[float], 8] = field(default_factory=lambda: [0.0] * 8)


@dataclass(slots=True)
class CommandStateCache:
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
        self.__setattr__(key, value)

    def __getitem__(self, key) -> Any:
        return self.__getattribute__(key)


class CommunicationManager:
    _serial: STM32
    _joystick: ActiveJoystick
    _sensor_cache: SensorCache
    _command_cache: CommandStateCache
    _data_ready_event: threading.Event
    _killswitch: bool
    _serial_incoming_thread: threading.Thread
    _serial_outgoing_thread: threading.Thread

    def __init__(self, serial: STM32, joystick: ActiveJoystick):
        self._serial = serial
        self._joystick = joystick
        self._sensor_cache = SensorCache()
        self._command_cache = CommandStateCache()
        self._data_ready_event = threading.Event()
        self._killswitch = False
        self._serial_incoming_thread = threading.Thread(
            target=self._serial_incoming_loop, daemon=True
        )
        self._serial_incoming_thread.start()
        self._serial_outgoing_thread = threading.Thread(
            target=self._serial_outgoing_loop, daemon=True
        )
        self._serial_outgoing_thread.start()
        if self._joystick.selected:
            self._set_button_listeners()
        self._joystick.add_on_select_listener(self._set_button_listeners)

    def _set_button_listeners(self):
        for btn in ToggleButtons.keys():
            self._joystick.add_gamepad_button_listener(self._controller_toggles, btn)

    def _controller_toggles(self, _: Joystick, button: GamepadButton, is_pressed: bool):
        if self._serial.serial_ready:
            if is_pressed:
                toggle: str = ToggleButtons[button]
                self._command_cache[toggle] = not self._command_cache[toggle]

    @property
    def sensor_cache(self) -> SensorCache:
        return self._sensor_cache

    def _serial_outgoing_loop(self):
        while not self._killswitch:
            self._data_ready_event.wait()
            if self._serial.serial_ready and self._joystick.selected:
                print("Sending")
                payload = self._serial_controller_payload()
                self._serial.send(payload)
                self._data_ready_event.clear()

    def _serial_incoming_loop(self):
        synced = False
        detected_rx = None

        while not self._killswitch:
            sleep(0.015)

            if not self._serial.serial_ready:
                # Reset the transient part of the cache
                # Non-transient keys include: controller['leds_and_valves']
                self._sensor_cache = SensorCache()
                synced = False
                detected_rx = None
                continue

            if not self._serial.incoming:
                continue
            if not synced:
                byte = self._serial.recieve(1)
                if byte and byte[0] == Constants.SYNC_BYTE:
                    synced = True
                continue

            if detected_rx is None:
                byte = self._serial.recieve(1)
                if not byte:
                    synced = False
                    continue
                msg_type = byte[0]
                try:
                    detected_rx = MessageType.from_type(msg_type)
                except ValueError:
                    synced = False
                    continue
            if detected_rx == MessageType.READY:
                self._data_ready_event.set()
            elif detected_rx == MessageType.SENSORS:
                raw = self._serial.recieve(MessageType.SENSORS.size)
                if raw and len(raw) == MessageType.SENSORS.size:
                    self._parse_incoming(raw)

            synced = False
            detected_rx = None

    def _parse_incoming(self, raw_data: bytes):
        try:
            data = cast(SensorsData, Message.decode(MessageType.SENSORS, raw_data))
            self._sensor_cache.led = data.led
            self._sensor_cache.depth = data.depth
            self._sensor_cache.yaw = data.yaw
            self._sensor_cache.pitch = data.pitch
            self._sensor_cache.roll = data.roll
            self._sensor_cache.thrusters = list(data.thrusters)

        except struct.error as e:
            print(f"Decode error: {e}")

    def _serial_controller_payload(self):
        joy = self._joystick
        control_word = int(self._command_cache.led) << 0

        control_word |= int(self._command_cache.gripper) << 1
        control_word |= int(self._command_cache.arm) << 2
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
        return Message.encode(MessageType.COMMAND, payload)

    def __del__(self):
        self._killswitch = True
        if self._serial_incoming_thread.is_alive():
            self._serial_incoming_thread.join()
        if self._serial_outgoing_thread.is_alive():
            self._serial_outgoing_thread.join()

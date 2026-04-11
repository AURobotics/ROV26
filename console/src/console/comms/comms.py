import struct
from threading import Event, Thread
from time import sleep
from typing import TypedDict, Annotated, cast
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
    GamepadButton.SOUTH: "LED",
    GamepadButton.NORTH: "GRIPPER",
    GamepadButton.EAST: "ARM",
}


class SensorCache(TypedDict):
    thrusters: Annotated[list[float], 8]
    status: dict
    yaw: float
    pitch: float
    roll: float
    depth: float


class CommandStateCache(TypedDict):
    forces: Annotated[list[ExponentialFilter], 6]


class CommunicationManager:
    """Competition-specific handler for the serial comms"""

    def __init__(self, serial: STM32, joystick: ActiveJoystick):
        self._serial = serial
        self._joystick: ActiveJoystick = joystick
        self._sensor_cache: SensorCache = {
            "thrusters": [0, 0, 0, 0, 0, 0, 0],
            "yaw": 0,
            "pitch": 0,
            "roll": 0,
            "depth": 0,
            "status": {},
        }

        self._toggles_cache = {"LED": False, "GRIPPER": False, "ARM": False}

        self._data_ready_event = Event()

        self._killswitch = False
        self._serial_incoming_thread = Thread(
            target=self._serial_incoming_loop, daemon=True
        )
        self._serial_incoming_thread.start()
        self._serial_outgoing_thread = Thread(
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
                toggle = ToggleButtons[button]
                self._toggles_cache[toggle] = not self._toggles_cache[toggle]

    @property
    def sensor_cache(self) -> SensorCache:
        return self._sensor_cache

    def _serial_outgoing_loop(self):
        while not self._killswitch:
            self._data_ready_event.wait()
            print("Ready")
            if self._serial.serial_ready and self._joystick.selected:
                payload = self._serial_controller_payload()
                self._serial.send(payload)
                self._data_ready_event.clear()

    def _serial_incoming_loop(self):
        """Reads TxPackets from STM, updates internal cache, runs on separate internal thread"""
        synced = False
        detected_rx = None

        while not self._killswitch:
            sleep(0.015)

            if not self._serial.serial_ready:
                # Reset the transient part of the cache
                # Non-transient keys include: controller['leds_and_valves']
                self._sensor_cache: SensorCache = {
                    "thrusters": [0, 0, 0, 0, 0, 0, 0],
                    "yaw": 0,
                    "pitch": 0,
                    "roll": 0,
                    "depth": 0,
                    "status": {},
                }
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
            message = Message(MessageType.SENSORS)
            data = cast(SensorsData, message.unpack(raw_data))
            self._sensor_cache["status"] = {"LED": data.led}
            self._sensor_cache["depth"] = data.depth
            self._sensor_cache["yaw"] = data.yaw
            self._sensor_cache["pitch"] = data.pitch
            self._sensor_cache["roll"] = data.roll
            self._sensor_cache["thrusters"] = list(data.motors)

        except struct.error as e:
            print(f"Unpack error: {e}")

    def _serial_controller_payload(self):
        joy = self._joystick
        control_word = int(self._toggles_cache["LED"]) << 0

        control_word |= int(self._toggles_cache["GRIPPER"]) << 1
        control_word |= int(self._toggles_cache["ARM"]) << 2
        control_word |= int(joy.get_gpinput(GamepadButton.DPAD_UP)) << 3
        control_word |= int(joy.get_gpinput(GamepadButton.DPAD_DOWN)) << 4

        payload = CommandData(
            control=control_word,
            x=-joy.get_gpinput(GamepadStick.LEFT_Y),
            y=joy.get_gpinput(GamepadStick.LEFT_X),
            z=joy.get_gpinput(GamepadTrigger.LEFT_TRIGGER)
            - joy.get_gpinput(GamepadTrigger.RIGHT_TRIGGER),
            roll=joy.get_gpinput(GamepadStick.RIGHT_X),
            pitch=joy.get_gpinput(GamepadStick.RIGHT_Y),
            yaw=joy.get_gpinput(GamepadButton.RIGHT_SHOULDER)
            - joy.get_gpinput(GamepadButton.LEFT_SHOULDER),
        )
        # print(payload)
        message = Message(MessageType.COMMAND)
        return message.pack(payload)

    def __del__(self):
        self._killswitch = True
        if self._serial_incoming_thread.is_alive():
            self._serial_incoming_thread.join()
        if self._serial_outgoing_thread.is_alive():
            self._serial_outgoing_thread.join()

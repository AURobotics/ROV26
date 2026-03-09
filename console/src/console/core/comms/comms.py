import struct
from enum import IntEnum, StrEnum
from threading import Event, Thread
from time import sleep
from typing import Dict, TypedDict, Annotated
from console.core.comms.stm32 import STM32
from console.core.gamepad import Controller


class MessageType(IntEnum):
    READY_MESSAGE = 0x00
    COMMAND_MESSAGE = 0x01
    PARAMETERS_MESSAGE = 0x02
    OPERATION_MESSAGE = 0x03
    SENSOR_MESSAGE = 0x04
    TUNING_MESSAGE = 0x05


class MessageFormat(StrEnum):
    COMMAND_MESSAGE = "<BBH6f"  # sync + msg_type + control_word + 6 floats = 29 bytes
    SENSOR_MESSAGE = (
        "<Bffff8f"  # status + depth + yaw + pitch + roll + 8 motor speeds = 53 bytes
    )


class MagicNumbers(IntEnum):
    SYNC_BYTE = 0xFF


ToggleButtons = {"CROSS": "LED", "TRIANGLE": "GRIPPER", "CIRCLE": "ARM"}


class SensorCache(TypedDict):
    thrusters: Annotated[list[int], 8]
    status: dict
    yaw: float
    pitch: float
    roll: float
    depth: float


class CommunicationManager:
    """Competition-specific handler for the serial comms"""

    _IDLE_TIMOUT = 0.05  # 50ms = 20Hz

    _IN_SIZE = struct.calcsize(MessageFormat.SENSOR_MESSAGE)  # 53 bytes

    def __init__(self, serial: STM32, controller: Controller):
        self._serial = serial
        self._controller = controller
        self._sensor_cache: SensorCache = {
            "thrusters": [0, 0, 0, 0, 0, 0, 0],
            "yaw": 0,
            "pitch": 0,
            "roll": 0,
            "depth": 0,
            "status": {},
        }

        self._toggles_cache = {
            "LED": False,
        }

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
        self._controller.register_listener(
            self._controller_toggles, [*ToggleButtons.keys()], send_buttons=True
        )

    def _controller_toggles(self, button: str):
        if self._serial.serial_ready:
            if button in ToggleButtons:
                toggle = ToggleButtons[button]
                self._toggles_cache[toggle] = not self._toggles_cache[toggle]

    @property
    def sensor_cache(self) -> SensorCache:
        return self._sensor_cache

    def _serial_outgoing_loop(self):
        while not self._killswitch:
            self._data_ready_event.wait()
            # print("Ready")
            if self._serial.serial_ready and self._controller.connected:
                current_state = self._controller.bindings_state
                payload = self._serial_controller_payload(current_state)
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

            # 1. Hunt for sync byte (0xFF)
            if not synced:
                byte = self._serial.recieve(1)
                if byte and byte[0] == MagicNumbers.SYNC_BYTE:
                    synced = True
                continue

            # 2. Read size byte
            if detected_rx is None:
                byte = self._serial.recieve(1)
                if not byte:
                    synced = False
                    continue
                msg_type = byte[0]
                if msg_type in MessageType._value2member_map_:
                    detected_rx = MessageType(msg_type)
                else:
                    synced = False
                    continue

            # 3. Handle message
            if detected_rx == MessageType.READY_MESSAGE:
                self._data_ready_event.set()
            elif detected_rx == MessageType.SENSOR_MESSAGE:
                raw = self._serial.recieve(self._IN_SIZE)
                if raw and len(raw) == self._IN_SIZE:
                    self._parse_incoming(raw)

            synced = False
            detected_rx = None

    def _parse_incoming(self, data: bytes):
        try:
            values = struct.unpack(MessageFormat.SENSOR_MESSAGE, data)
            self._sensor_cache["status"] = {
                "LED": (values[0] >> 2) & 1  # bit 2 (status_byte)
            }

            self._sensor_cache["depth"] = values[1]
            self._sensor_cache["yaw"] = values[2]
            self._sensor_cache["pitch"] = values[3]
            self._sensor_cache["roll"] = values[4]

            self._sensor_cache["thrusters"] = list(values[5:])

        except struct.error as e:
            print(f"Unpack error: {e}")

    def _serial_controller_payload(self, current_state: Dict):
        # Keybindings:
        # LStick - Axis 0 (Horizontal): Shift the ROV sideways
        # LStick - Axis 1 (Vertical): Move forward/ backward
        # RStick - Axis 2 (Horizontal): Rotate sideways about vertical axis
        # RStick - Axis 3 (Vertical): Tilt up or down
        # L2 - Axis 4 (+1 then /2): descend
        # R2 - Axis 5 (+1 then / 2): climb
        # Climb total value: R2 - L2

        bindings = current_state

        control_word = int(self._toggles_cache["LED"]) << 0

        control_word |= int(bindings.get("TRIANGLE", 0)) << 1
        control_word |= int(bindings.get("CIRCLE", 0)) << 2
        control_word |= int(bindings.get("D-UP", 0)) << 3
        control_word |= int(bindings.get("D-DOWN", 0)) << 4

        payload = [
            0xFF,
            0x01,
            control_word,
            -bindings.get("LS-V", 0),
            bindings.get("LS-H", 0),
            bindings.get("R1", 0) - bindings.get("L1", 0),
            -bindings.get("RS-V", 0),
            bindings.get("RS-H", 0),
            bindings.get("R2", 0) - bindings.get("L2", 0),
        ]
        return struct.pack(MessageFormat.COMMAND_MESSAGE, *payload)

    def __del__(self):
        self._killswitch = True
        if self._serial_incoming_thread.is_alive():
            self._serial_incoming_thread.join()
        if self._serial_outgoing_thread.is_alive():
            self._serial_outgoing_thread.join()

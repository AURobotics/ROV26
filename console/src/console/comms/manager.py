import threading
from dataclasses import dataclass
from time import sleep
from typing import Any, cast
from console.comms.float.float_messages import (
    CompanyNumberHandler,
    MQTTSignalBridge,
    StatusHandler,
)
from console.comms.float.file_receiver import file_receiver
from console.comms.float.mqtt import mqtt, topic
from console.comms.float.main import MAIN_TOPIC_NAME, SECONDARY_TOPIC_NAME
from PySide6.QtCore import QTimer
from console.comms.rov.stm32 import Stm32
from core.math.exponential_filter import ExponentialFilter
from hal.joystick.inputs import GamepadButton, GamepadStick, GamepadTrigger
from hal.joystick.joystick import Joystick
from hal.joystick.active_joystick import ActiveJoystick
from console.comms.rov.messages import (
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
    _mqtt_client: mqtt  # mqtt client for float communication

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
        self._mqtt_client = mqtt("localhost", 1883)

    def _register_button_listeners(self):
        for btn in ToggleButtons.keys():
            self._joystick.add_gamepad_button_listener(self._on_joystick_button, btn)

    def _on_joystick_button(self, _: Joystick, button: GamepadButton, is_pressed: bool):
        try:
            if self._stm.connected:
                if is_pressed:
                    toggle: str = ToggleButtons[button]
                    self._command_cache[toggle] = not self._command_cache[toggle]
        except Exception as ex:
            print(f"[WARN] | {ex}")

    @property
    def sensor_cache(self) -> SensorsData:
        return self._sensor_cache

    def _outgoing_loop(self):
        while not self._killswitch:
            self._data_ready_event.wait()
            try:
                if self._stm.has_incoming and self._joystick.selected:
                    payload = self._controller_payload()
                    self._stm.send(payload)
                    self._data_ready_event.clear()
            except Exception as ex:
                print(f"[WARN] | {ex}")

    def _incoming_loop(self):
        while not self._killswitch:
            sleep(0.015)
            try:
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
            except Exception as ex:
                print(f"[WARN] | {ex}")

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

    def float_communication_setup(self, float_tab):
        # Create bridge in main thread BEFORE MQTT handlers
        bridge = MQTTSignalBridge()

        # Connect bridge signals to float_tab slots
        bridge.status_signal.connect(lambda msg: float_tab.post_message(msg, "OK"))
        bridge.company_number_signal.connect(
            lambda msg: float_tab.post_message(msg, "OK")
        )
        bridge.file_complete_signal.connect(
            lambda: float_tab.post_message("CSV file received", "OK")
        )
        bridge.file_complete_signal.connect(lambda: float_tab.load_csv("log.csv"))

        # Create handlers with bridge reference
        status_handler = StatusHandler(bridge)
        company_handler = CompanyNumberHandler(bridge)

        # Subscribe to topics
        float_status_topic = topic(SECONDARY_TOPIC_NAME, self._mqtt_client)
        float_status_topic.subscribe(status_handler)

        float_company_number_topic = topic("float/data/credential", self._mqtt_client)
        float_company_number_topic.subscribe(company_handler)

        file_receiver_instance = file_receiver(
            self._mqtt_client, MAIN_TOPIC_NAME, crc32=False
        )

        # File polling timer (runs in main thread)
        _file_poll_timer = QTimer()

        def _check_file_complete():
            if file_receiver_instance.is_complete:
                _file_poll_timer.stop()
                bridge.file_complete_signal.emit()

        _file_poll_timer.timeout.connect(_check_file_complete)
        _file_poll_timer.start(5000)

    def __del__(self):
        self._killswitch = True
        if self._incoming_thread.is_alive():
            self._incoming_thread.join()
        if self._outgoing_thread.is_alive():
            self._outgoing_thread.join()

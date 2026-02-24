import json
import struct
from functools import reduce
from threading import Event, Thread
from time import sleep
from typing import Dict, Optional

from schema import Schema, Optional, SchemaError
from GamePad import Controller
from ROV_CONSOLE.esp32 import ESP32

readings_schema = Schema(
    {
        'thrusters':    {'h1': float, 'h2': float, 'h3': float, 'h4': float, 'v1': float, 'v2': float},
        'orientation':  {'roll': float, 'pitch': float, 'yaw': float},
        'acceleration': {'x': float, 'y': float, 'z': float},
        'status':       {'led': bool, 'dcv1': bool, 'dcv2': bool},
        }
    )


class CommunicationManager:
    """Competition-specific handler for the ESP Comms"""
    _PAYLOAD_MS = 0.033
    _IDLE_TIMOUT = 0.5 #Send heartbeat every 5000ms even if no changes

    def __init__(self, esp: ESP32, controller: Controller):
        self._esp = esp
        self._controller = controller
        self._cache = {
            'controller':  {'L1': 0, 'R1': 0, 'TOUCHPAD': 0},
            'status':      {},
            'thrusters':   {},
            'orientation': None,
            }
        #----------------------------(ADDED)--------------------------------
        """Event-driven control"""
        self._data_ready_event = Event()
        self._last_send_time = 0
        self._last_controller_stats: Dict = {}

        self._killswitch = False
        self._serial_incoming_thread = Thread(target=self._serial_incoming_loop, daemon=True)
        self._serial_incoming_thread.start()
        self._serial_outgoing_thread = Thread(target=self._serial_outgoing_loop, daemon=True)
        self._serial_outgoing_thread.start()
        self._controller.register_listener(self._controller_toggles, ['L1', 'R1', 'TOUCHPAD'], send_buttons=True)

    def _controller_toggles(self, button):
        if self._esp.serial_ready:
            self._cache['controller'][button] = not self._cache['controller'][button]
            self._data_ready_event.set()

    @property
    def led_and_valves(self):
        return self._cache['status'].copy()

    @property
    def thrusters_readings(self):
        return self._cache['thrusters'].copy()

    @property
    def orientations_readings(self):
        return self._cache['orientation']

    def _serial_outgoing_loop(self):
        while not self._killswitch:
            #--------------------------------(ADDED)------------------------------------------
            """Wait fot event OR timeout (heartbeat)"""
            timeout_occurred = not self._data_ready_event.wait(timeout=self._IDLE_TIMOUT)
            
            if self._esp.serial_ready and self._controller.connected:
                current_state = self._controller.bindings_state

                """Check if Controller axis values changed"""
                if self._has_meaningful_change(current_state):
                    payload = self._serial_controller_payload(current_state)
                    self._esp.send(payload)
                    self._last_controller_stats = current_state.copy()
                    self._data_ready_event.clear()
                
                elif timeout_occurred:
                    payload = self._serial_controller_payload(current_state)
                    self._esp.send(payload)
                    self._data_ready_event.clear()
    #-----------------------------------(ADDED)-------------------------------
    def _has_meaningful_change(self, current_state: Dict) -> bool:
        if not self._last_controller_stats:
            return True
        """Check axes"""
        axis_keys = ['LS-H','LS-V','RS-H','RS-V','L2','R2']
        for key in axis_keys:
            current = current_state.get(key,0)
            last = self._last_controller_stats.get(key,0)
            if abs(current - last) > 0.05: #5% threshold
                return True
        
        button_keys = ['CROSS','CIRCLE','SQUARE','TRIANGLE','L1','R1','TOUCHPAD']
        for key in button_keys:
            if current_state.get(key) != self._last_controller_stats(key):
                return True
        return False

    def _serial_incoming_loop(self):
        """Updates internal values, runs on separate internal thread"""
        while not self._killswitch:
            sleep(0.015)
            if not self._esp.serial_ready:
                # Reset the transient part of the cache
                # Non-transient keys include: controller['leds_and_valves']

                self._cache['thrusters'] = {}
                self._cache['status'] = {}
                self._cache['orientation'] = None
            else:
                consumed: Optional[str] = None

                while self._esp.incoming:
                    readings = None
                    # TODO: Tolerate sudden disconnect
                    consumed = self._esp.next_line
                    try:
                        readings = json.loads(consumed, parse_int=float)
                        readings = readings_schema.validate(readings)
                    except json.JSONDecodeError:
                        # Consumed message was an error or debug message
                        readings = None
                        if consumed:
                            print(consumed)
                    except SchemaError:
                        # Consumed message was a malformed readings message
                        readings = None
                    except TypeError:
                        # Probably interrupted connection
                        pass

                    if readings is not None:
                        self._cache['thrusters'] = readings['thrusters'].copy()
                        self._cache['orientation'] = readings['orientation'].copy()
                        self._cache['status'] = readings['status'].copy()

    def _serial_controller_payload(self):
        # Keybindings:
        # LStick - Axis 0 (Horizontal): Shift the ROV sideways
        # LStick - Axis 1 (Vertical): Move forward/ backward
        # RStick - Axis 2 (Horizontal): Rotate sideways about vertical axis
        # RStick - Axis 3 (Vertical): Tilt up or down
        # L2 - Axis 4 (+1 then /2): descend
        # R2 - Axis 5 (+1 then / 2): climb
        # Climb total value: R2 - L2
        bindings = self._controller.bindings_state
        signed_payload = [
            int(-254 * bindings["LS-V"]),
            int(254 * bindings["LS-H"]),
            int(254 * bindings["RS-V"]),
            int(-127 * bindings["RS-H"]),
            int(
                254 * (bindings["R2"] - bindings["L2"])
                ),
            ]
        thruster_payload = [abs(byte) for byte in signed_payload]
        sign_byte = 0
        for i, byte in enumerate(signed_payload):
            if byte < 0:
                sign_byte |= 1 << i
        payload = thruster_payload
        payload.append(sign_byte)

        toggles = self._cache['controller']
        # Touchpad Click - LED: 0000 0 LED 0      0
        # L1, R1 - Valves:      0000 0 0   VALVE1 VALVE2
        led_and_valves = toggles['L1'] * 4 + toggles['R1'] * 2 + toggles['TOUCHPAD']
        if bindings['CIRCLE']:
            led_and_valves |= 1  # Circle button inverts current LED state

        payload.append(led_and_valves)

        # Checksum: XOR first 7 bytes
        payload.append(reduce(lambda x, y: x ^ y, payload[:7]))

        # Terminator byte
        payload.append(255)
        payload = struct.pack("9B", *payload)
        return payload

    def __del__(self):
        self._killswitch = True
        if self._serial_incoming_thread.is_alive():
            self._serial_incoming_thread.join()
        if self._serial_outgoing_thread.is_alive():
            self._serial_outgoing_thread.join()
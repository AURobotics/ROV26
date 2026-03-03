import struct
from enum import IntEnum
from threading import Event, Thread
from time import sleep
from typing import Dict
from console.core.comms.stm32 import STM32
from console.core.gamepad.gamepad import Controller

class MessageType(IntEnum):
    READY_MESSAGE      = 0x00
    COMMAND_MESSAGE    = 0x01
    PARAMETERS_MESSAGE = 0x02
    OPERATION_MESSAGE  = 0x03
    SENSOR_MESSAGE     = 0x04
    TUNING_MESSAGE     = 0x05


class MessageFormat(str):
    COMMAND_MESSAGE = '<BBH6f'   # sync + msg_type + control_word + 6 floats = 29 bytes
    SENSOR_MESSAGE  = '<Bffff8f' # status + depth + yaw + pitch + roll + 8 motor speeds = 53 bytes


class MagicNumbers(IntEnum):
    SYNC_BYTE = 0xFF

class CommunicationManager:
    """Competition-specific handler for the ESP Comms"""
    _IDLE_TIMOUT = 0.05 #50ms = 20Hz
    
    _IN_SIZE = struct.calcsize(MessageFormat.SENSOR_MESSAGE) # 53 bytes
    

    def __init__(self, esp: STM32, controller: Controller):
        self._esp = esp
        self._controller = controller
        self._cache = {
            'controller':  {
                            'LED': 0, # Cross
                            },
            'status':      {},
            'thrusters':   {},
            'orientation': None,
            }
        #----------------------------(ADDED)--------------------------------
        """Event-driven control"""
        self._data_ready_event = Event()

        self._killswitch = False
        self._serial_incoming_thread = Thread(target=self._serial_incoming_loop, daemon=True)
        self._serial_incoming_thread.start()
        self._serial_outgoing_thread = Thread(target=self._serial_outgoing_loop, daemon=True)
        self._serial_outgoing_thread.start()
        self._controller.register_listener(self._controller_toggles, ['CROSS'], send_buttons=True)

    def _controller_toggles(self, button: str):
        if self._esp.esp_ready:
            if button == 'CROSS':
                self._cache['controller']['LED'] = not self._cache['controller']['LED']
            
            self._data_ready_event.set()

    @property
    def status(self):
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
            self._data_ready_event.wait(timeout=self._IDLE_TIMOUT)
            
            if self._esp.esp_ready and self._controller.connected:
                current_state = self._controller.bindings_state
                payload = self._serial_controller_payload(current_state)
                self._esp.send(payload)
                self._data_ready_event.clear()

    def _serial_incoming_loop(self):
        """Reads TxPackets from STM, updates internal cache, runs on separate internal thread"""
        synced = False
        detected_rx = None

        while not self._killswitch:
            sleep(0.015)

            if not self._esp.serial_ready:
                # Reset the transient part of the cache
                # Non-transient keys include: controller['leds_and_valves']
                self._esp.esp_ready = False
                self._cache['thrusters'] = {}
                self._cache['status'] = {}
                self._cache['orientation'] = None
                synced = False
                detected_rx = None
                continue
            
            if not self._esp.incoming:
                continue

            # 1. Hunt for sync byte (0xFF)
            if not synced:
                byte = self._esp.recieve(1)
                if byte and byte[0] == MagicNumbers.SYNC_BYTE:
                    synced = True
                continue
            
            # 2. Read size byte
            if detected_rx is None:
                byte = self._esp.recieve(1)
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
                print("ESP is ready")
                self._esp.esp_ready = True
            elif detected_rx == MessageType.SENSOR_MESSAGE:
                raw = self._esp.recieve(self._IN_SIZE)
                if raw and len(raw) == self._IN_SIZE:
                    self._parse_incoming(raw)
            
            synced = False
            detected_rx = None

            #     if ready and ready[0] ==0xAA:
            #         print("ESP is ready")
            #         self._esp.esp_ready = True
            #     continue
            # data = self._esp.recieve(size)
            # if not data or len(data) < size:
            #     continue
            # self._parse_incoming(data)
            
            # # 4. Read TxPacket body
            # data = self._esp.recieve(size)
            # if not data or len(data) < size:
            #     continue

            # self._parse_incoming(data)
            
    def _parse_incoming(self, data: bytes):
        try:
            values = struct.unpack(MessageFormat.SENSOR_MESSAGE, data)
            self._cache['status'] = {
                'LED': (values[0] >> 2) & 1 # bit 2 (status_byte)
            }
            
            self._cache['orientation'] = {
                'depth': values[1], 
                'yaw': values[2],
                'pitch': values[3],
                'roll': values[4],
            }
            
            self._cache['thrusters'] ={
                't1': values[5],
                't2': values[6],
                't3': values[7],
                't4': values[8],
                't5': values[9],
                't6': values[10],
                't7': values[11],
                't8': values[12],
            }

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
        toggles = self._cache['controller']

        control_word = int(toggles['LED']) << 0

        control_word |= int(bindings.get('TRIANGLE', 0)) << 1
        control_word |= int(bindings.get('CIRCLE', 0)) << 2
        control_word |= int(bindings.get('D-UP', 0)) << 3
        control_word |= int(bindings.get('D-DOWN', 0)) << 4

        return struct.pack(
            MessageFormat.COMMAND_MESSAGE,
            0xFF,
            0x01,    
            control_word,
            -bindings.get('LS-V', 0),
            bindings.get('LS-H', 0),
            bindings.get('R1', 0) - bindings.get('L1', 0),
            -bindings.get('RS-V', 0),
            bindings.get('RS-H', 0),
            bindings.get('R2', 0) - bindings.get('L2', 0),
        )
    def __del__(self):
        self._killswitch = True
        if self._serial_incoming_thread.is_alive():
            self._serial_incoming_thread.join()
        if self._serial_outgoing_thread.is_alive():
            self._serial_outgoing_thread.join()
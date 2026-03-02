from serial import Serial
import struct
from random import random, randint

from enum import IntEnum, StrEnum


class MessageType(IntEnum):
    READY_MESSAGE = 0x00
    COMMAND_MESSAGE = 0x01
    PARAMETERS_MESSAGE = 0x02
    OPERATION_MESSAGE = 0x03
    SENSOR_MESSAGE = 0x04
    TUNING_MESSAGE = 0x05


class MessageFormat(StrEnum):
    COMMAND_MESSAGE = "<BBH6f"
    SENSOR_MESSAGE = "<Bffff8f"


class MagicNumbers(IntEnum):
    SYNC_BYTE = 0xFF


esp = Serial("/dev/ttyUSB0", baudrate=115200, timeout=1)

synced = False
detected_rx = None  # reset value
while True:
    while esp.in_waiting > 0:
        next = int.from_bytes(esp.read(1), byteorder="little")
        if not synced:
            if next == MagicNumbers.SYNC_BYTE:
                synced = True
            continue
        if detected_rx is None:
            if next in MessageType._value2member_map_:
                detected_rx = MessageType(next)
        if detected_rx == MessageType.READY_MESSAGE:
            # print("Ready")
            payload = [
                MagicNumbers.SYNC_BYTE,
                MessageType.COMMAND_MESSAGE,
                randint(0x0000, 0xFFFF),
                *[random() for _ in range(6)],
            ]
            binary_payload = struct.pack(MessageFormat.COMMAND_MESSAGE, *payload)
            esp.write(binary_payload)
            # print(f"Sent {binary_payload}")
        elif detected_rx == MessageType.SENSOR_MESSAGE:
            expected_size = struct.calcsize(MessageFormat.SENSOR_MESSAGE)
            raw_data = esp.read(expected_size)
            data = list(
                struct.unpack(MessageFormat.SENSOR_MESSAGE, raw_data[:expected_size])
            )
            print(data)
        synced = False
        detected_rx = None

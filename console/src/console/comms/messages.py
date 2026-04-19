from __future__ import annotations
from abc import ABC
from dataclasses import dataclass, field, fields
from enum import Enum, IntFlag
import struct
from typing import Annotated, Self, TypeAlias

from annotated_types import Ge, Le


class Constants:
    SYNC_BYTE = b"\xff"
    SYNC_INT = 255


class ControlFlags(IntFlag):
    depth = 1 << 15
    roll = 1 << 14
    pitch = 1 << 13
    yaw = 1 << 12
    led_open = 1 << 11
    gripper_close = 1 << 10
    arm_close = 1 << 9
    arm_enable_rotation = 1 << 8
    arm_rotate_up = 1 << 7


NormalizedFloat: TypeAlias = Annotated[float, Ge(-1.0), Le(1.0)]
Byte: TypeAlias = Annotated[int, Ge(0), Le(255)]
Word: TypeAlias = Annotated[int, Ge(0), Le(65535)]


@dataclass(frozen=True, slots=True)
class Payload(ABC): ...


@dataclass(frozen=True, slots=True)
class CommandData(Payload):
    control: Word
    x: NormalizedFloat
    y: NormalizedFloat
    z: NormalizedFloat
    yaw: NormalizedFloat
    pitch: NormalizedFloat
    roll: NormalizedFloat


@dataclass(frozen=True, slots=True)
class SensorsData(Payload):
    status: Byte
    depth: NormalizedFloat
    yaw: NormalizedFloat
    pitch: NormalizedFloat
    roll: NormalizedFloat
    thrusters: list[NormalizedFloat] = field(metadata={"size": 8}, default_factory=list)

    @property
    def led(self) -> bool:
        return bool((self.status >> 2) & 1)


@dataclass(frozen=True, slots=True)
class OperationModeData(Payload): ...


@dataclass(frozen=True, slots=True)
class ParametersData(Payload): ...


@dataclass(frozen=True, slots=True)
class ReadyData(Payload): ...


@dataclass(frozen=True, slots=True)
class DfuData(Payload): ...


@dataclass(frozen=True, slots=True)
class Frame:
    type_id: int
    format: str
    payload_cls: type[Payload]


class MessageType(Enum):
    READY = Frame(0, "", ReadyData)
    COMMAND = Frame(1, "H6f", CommandData)
    PARAMETERS = Frame(2, "", ParametersData)
    OPERATION_MODE = Frame(3, "", OperationModeData)
    SENSORS = Frame(4, "B12f", SensorsData)
    DFU = Frame(7, "", DfuData)

    @property
    def type_id(self) -> int:
        return self.value.type_id

    @property
    def payload_cls(self) -> type[Payload]:
        return self.value.payload_cls

    @property
    def size(self) -> int:
        return struct.calcsize(self.value.format)

    @property
    def format(self) -> str:
        return self.value.format

    @classmethod
    def from_type(cls, type_id: int) -> Self:
        for member in cls:
            if member.value.type_id == type_id:
                return member
        raise ValueError(f"Unknown message type value {type_id}")

    @classmethod
    def from_payload(cls, payload: Payload) -> Self:
        for member in cls:
            if isinstance(payload, member.value.payload_cls):
                return member
        raise ValueError(f"Unknown payload type {type(payload)}")


class Message:
    @staticmethod
    def encode(payload: Payload) -> bytes:
        type = MessageType.from_payload(payload)
        flat_values = []
        for f in fields(payload):
            val = getattr(payload, f.name)
            if isinstance(val, list):
                flat_values.extend(val)
            else:
                flat_values.append(val)
        header_fmt = f"<BB{type.format}"
        return struct.pack(header_fmt, Constants.SYNC_INT, type.type_id, *flat_values)

    @staticmethod
    def decode(type: MessageType, content: bytes) -> Payload:
        raw_values = list(struct.unpack(f"<{type.format}", content))

        final_args = []
        i = 0

        for f in fields(type.payload_cls):
            size = f.metadata.get("size")

            if size is not None:
                final_args.append(raw_values[i : i + size])
                i += size
            else:
                final_args.append(raw_values[i])
                i += 1

        return type.payload_cls(*final_args)

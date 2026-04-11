from __future__ import annotations
from abc import ABC
from dataclasses import dataclass, fields
from enum import Enum, IntEnum, auto
import struct
from typing import Annotated, Any, Literal, Self

from annotated_types import Ge, Le


class Constants(IntEnum):
    SYNC_BYTE = 255


class Direction(Enum):
    INCOMING = auto()
    OUTGOING = auto()
    BIDIRECTIONAL = INCOMING | OUTGOING


type NormalizedFloat = Annotated[float, Ge(-1.0), Le(1.0)]
type Byte = Annotated[int, Ge(0), Le(255)]
type Word = Annotated[int, Ge(0), Le(65535)]


@dataclass(frozen=True, slots=True)
class PayloadType(ABC): ...


@dataclass(frozen=True, slots=True)
class CommandData(PayloadType):
    control: Word
    x: NormalizedFloat
    y: NormalizedFloat
    z: NormalizedFloat
    yaw: NormalizedFloat
    pitch: NormalizedFloat
    roll: NormalizedFloat


@dataclass(frozen=True, slots=True)
class SensorsData(PayloadType):
    status: Byte
    depth: NormalizedFloat
    yaw: NormalizedFloat
    pitch: NormalizedFloat
    roll: NormalizedFloat
    motors: Annotated[list[NormalizedFloat], 8]

    @property
    def led(self) -> bool:
        return bool((self.status >> 2) & 1)


@dataclass(frozen=True, slots=True)
class OperationModeData(PayloadType): ...


@dataclass(frozen=True, slots=True)
class ParametersData(PayloadType): ...


@dataclass(frozen=True, slots=True)
class Frame:
    type_id: int
    format: str
    direction: Direction
    payload_cls: type[PayloadType] | None = None


class MessageType(Enum):
    READY = Frame(0, "", Direction.INCOMING)
    COMMAND = Frame(1, "BH6f", Direction.OUTGOING, CommandData)
    PARAMETERS = Frame(2, "", Direction.OUTGOING, ParametersData)
    OPERATION_MODE = Frame(3, "", Direction.OUTGOING, OperationModeData)
    SENSORS = Frame(4, "Bffff8f", Direction.INCOMING, SensorsData)

    @property
    def type_id(self) -> int:
        return self.value.type_id

    @property
    def payload_cls(self) -> type[PayloadType] | None:
        return self.value.payload_cls

    @property
    def size(self) -> int:
        return struct.calcsize(self.value.format)

    @property
    def format(self) -> str:
        return self.value.format

    @property
    def direction(self) -> Direction:
        return self.value.direction

    @classmethod
    def from_type(cls, type_id: int) -> Self:
        for member in cls:
            if member.value.type_id == type_id:
                return member
        raise ValueError(f"Unknown message type value {type_id}")


class Message:
    type_id: int
    format: str
    sync: int | None = 255
    endian: Literal["<"] | Literal[">"] = "<"
    payload_cls: type[PayloadType] | None = None

    def __init__(self, message_type: MessageType) -> None:
        self.type_id = message_type.type_id
        self.format = message_type.format
        self.payload_cls = message_type.payload_cls

    def pack(self, payload: PayloadType) -> bytes:
        data_values = [getattr(payload, f.name) for f in fields(payload)]
        header_fmt = f"<BB{self.format}"
        return struct.pack(header_fmt, Constants.SYNC_BYTE, self.type_id, *data_values)

    def unpack(self, content: bytes) -> PayloadType | tuple[Any, ...]:
        raw_values = struct.unpack(f"<{self.format}", content)
        if self.payload_cls:
            return self.payload_cls(*raw_values)
        return raw_values

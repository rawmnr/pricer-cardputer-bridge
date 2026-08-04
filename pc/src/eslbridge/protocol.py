"""Versioned binary protocol shared with the Cardputer firmware."""

from __future__ import annotations

import enum
import struct
import zlib
from dataclasses import dataclass

MAGIC = b"ESLI"
PROTOCOL_VERSION = 1
MAX_PAYLOAD = 4096
_HEADER_WITHOUT_MAGIC = struct.Struct("<BBBBHH")
_CRC = struct.Struct("<I")


class ProtocolError(ValueError):
    """Raised when a bridge frame is malformed or unsupported."""


class Command(enum.IntEnum):
    HELLO = 0x01
    GET_STATUS = 0x02
    CARRIER_TEST = 0x10
    SEND_PRICER_FRAME = 0x11


class Status(enum.IntEnum):
    OK = 0x00
    BAD_MAGIC = 0x01
    BAD_VERSION = 0x02
    BAD_CRC = 0x03
    BAD_LENGTH = 0x04
    UNSUPPORTED_COMMAND = 0x05
    INVALID_ARGUMENT = 0x06
    BUSY = 0x07
    HARDWARE_ERROR = 0x08
    NOT_IMPLEMENTED = 0x09
    TIMEOUT = 0x0A


@dataclass(frozen=True, slots=True)
class Message:
    command: Command
    sequence: int
    payload: bytes = b""
    status: Status = Status.OK
    flags: int = 0
    version: int = PROTOCOL_VERSION


def _validate_u16(name: str, value: int) -> None:
    if not 0 <= value <= 0xFFFF:
        raise ProtocolError(f"{name} must fit in uint16, got {value}")


def encode_message(message: Message) -> bytes:
    """Encode one bridge message including magic and IEEE CRC32."""
    _validate_u16("sequence", message.sequence)
    if len(message.payload) > MAX_PAYLOAD:
        raise ProtocolError(f"payload exceeds {MAX_PAYLOAD} bytes")
    if not 0 <= message.flags <= 0xFF:
        raise ProtocolError("flags must fit in uint8")

    body = (
        _HEADER_WITHOUT_MAGIC.pack(
            message.version,
            int(message.command),
            message.flags,
            int(message.status),
            message.sequence,
            len(message.payload),
        )
        + message.payload
    )
    checksum = zlib.crc32(body) & 0xFFFFFFFF
    return MAGIC + body + _CRC.pack(checksum)


def decode_message(frame: bytes) -> Message:
    """Decode and validate exactly one complete bridge frame."""
    minimum_size = len(MAGIC) + _HEADER_WITHOUT_MAGIC.size + _CRC.size
    if len(frame) < minimum_size:
        raise ProtocolError("frame is shorter than the fixed header")
    if frame[:4] != MAGIC:
        raise ProtocolError("bad magic")

    version, command_raw, flags, status_raw, sequence, payload_length = (
        _HEADER_WITHOUT_MAGIC.unpack_from(frame, 4)
    )
    if version != PROTOCOL_VERSION:
        raise ProtocolError(f"unsupported protocol version {version}")
    if payload_length > MAX_PAYLOAD:
        raise ProtocolError(f"payload length exceeds {MAX_PAYLOAD}")

    expected_size = minimum_size + payload_length
    if len(frame) != expected_size:
        raise ProtocolError(f"frame length mismatch: expected {expected_size}, got {len(frame)}")

    payload_start = 4 + _HEADER_WITHOUT_MAGIC.size
    payload_end = payload_start + payload_length
    expected_crc = _CRC.unpack_from(frame, payload_end)[0]
    actual_crc = zlib.crc32(frame[4:payload_end]) & 0xFFFFFFFF
    if expected_crc != actual_crc:
        raise ProtocolError(
            f"CRC mismatch: expected 0x{expected_crc:08X}, calculated 0x{actual_crc:08X}"
        )

    try:
        command = Command(command_raw)
    except ValueError as exc:
        raise ProtocolError(f"unknown command 0x{command_raw:02X}") from exc
    try:
        status = Status(status_raw)
    except ValueError as exc:
        raise ProtocolError(f"unknown status 0x{status_raw:02X}") from exc

    return Message(
        version=version,
        command=command,
        flags=flags,
        status=status,
        sequence=sequence,
        payload=frame[payload_start:payload_end],
    )


def expected_frame_size(header: bytes) -> int:
    """Return complete frame size from the fixed 12-byte header."""
    if len(header) != 12:
        raise ProtocolError("header must be exactly 12 bytes")
    if header[:4] != MAGIC:
        raise ProtocolError("bad magic")
    payload_length = struct.unpack_from("<H", header, 10)[0]
    if payload_length > MAX_PAYLOAD:
        raise ProtocolError(f"payload length exceeds {MAX_PAYLOAD}")
    return 12 + payload_length + 4

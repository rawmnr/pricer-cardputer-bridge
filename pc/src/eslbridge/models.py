"""Typed payload models for bridge commands."""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .protocol import ProtocolError

_HELLO = struct.Struct("<BBBBIHBB")
_STATUS = struct.Struct("<BBBBI")
_CARRIER_TEST = struct.Struct("<IIB3x")


@dataclass(frozen=True, slots=True)
class HelloInfo:
    protocol_version: int
    firmware_version: tuple[int, int, int]
    capabilities: int
    max_payload: int
    ir_gpio: int

    @classmethod
    def decode(cls, payload: bytes) -> HelloInfo:
        if len(payload) != _HELLO.size:
            raise ProtocolError(f"HELLO payload must be {_HELLO.size} bytes")
        protocol, major, minor, patch, capabilities, max_payload, ir_gpio, _ = _HELLO.unpack(
            payload
        )
        return cls(protocol, (major, minor, patch), capabilities, max_payload, ir_gpio)


@dataclass(frozen=True, slots=True)
class DeviceStatus:
    last_command: int
    transmitter_state: int
    last_error: int
    tx_count: int

    @classmethod
    def decode(cls, payload: bytes) -> DeviceStatus:
        if len(payload) != _STATUS.size:
            raise ProtocolError(f"status payload must be {_STATUS.size} bytes")
        command, state, error, _, tx_count = _STATUS.unpack(payload)
        return cls(command, state, error, tx_count)


@dataclass(frozen=True, slots=True)
class CarrierTestRequest:
    frequency_hz: int = 1_245_000
    duration_us: int = 2_000
    duty_percent: int = 50

    def encode(self) -> bytes:
        if not 500_000 <= self.frequency_hz <= 2_000_000:
            raise ProtocolError("frequency must be between 500 kHz and 2 MHz")
        if not 1 <= self.duration_us <= 5_000:
            raise ProtocolError("duration must be between 1 and 5000 us")
        if not 10 <= self.duty_percent <= 60:
            raise ProtocolError("duty cycle must be between 10 and 60 percent")
        return _CARRIER_TEST.pack(self.frequency_hz, self.duration_us, self.duty_percent)

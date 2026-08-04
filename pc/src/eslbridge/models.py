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
    reserved: int = 0

    @classmethod
    def decode(cls, payload: bytes) -> HelloInfo:
        if len(payload) != _HELLO.size:
            raise ProtocolError(f"HELLO payload must be {_HELLO.size} bytes")
        protocol, major, minor, patch, capabilities, max_payload, ir_gpio, reserved = _HELLO.unpack(
            payload
        )
        return cls(protocol, (major, minor, patch), capabilities, max_payload, ir_gpio, reserved)

    def is_valid_identity(self) -> tuple[bool, str]:
        if self.protocol_version != 1:
            return False, f"unsupported protocol version {self.protocol_version} (expected 1)"
        if self.max_payload != 4096:
            return False, f"unexpected max payload {self.max_payload} (expected 4096)"
        if self.ir_gpio != 44:
            return False, f"unexpected IR GPIO {self.ir_gpio} (expected 44)"
        if self.reserved != 0:
            return False, f"non-zero reserved byte {self.reserved}"
        required_capabilities = 0x09
        if (self.capabilities & required_capabilities) != required_capabilities:
            return False, f"missing required capabilities 0x09 (got 0x{self.capabilities:08X})"
        return True, ""

    def validate_identity(self, port: str = "") -> None:
        valid, reason = self.is_valid_identity()
        if not valid:
            from .transport import InvalidDeviceError

            prefix = f"Device on {port} " if port else "Device "
            raise InvalidDeviceError(f"{prefix}{reason}")


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

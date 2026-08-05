"""Typed payload models for bridge commands."""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .protocol import ProtocolError

_HELLO = struct.Struct("<BBBBIHBB")
_HELLO_IDENTITY = struct.Struct("<BBBBIHBBB7sB8s")
_STATUS = struct.Struct("<BBBBI")
_CARRIER_TEST = struct.Struct("<IIB3x")
_PRICER_FRAME_HEADER = struct.Struct("<BBHIH")

MODULATION_PP4 = 4
MODULATION_PP16 = 16
MIN_PRICER_FRAME_BYTES = 1
MAX_PRICER_FRAME_BYTES = 256
MIN_PRICER_REPEATS = 1
MAX_PRICER_REPEATS = 400
MAX_INTER_REPEAT_GAP_US = 1_000_000
BUILD_PROVENANCE_NAMES = {
    0: "unknown",
    1: "clean",
    2: "dirty",
    3: "ci",
}


@dataclass(frozen=True, slots=True)
class HelloInfo:
    protocol_version: int
    firmware_version: tuple[int, int, int]
    capabilities: int
    max_payload: int
    ir_gpio: int
    reserved: int = 0
    identity_version: int = 0
    git_sha: str = "unknown"
    build_provenance: str = "legacy"
    pp16_profile_revision: str = "unknown"

    @classmethod
    def decode(cls, payload: bytes) -> HelloInfo:
        if len(payload) == _HELLO.size:
            values = _HELLO.unpack(payload)
            protocol, major, minor, patch, capabilities, max_payload, ir_gpio, reserved = values
            return cls(
                protocol, (major, minor, patch), capabilities, max_payload, ir_gpio, reserved
            )
        if len(payload) != _HELLO_IDENTITY.size:
            raise ProtocolError(
                f"HELLO payload must be {_HELLO.size} or {_HELLO_IDENTITY.size} bytes"
            )
        (
            protocol,
            major,
            minor,
            patch,
            capabilities,
            max_payload,
            ir_gpio,
            reserved,
            identity_version,
            raw_git_sha,
            provenance_code,
            raw_profile,
        ) = _HELLO_IDENTITY.unpack(payload)
        if identity_version != 1:
            raise ProtocolError(f"unsupported HELLO build identity version {identity_version}")
        try:
            git_sha = raw_git_sha.decode("ascii").rstrip("\x00")
            profile_revision = raw_profile.decode("ascii").rstrip("\x00")
        except UnicodeDecodeError as exc:
            raise ProtocolError("HELLO build identity is not ASCII") from exc
        return cls(
            protocol,
            (major, minor, patch),
            capabilities,
            max_payload,
            ir_gpio,
            reserved,
            identity_version,
            git_sha or "unknown",
            BUILD_PROVENANCE_NAMES.get(provenance_code, "unknown"),
            profile_revision or "unknown",
        )

    def is_valid_identity(self) -> tuple[bool, str]:
        if self.protocol_version != 1:
            return False, f"unsupported protocol version {self.protocol_version} (expected 1)"
        if self.max_payload != 4096:
            return False, f"unexpected max payload {self.max_payload} (expected 4096)"
        if self.ir_gpio != 44:
            return False, f"unexpected IR GPIO {self.ir_gpio} (expected 44)"
        if self.reserved != 0:
            return False, f"non-zero reserved byte {self.reserved}"
        if self.identity_version not in (0, 1):
            return False, f"unsupported build identity version {self.identity_version}"
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


@dataclass(frozen=True, slots=True)
class PricerFrameRequest:
    frame: bytes
    modulation: int = MODULATION_PP16
    repeats: int = 1
    inter_repeat_gap_us: int = 0
    reserved: int = 0

    def encode(self) -> bytes:
        if self.modulation not in (MODULATION_PP4, MODULATION_PP16):
            raise ProtocolError(f"modulation must be 4 (PP4) or 16 (PP16), got {self.modulation}")
        if self.reserved != 0:
            raise ProtocolError("reserved byte must be 0")
        if not MIN_PRICER_REPEATS <= self.repeats <= MAX_PRICER_REPEATS:
            raise ProtocolError(
                "repeats must be between "
                f"{MIN_PRICER_REPEATS} and {MAX_PRICER_REPEATS}, got {self.repeats}"
            )
        if not 0 <= self.inter_repeat_gap_us <= MAX_INTER_REPEAT_GAP_US:
            raise ProtocolError(
                "inter-repeat gap must be between "
                f"0 and {MAX_INTER_REPEAT_GAP_US} us, got {self.inter_repeat_gap_us}"
            )
        if not MIN_PRICER_FRAME_BYTES <= len(self.frame) <= MAX_PRICER_FRAME_BYTES:
            raise ProtocolError(
                "frame length must be between "
                f"{MIN_PRICER_FRAME_BYTES} and {MAX_PRICER_FRAME_BYTES} bytes, "
                f"got {len(self.frame)}"
            )
        header = _PRICER_FRAME_HEADER.pack(
            self.modulation,
            self.reserved,
            self.repeats,
            self.inter_repeat_gap_us,
            len(self.frame),
        )
        return header + self.frame

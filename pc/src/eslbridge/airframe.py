"""Direct Pricer AirFrame builders for the TagTinker type-1327 profile.

These bytes are the payload sent to the PP4 symbol encoder.  The legacy
PrecIR/IRDongle transport marker ``00 00 00 40`` is deliberately not part of
an AirFrame and is only available through explicit compatibility helpers.

The protocol and physical compatibility remain unverified on the target ESL.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

from .models import PricerFrameRequest
from .precir import (
    MODULATION_PP4,
    PricerPlid,
    build_pricer_frame_request,
    calculate_precir_crc16,
    derive_pricer_plid,
)

AIRFRAME_PROTOCOL: Final[int] = 0x85
TAGTINKER_TYPE_CODE: Final[int] = 1327
TAGTINKER_BARCODE: Final[str] = "N4163114582613272"
TAGTINKER_WIDTH: Final[int] = 208
TAGTINKER_HEIGHT: Final[int] = 112
TAGTINKER_PLANE_BITS: Final[int] = TAGTINKER_WIDTH * TAGTINKER_HEIGHT
TAGTINKER_PLANE_BYTES: Final[int] = TAGTINKER_PLANE_BITS // 8
TAGTINKER_RAW_BYTES: Final[int] = TAGTINKER_PLANE_BYTES * 2
TAGTINKER_DATA_BYTES_PER_PACKET: Final[int] = 20
TAGTINKER_PADDED_BYTES: Final[int] = 5_840
TAGTINKER_DATA_FRAME_COUNT: Final[int] = TAGTINKER_PADDED_BYTES // TAGTINKER_DATA_BYTES_PER_PACKET
TAGTINKER_PAGE: Final[int] = 0
TAGTINKER_GAP_US: Final[int] = 500
TAGTINKER_REPEAT_COUNTS: Final[tuple[int, int, int, int]] = (81, 16, 3, 21)
AIRFRAME_DONGLE_HEADER: Final[bytes] = b"\x00\x00\x00\x40"


class AirFrameError(ValueError):
    """Raised when direct AirFrame fields or payloads are invalid."""


@dataclass(frozen=True, slots=True)
class AirFrame:
    """One direct on-air frame and its separate transmission metadata."""

    name: str
    command: int
    frame: bytes
    repeats: int
    inter_repeat_gap_us: int = TAGTINKER_GAP_US

    def request(self) -> PricerFrameRequest:
        """Return a PP4 bridge request without embedding repeat metadata in bytes."""
        return build_pricer_frame_request(
            self.frame,
            repeats=self.repeats,
            inter_repeat_gap_us=self.inter_repeat_gap_us,
            modulation=MODULATION_PP4,
        )

    def __post_init__(self) -> None:
        if AIRFRAME_DONGLE_HEADER in self.frame[:4]:
            raise AirFrameError("direct AirFrame must not contain the legacy dongle header")
        if not 0 <= self.command <= 0xFF:
            raise AirFrameError("command must be uint8")
        if not self.frame or len(self.frame) > 256:
            raise AirFrameError("direct AirFrame length must be between 1 and 256 bytes")
        if self.repeats < 1:
            raise AirFrameError("repeats must be positive")


def _finalize(payload: bytes) -> bytes:
    if not payload or payload[0] != AIRFRAME_PROTOCOL:
        raise AirFrameError("direct AirFrame payload must start with protocol byte 0x85")
    crc = calculate_precir_crc16(payload)
    return payload + crc.to_bytes(2, "little")


def _validate_plid(plid: PricerPlid) -> bytes:
    if not isinstance(plid, PricerPlid):
        raise AirFrameError(f"plid must be PricerPlid, got {type(plid).__name__}")
    return plid.wire


def _mcu_payload(plid: PricerPlid, command: int, body: bytes) -> bytes:
    if not 0 <= command <= 0xFF:
        raise AirFrameError("command must be uint8")
    if not isinstance(body, bytes):
        raise AirFrameError("body must be bytes")
    return (
        bytes((AIRFRAME_PROTOCOL,))
        + _validate_plid(plid)
        + b"\x34\x00\x00\x00"
        + bytes((command,))
        + body
    )


def make_tagtinker_ping_frame(plid: PricerPlid) -> bytes:
    """Build the exact 32-byte direct ping AirFrame."""
    payload = (
        bytes((AIRFRAME_PROTOCOL,)) + _validate_plid(plid) + b"\x97\x01\x00\x00\x00" + b"\x01" * 20
    )
    return _finalize(payload)


def make_tagtinker_params_frame(
    plid: PricerPlid,
    *,
    byte_count: int = TAGTINKER_RAW_BYTES,
    page: int = TAGTINKER_PAGE,
    width: int = TAGTINKER_WIDTH,
    height: int = TAGTINKER_HEIGHT,
) -> bytes:
    """Build the raw type-1327 page-0, uncompressed image parameter frame."""
    fields = (byte_count, width, height, 0, 0, 0)
    if not 0 <= byte_count <= 0xFFFF or not 0 <= page <= 0xFF:
        raise AirFrameError("image byte count/page is outside wire range")
    if any(not 0 <= field <= 0xFFFF for field in fields[1:]):
        raise AirFrameError("image dimensions/position fields are outside wire range")
    body = (
        byte_count.to_bytes(2, "big")
        + b"\x00\x00"  # raw/no compression
        + bytes((page,))
        + width.to_bytes(2, "big")
        + height.to_bytes(2, "big")
        + b"\x00\x00\x00\x00\x00\x00"  # x, y, key
        + b"\x88\x00\x00\x00\x00\x00\x00"
    )
    return _finalize(_mcu_payload(plid, 0x05, body))


def make_tagtinker_data_frame(plid: PricerPlid, index: int, data: bytes) -> bytes:
    """Build one direct indexed 20-byte type-1327 data AirFrame."""
    if not 0 <= index <= 0xFFFF:
        raise AirFrameError("data packet index must be uint16")
    if not isinstance(data, bytes) or len(data) != TAGTINKER_DATA_BYTES_PER_PACKET:
        raise AirFrameError("data packet must contain exactly 20 bytes")
    return _finalize(_mcu_payload(plid, 0x20, index.to_bytes(2, "big") + data))


def make_tagtinker_refresh_frame(plid: PricerPlid) -> bytes:
    """Build the direct page refresh AirFrame."""
    return _finalize(_mcu_payload(plid, 0x01, b"\x00" * 18))


def pack_plane_bits(bits: Sequence[int]) -> bytes:
    """Pack one 208x112 plane MSB-first, one bit per pixel."""
    if len(bits) != TAGTINKER_PLANE_BITS:
        raise AirFrameError(f"plane must contain {TAGTINKER_PLANE_BITS} bits")
    if any(bit not in (0, 1) for bit in bits):
        raise AirFrameError("plane bits must contain only 0 or 1")
    output = bytearray(TAGTINKER_PLANE_BYTES)
    for index, bit in enumerate(bits):
        output[index // 8] |= bit << (7 - (index % 8))
    return bytes(output)


def make_two_plane_payload(
    primary_bits: Sequence[int], accent_bits: Sequence[int] | None = None
) -> bytes:
    """Pack primary and accent planes in wire order, both MSB-first."""
    primary = pack_plane_bits(primary_bits)
    accent = pack_plane_bits([1] * TAGTINKER_PLANE_BITS if accent_bits is None else accent_bits)
    return primary + accent


def packetize_tagtinker_image(payload: bytes) -> list[bytes]:
    """Zero-pad raw image bytes and prepend big-endian packet indices."""
    if not isinstance(payload, bytes) or len(payload) != TAGTINKER_RAW_BYTES:
        raise AirFrameError(f"raw image must contain exactly {TAGTINKER_RAW_BYTES} bytes")
    padded = payload + b"\x00" * (TAGTINKER_PADDED_BYTES - len(payload))
    return [
        index.to_bytes(2, "big") + padded[offset : offset + TAGTINKER_DATA_BYTES_PER_PACKET]
        for index, offset in enumerate(
            range(0, TAGTINKER_PADDED_BYTES, TAGTINKER_DATA_BYTES_PER_PACKET)
        )
    ]


def make_tagtinker_profile(
    plid: PricerPlid | None = None,
    *,
    primary_bits: Sequence[int] | None = None,
    accent_bits: Sequence[int] | None = None,
) -> list[AirFrame]:
    """Build deterministic ping, params, raw data, and refresh frames."""
    target_plid = derive_pricer_plid(TAGTINKER_BARCODE) if plid is None else plid
    primary = [1] * TAGTINKER_PLANE_BITS if primary_bits is None else primary_bits
    payload = make_two_plane_payload(primary, accent_bits)
    packets = packetize_tagtinker_image(payload)
    ping, params, data_repeats, refresh = TAGTINKER_REPEAT_COUNTS
    vectors = [
        AirFrame("tagtinker-1327-ping.bin", 0x97, make_tagtinker_ping_frame(target_plid), ping),
        AirFrame(
            "tagtinker-1327-params-page0.bin",
            0x05,
            make_tagtinker_params_frame(target_plid),
            params,
        ),
    ]
    vectors.extend(
        AirFrame(
            f"tagtinker-1327-data-{index:04d}.bin",
            0x20,
            make_tagtinker_data_frame(target_plid, index, packet[2:]),
            data_repeats,
        )
        for index, packet in enumerate(packets)
    )
    vectors.append(
        AirFrame(
            "tagtinker-1327-refresh.bin",
            0x01,
            make_tagtinker_refresh_frame(target_plid),
            refresh,
        )
    )
    return vectors


__all__ = [
    "AIRFRAME_DONGLE_HEADER",
    "AIRFRAME_PROTOCOL",
    "TAGTINKER_BARCODE",
    "TAGTINKER_DATA_BYTES_PER_PACKET",
    "TAGTINKER_DATA_FRAME_COUNT",
    "TAGTINKER_GAP_US",
    "TAGTINKER_HEIGHT",
    "TAGTINKER_PADDED_BYTES",
    "TAGTINKER_PAGE",
    "TAGTINKER_PLANE_BITS",
    "TAGTINKER_PLANE_BYTES",
    "TAGTINKER_RAW_BYTES",
    "TAGTINKER_REPEAT_COUNTS",
    "TAGTINKER_TYPE_CODE",
    "TAGTINKER_WIDTH",
    "AirFrame",
    "AirFrameError",
    "make_tagtinker_data_frame",
    "make_tagtinker_params_frame",
    "make_tagtinker_ping_frame",
    "make_tagtinker_profile",
    "make_tagtinker_refresh_frame",
    "make_two_plane_payload",
    "pack_plane_bits",
    "packetize_tagtinker_image",
]

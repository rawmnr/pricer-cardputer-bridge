"""PrecIR interoperability adapter for Pricer PP16 frame formatting and CRC16 calculation.

PROVISIONAL / INFERRED WARNING:
Frame finalization, header placement, and CRC16 algorithms in this module are clean-room
reimplementations of published PrecIR prior art (GPL-3.0) and remain UNTESTED against
physical Pricer ESL target tags in this setup. No claim of tag or physical carrier
compatibility is made.

Provenance & Citation:
- Upstream repo: https://github.com/furrtek/PrecIR
- Upstream commit: b09951e2b3d2741e4ca08f929eafef849f6fc006
- Inspected upstream file: tools_python/pr.py (terminate_frame / crc16)
- Reference doc: https://www.furrtek.org/index.php?a=esl
- License: GNU General Public License v3.0
- Clean-room status: No PrecIR source code was copied or vendored. Frame layout,
  PP16 header bytes (0x00, 0x00, 0x00, 0x40), and CRC16 calculation (poly 0x8408,
  init 0x8408) are clean-room reimplementations derived from published Python driver
  tools_python/pr.py and reverse-engineering documentation.
"""

from __future__ import annotations

import struct
from typing import Final

from .models import (
    MAX_INTER_REPEAT_GAP_US,
    MAX_PRICER_FRAME_BYTES,
    MAX_PRICER_REPEATS,
    MIN_PRICER_FRAME_BYTES,
    MIN_PRICER_REPEATS,
    MODULATION_PP4,
    MODULATION_PP16,
    PricerFrameRequest,
)

# Documented PrecIR PP16 header prefix; PP4 has no extra prefix.
# Source: tools_python/pr.py in PrecIR commit b09951e2b3d2741e4ca08f929eafef849f6fc006
PRECIR_PP16_HEADER: Final[bytes] = b"\x00\x00\x00\x40"
PRECIR_PP4_HEADER: Final[bytes] = b""

# Pinned commit SHA and provenance statement
PRECIR_UPSTREAM_COMMIT: Final[str] = "b09951e2b3d2741e4ca08f929eafef849f6fc006"
PRECIR_UPSTREAM_FILE: Final[str] = "tools_python/pr.py"
PRECIR_ADAPTER_PROVENANCE: Final[str] = (
    "Clean-room reimplementation based on PrecIR commit "
    f"{PRECIR_UPSTREAM_COMMIT} ({PRECIR_UPSTREAM_FILE}) under GPL-3.0; "
    "no source code copied."
)

# CRC16 polynomial and initial value used in PrecIR tools_python/pr.py
CRC16_POLYNOMIAL: Final[int] = 0x8408
CRC16_INITIAL: Final[int] = 0x8408


class PrecIRAdapterError(ValueError):
    """Raised when PrecIR frame parameters or lengths fail validation."""


def calculate_precir_crc16(data: bytes | bytearray) -> int:
    """Calculate 16-bit CRC over data bytes using PrecIR crc16 algorithm.

    Polynomial: 0x8408 (reflected 0x1021), initial value 0x8408.
    Matches tools_python/pr.py in PrecIR commit b09951e2b3d2741e4ca08f929eafef849f6fc006.
    Input must be bytes or bytearray. Returns 16-bit integer (0..65535).
    """
    if not isinstance(data, (bytes, bytearray)):
        raise PrecIRAdapterError(f"data must be bytes or bytearray, got {type(data).__name__}")

    crc = CRC16_INITIAL
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc >> 1) ^ CRC16_POLYNOMIAL) & 0xFFFF if crc & 0x0001 else (crc >> 1) & 0xFFFF
    return crc & 0xFFFF


def finalize_precir_frame(
    payload: bytes | bytearray,
    modulation: int = MODULATION_PP16,
    custom_crc: int | None = None,
) -> bytes:
    """Finalize raw frame bytes using PrecIR terminate_frame behavior.

    1. Validates payload type and modulation scheme (16 for PP16, 4 for PP4).
    2. Calculates CRC16 over raw payload bytes BEFORE prepending header.
    3. Prepends 4-byte header prefix (b"\\x00\\x00\\x00\\x40" for PP16).
    4. Appends little-endian 2-byte CRC16.
    5. Validates total finalized frame length is within 1..256 bytes.
    """
    if not isinstance(payload, (bytes, bytearray)):
        raise PrecIRAdapterError(
            f"payload must be bytes or bytearray, got {type(payload).__name__}"
        )

    if modulation == MODULATION_PP16:
        header = PRECIR_PP16_HEADER
    elif modulation == MODULATION_PP4:
        header = PRECIR_PP4_HEADER
    else:
        raise PrecIRAdapterError(f"unsupported modulation {modulation}, expected 16 or 4")

    payload_bytes = bytes(payload)

    # Compute CRC16 over raw payload before header prepending
    if custom_crc is None:
        crc_val = calculate_precir_crc16(payload_bytes)
    else:
        if not 0 <= custom_crc <= 0xFFFF:
            raise PrecIRAdapterError(f"custom_crc must be uint16 (0..65535), got {custom_crc}")
        crc_val = custom_crc

    crc_bytes = struct.pack("<H", crc_val)
    finalized = header + payload_bytes + crc_bytes

    if not MIN_PRICER_FRAME_BYTES <= len(finalized) <= MAX_PRICER_FRAME_BYTES:
        raise PrecIRAdapterError(
            f"finalized frame size ({len(finalized)} bytes) outside allowed range "
            f"[{MIN_PRICER_FRAME_BYTES}..{MAX_PRICER_FRAME_BYTES}]"
        )

    return finalized


def build_pricer_frame_request(
    frame: bytes | bytearray,
    repeats: int = 1,
    inter_repeat_gap_us: int = 0,
    modulation: int = MODULATION_PP16,
) -> PricerFrameRequest:
    """Build a PricerFrameRequest from raw frame bytes.

    Ensures repeat metadata (repeats, inter_repeat_gap_us) remains host-side metadata
    strictly separated from raw frame payload bytes. Validates bounds before returning.
    """
    if not isinstance(frame, (bytes, bytearray)):
        raise PrecIRAdapterError(f"frame must be bytes or bytearray, got {type(frame).__name__}")

    raw_frame = bytes(frame)

    if not MIN_PRICER_FRAME_BYTES <= len(raw_frame) <= MAX_PRICER_FRAME_BYTES:
        raise PrecIRAdapterError(
            f"raw frame length {len(raw_frame)} outside allowed range "
            f"[{MIN_PRICER_FRAME_BYTES}..{MAX_PRICER_FRAME_BYTES}]"
        )

    if not MIN_PRICER_REPEATS <= repeats <= MAX_PRICER_REPEATS:
        raise PrecIRAdapterError(
            f"repeats {repeats} outside allowed range [{MIN_PRICER_REPEATS}..{MAX_PRICER_REPEATS}]"
        )

    if not 0 <= inter_repeat_gap_us <= MAX_INTER_REPEAT_GAP_US:
        raise PrecIRAdapterError(
            f"inter_repeat_gap_us {inter_repeat_gap_us} outside allowed "
            f"range [0..{MAX_INTER_REPEAT_GAP_US}]"
        )

    return PricerFrameRequest(
        frame=raw_frame,
        modulation=modulation,
        repeats=repeats,
        inter_repeat_gap_us=inter_repeat_gap_us,
    )

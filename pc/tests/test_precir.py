from __future__ import annotations

import struct

import pytest

from eslbridge.models import (
    MAX_INTER_REPEAT_GAP_US,
    MAX_PRICER_REPEATS,
    MODULATION_PP4,
    MODULATION_PP16,
)
from eslbridge.precir import (
    CRC16_INITIAL,
    CRC16_POLYNOMIAL,
    PRECIR_ADAPTER_PROVENANCE,
    PRECIR_PP4_HEADER,
    PRECIR_PP16_HEADER,
    PRECIR_UPSTREAM_COMMIT,
    PRECIR_UPSTREAM_FILE,
    PrecIRAdapterError,
    build_pricer_frame_request,
    calculate_precir_crc16,
    finalize_precir_frame,
)


def test_precir_provenance_and_constants() -> None:
    assert PRECIR_UPSTREAM_COMMIT == "b09951e2b3d2741e4ca08f929eafef849f6fc006"
    assert PRECIR_UPSTREAM_FILE == "tools_python/pr.py"
    assert "Clean-room reimplementation" in PRECIR_ADAPTER_PROVENANCE
    assert PRECIR_PP16_HEADER == b"\x00\x00\x00\x40"
    assert PRECIR_PP4_HEADER == b""
    assert CRC16_POLYNOMIAL == 0x8408
    assert CRC16_INITIAL == 0x8408


def test_calculate_precir_crc16_golden_vectors() -> None:
    assert calculate_precir_crc16(b"") == 0x8408
    assert calculate_precir_crc16(b"\x00") == 0x8CCC
    assert calculate_precir_crc16(b"\x01\x02\x03\x04") == 0x4F1A


def test_calculate_precir_crc16_invalid_type_raises() -> None:
    with pytest.raises(PrecIRAdapterError, match="data must be bytes or bytearray"):
        calculate_precir_crc16("invalid string")  # type: ignore[arg-type]


def test_finalize_precir_frame_structure_and_header_placement() -> None:
    payload = b"\x12\x34\x56"
    finalized = finalize_precir_frame(payload, modulation=MODULATION_PP16)

    # Total length: 4 (header) + 3 (payload) + 2 (crc16) = 9 bytes
    assert len(finalized) == 9

    # Header placement at offset 0..4 (PP16 header b"\x00\x00\x00\x40")
    assert finalized[:4] == b"\x00\x00\x00\x40"

    # Payload placement at offset 4..7
    assert finalized[4:7] == b"\x12\x34\x56"

    # CRC16 is computed over payload ONLY (not header!) and appended little-endian
    expected_crc = calculate_precir_crc16(payload)
    actual_crc = struct.unpack("<H", finalized[7:9])[0]
    assert actual_crc == expected_crc


def test_finalize_precir_frame_pp4_header() -> None:
    payload = b"\xaa\xbb"
    finalized = finalize_precir_frame(payload, modulation=MODULATION_PP4)

    assert len(finalized) == 2 + 2
    assert finalized[:2] == b"\xaa\xbb"

    expected_crc = calculate_precir_crc16(payload)
    actual_crc = struct.unpack("<H", finalized[2:4])[0]
    assert actual_crc == expected_crc


def test_finalize_precir_frame_custom_crc_override() -> None:
    payload = b"\x01\x02"
    finalized = finalize_precir_frame(payload, custom_crc=0x1234)

    actual_crc = struct.unpack("<H", finalized[-2:])[0]
    assert actual_crc == 0x1234


def test_repeat_metadata_separation_in_request_builder() -> None:
    payload = b"\x01\x02\x03\x04"
    finalized_frame = finalize_precir_frame(payload)

    # Build request with 5 repeats and 2500 us gap
    req = build_pricer_frame_request(
        frame=finalized_frame,
        repeats=5,
        inter_repeat_gap_us=2500,
    )

    assert req.modulation == MODULATION_PP16
    assert req.repeats == 5
    assert req.inter_repeat_gap_us == 2500

    # Frame bytes exclude repeat metadata appended by the host protocol.
    assert req.frame == finalized_frame
    assert len(req.frame) == len(finalized_frame)


def test_finalize_precir_frame_validation_errors() -> None:
    # Invalid payload type
    with pytest.raises(PrecIRAdapterError, match="payload must be bytes or bytearray"):
        finalize_precir_frame("invalid")  # type: ignore[arg-type]

    # Unsupported modulation
    with pytest.raises(PrecIRAdapterError, match="unsupported modulation"):
        finalize_precir_frame(b"\x00", modulation=8)

    # Invalid custom CRC
    with pytest.raises(PrecIRAdapterError, match="custom_crc must be uint16"):
        finalize_precir_frame(b"\x00", custom_crc=0x10000)

    # Oversized payload resulting in total frame > 256 bytes
    oversized_payload = b"\x00" * 251  # 4 + 251 + 2 = 257 > 256
    with pytest.raises(PrecIRAdapterError, match="finalized frame size"):
        finalize_precir_frame(oversized_payload)


def test_request_builder_bounds_validation() -> None:
    valid_frame = b"\x00\x00\x00\x40\x01\x02\x34\x12"

    # Invalid frame type
    with pytest.raises(PrecIRAdapterError, match="frame must be bytes"):
        build_pricer_frame_request(12345)  # type: ignore[arg-type]

    # Repeats < 1 or > 100
    with pytest.raises(PrecIRAdapterError, match="repeats 0 outside allowed range"):
        build_pricer_frame_request(valid_frame, repeats=0)

    with pytest.raises(PrecIRAdapterError, match=f"repeats {MAX_PRICER_REPEATS + 1}"):
        build_pricer_frame_request(valid_frame, repeats=MAX_PRICER_REPEATS + 1)

    # Inter-repeat gap < 0 or > 1,000,000 us
    with pytest.raises(PrecIRAdapterError, match="inter_repeat_gap_us -1 outside"):
        build_pricer_frame_request(valid_frame, inter_repeat_gap_us=-1)

    with pytest.raises(
        PrecIRAdapterError, match=f"inter_repeat_gap_us {MAX_INTER_REPEAT_GAP_US + 1}"
    ):
        build_pricer_frame_request(valid_frame, inter_repeat_gap_us=MAX_INTER_REPEAT_GAP_US + 1)

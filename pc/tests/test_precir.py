from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

import pytest
from scripts.generate_vectors import make_image_data_bodies, make_vectors

from eslbridge.models import (
    MAX_INTER_REPEAT_GAP_US,
    MAX_PRICER_REPEATS,
    MODULATION_PP4,
    MODULATION_PP16,
)
from eslbridge.precir import (
    BITS_PER_FRAME,
    BYTES_PER_FRAME,
    CRC16_INITIAL,
    CRC16_POLYNOMIAL,
    PRECIR_ADAPTER_PROVENANCE,
    PRECIR_PP4_HEADER,
    PRECIR_PP16_HEADER,
    PRECIR_UPSTREAM_COMMIT,
    PRECIR_UPSTREAM_FILE,
    PrecIRAdapterError,
    PricerPlid,
    build_pricer_frame_request,
    calculate_precir_crc16,
    derive_pricer_plid,
    finalize_precir_frame,
    make_mcu_frame,
    make_raw_frame,
    pad_image_payload,
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

    # Repeats < 1 or > 400
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


TARGET_BARCODE = "N4163114582613272"
TARGET_PLID = PricerPlid(internal=b"\x3f\xb7\xb3\x02", wire=b"\x02\xb3\xb7\x3f")

RAW_IMAGE_PAYLOAD = bytes.fromhex("f00ff00ff00ff00ff00ff00ff00ff00f")
CORRECTED_VECTORS = {
    "wake.bin": "000000408502b3b73f170100000001010101010101010101010101010101010101010101f1c3",
    "params-8x8-color.bin": (
        "000000408502b3b73f340000000500140000010008000800000000000088000000000000789a"
    ),
    "data-8x8-color.bin": (
        "000000408502b3b73f34000000200000f00ff00ff00ff00ff00ff00ff00ff00f00000000f280"
    ),
    "refresh.bin": "000000408502b3b73f3400000001000000000000000000000000000000000000000000008c01",
}


def test_target_barcode_maps_to_precir_internal_and_wire_plid() -> None:
    assert derive_pricer_plid(TARGET_BARCODE) == TARGET_PLID


def test_precir_plid_and_frame_builder_validation() -> None:
    with pytest.raises(PrecIRAdapterError, match="decimal PLID fields"):
        derive_pricer_plid("N-invalid")
    with pytest.raises(PrecIRAdapterError, match="plid must be PricerPlid"):
        make_raw_frame(b"\x00" * 4, 0x17)  # type: ignore[arg-type]
    with pytest.raises(PrecIRAdapterError, match="command must be uint8"):
        make_raw_frame(TARGET_PLID, 0x100)
    with pytest.raises(PrecIRAdapterError, match="body must be bytes"):
        make_mcu_frame(TARGET_PLID, 0x05, "invalid")  # type: ignore[arg-type]


def test_precir_image_group_is_padded_to_complete_data_frame() -> None:
    assert BYTES_PER_FRAME == 20
    assert BITS_PER_FRAME == 160
    assert len(RAW_IMAGE_PAYLOAD) == 16

    padded = pad_image_payload(RAW_IMAGE_PAYLOAD)

    assert len(padded) == BYTES_PER_FRAME
    assert padded == RAW_IMAGE_PAYLOAD + b"\x00" * 4


def test_precir_padding_matches_upstream_for_aligned_payload() -> None:
    assert pad_image_payload(b"\xaa" * BYTES_PER_FRAME) == (
        b"\xaa" * BYTES_PER_FRAME + b"\x00" * BYTES_PER_FRAME
    )


def test_precir_padding_rejects_non_bytes_payload() -> None:
    with pytest.raises(PrecIRAdapterError, match="payload must be bytes, got bytearray"):
        pad_image_payload(bytearray(BYTES_PER_FRAME))  # type: ignore[arg-type]


def test_generated_image_vectors_use_padded_group_length_and_packet_size() -> None:
    _, bodies, frames = make_vectors()
    params_body = bodies["params-8x8-color.bin"]
    data_body = bodies["data-8x8-color.bin"]
    packets = make_image_data_bodies(RAW_IMAGE_PAYLOAD)

    assert len(packets) == 1
    assert packets == [data_body]
    assert int.from_bytes(params_body[:2], "big") == sum(len(packet[2:]) for packet in packets)
    assert all(len(packet[2:]) == BYTES_PER_FRAME for packet in packets)

    assert {name: frame.hex() for name, frame in frames.items()} == CORRECTED_VECTORS


def test_precir_raw_and_mcu_builders_match_independent_golden_frames() -> None:
    assert (
        make_raw_frame(TARGET_PLID, 0x17, bytes.fromhex("01000000" + "01" * 22)).hex()
        == CORRECTED_VECTORS["wake.bin"]
    )
    assert (
        make_mcu_frame(
            TARGET_PLID,
            0x05,
            bytes.fromhex("00140000010008000800000000000088000000000000"),
        ).hex()
        == CORRECTED_VECTORS["params-8x8-color.bin"]
    )
    assert (
        make_mcu_frame(
            TARGET_PLID,
            0x20,
            bytes.fromhex("0000f00ff00ff00ff00ff00ff00ff00ff00f00000000"),
        ).hex()
        == CORRECTED_VECTORS["data-8x8-color.bin"]
    )
    assert make_mcu_frame(TARGET_PLID, 0x01, b"\x00" * 22).hex() == CORRECTED_VECTORS["refresh.bin"]


def test_corrected_vectors_match_manifest_binaries_crc_and_frame_shape() -> None:
    import json
    from pathlib import Path

    root = Path(__file__).parents[2]
    manifest = json.loads((root / "tests" / "vectors" / "manifest.json").read_text())
    entries = {entry["name"]: entry for entry in manifest["vectors"]}

    assert manifest["target"]["barcode"] == TARGET_BARCODE
    assert manifest["target"]["plid_formula_result"] == "02b3b73f"
    assert manifest["target"]["raw_frame_plid_order"] == "02b3b73f"
    for name, expected_hex in CORRECTED_VECTORS.items():
        entry = entries[name]
        frame = bytes.fromhex(expected_hex)
        assert (root / "tests" / "vectors" / name).read_bytes() == frame
        assert entry["finalized_hex"] == expected_hex
        assert frame[-2:].hex() == entry["crc16_le_hex"]
        assert frame[5:9] == TARGET_PLID.wire
        if name == "wake.bin":
            assert b"\x34\x00\x00\x00" not in frame[4:-2]
        else:
            assert frame[9:13] == b"\x34\x00\x00\x00"
            assert frame[13] == int(entry["command"], 16)


def test_corrected_parameter_vector_has_raw_page_one_fields() -> None:
    frame = bytes.fromhex(CORRECTED_VECTORS["params-8x8-color.bin"])
    command_payload = frame[14:-2]
    assert command_payload[:2] == b"\x00\x14"
    assert command_payload[2] == 0
    assert command_payload[3] == 0
    assert command_payload[4] == 1
    assert command_payload[5:7] == b"\x00\x08"
    assert command_payload[7:9] == b"\x00\x08"


def test_embedded_orientation_vectors_match_retained_binaries() -> None:
    import re
    from pathlib import Path

    root = Path(__file__).parents[2]
    source = (root / "firmware" / "src" / "orientation_test.cpp").read_text()
    symbols = {
        "wake.bin": "PrecirWake",
        "params-8x8-color.bin": "PrecirParams",
        "data-8x8-color.bin": "PrecirData",
        "refresh.bin": "PrecirRefresh",
    }
    for name, symbol in symbols.items():
        match = re.search(
            rf"constexpr std::uint8_t k{symbol}Frame\[\] = \{{(.*?)\n\}};",
            source,
            flags=re.DOTALL,
        )
        assert match is not None
        embedded = bytes(int(token, 16) for token in re.findall(r"0x([0-9A-F]{2})", match.group(1)))
        assert embedded == bytes.fromhex(CORRECTED_VECTORS[name])

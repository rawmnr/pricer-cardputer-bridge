from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from eslbridge.airframe import (
    AIRFRAME_DONGLE_HEADER,
    TAGTINKER_BARCODE,
    TAGTINKER_DATA_FRAME_COUNT,
    TAGTINKER_GAP_US,
    TAGTINKER_HEIGHT,
    TAGTINKER_PADDED_BYTES,
    TAGTINKER_PAGE,
    TAGTINKER_PLANE_BITS,
    TAGTINKER_PLANE_BYTES,
    TAGTINKER_RAW_BYTES,
    TAGTINKER_REPEAT_COUNTS,
    TAGTINKER_WIDTH,
    make_tagtinker_data_frame,
    make_tagtinker_params_frame,
    make_tagtinker_ping_frame,
    make_tagtinker_profile,
    make_tagtinker_refresh_frame,
    make_two_plane_payload,
    packetize_tagtinker_image,
)
from eslbridge.precir import MODULATION_PP4, calculate_precir_crc16, derive_pricer_plid

PLID = derive_pricer_plid(TAGTINKER_BARCODE)
PING_GOLDEN = bytes.fromhex("8502b3b73f97010000000101010101010101010101010101010101010101402c")


def test_ping_is_exact_32_byte_direct_airframe() -> None:
    frame = make_tagtinker_ping_frame(PLID)
    assert frame == PING_GOLDEN
    assert len(frame) == 32
    assert not frame.startswith(AIRFRAME_DONGLE_HEADER)


def test_direct_builders_never_emit_legacy_dongle_prefix() -> None:
    vectors = make_tagtinker_profile(PLID)
    assert all(not vector.frame.startswith(AIRFRAME_DONGLE_HEADER) for vector in vectors)
    assert vectors[0].frame == make_tagtinker_ping_frame(PLID)
    assert vectors[1].frame == make_tagtinker_params_frame(PLID)
    assert vectors[-1].frame == make_tagtinker_refresh_frame(PLID)


def test_type_1327_shape_and_blank_accent_plane_are_msb_first() -> None:
    assert (TAGTINKER_WIDTH, TAGTINKER_HEIGHT) == (208, 112)
    assert TAGTINKER_PLANE_BYTES == 2_912
    assert TAGTINKER_RAW_BYTES == 5_824
    primary = [1] + [0] * (TAGTINKER_PLANE_BITS - 1)
    accent = [0] * TAGTINKER_PLANE_BITS
    payload = make_two_plane_payload(primary, accent)
    assert len(payload) == TAGTINKER_RAW_BYTES
    assert payload[0] == 0x80
    assert payload[1:TAGTINKER_PLANE_BYTES] == b"\x00" * (TAGTINKER_PLANE_BYTES - 1)
    assert payload[TAGTINKER_PLANE_BYTES:] == b"\x00" * TAGTINKER_PLANE_BYTES


def test_raw_payload_pads_to_292_big_endian_indexed_packets() -> None:
    payload = bytes(range(256)) * (TAGTINKER_RAW_BYTES // 256) + bytes(
        range(TAGTINKER_RAW_BYTES % 256)
    )
    packets = packetize_tagtinker_image(payload)
    assert len(packets) == TAGTINKER_DATA_FRAME_COUNT == 292
    assert all(len(packet) == 22 for packet in packets)
    assert packets[0][:2] == b"\x00\x00"
    assert packets[1][:2] == b"\x00\x01"
    assert packets[-1][:2] == b"\x01\x23"
    assert sum(len(packet[2:]) for packet in packets) == TAGTINKER_PADDED_BYTES
    assert packets[-1][-16:] == b"\x00" * 16


def test_image_fields_and_crc_wire_endianness() -> None:
    frame = make_tagtinker_params_frame(PLID)
    assert frame[0:5] == b"\x85\x02\xb3\xb7\x3f"
    assert frame[5:9] == b"\x34\x00\x00\x00"
    assert frame[9] == 0x05
    assert frame[10:12] == TAGTINKER_PADDED_BYTES.to_bytes(2, "big")
    assert frame[12:15] == bytes((0, 0, TAGTINKER_PAGE))
    assert frame[15:17] == TAGTINKER_WIDTH.to_bytes(2, "big")
    assert frame[17:19] == TAGTINKER_HEIGHT.to_bytes(2, "big")
    assert int.from_bytes(frame[-2:], "little") == calculate_precir_crc16(frame[:-2])

    data = bytes(range(20))
    data_frame = make_tagtinker_data_frame(PLID, 0x0123, data)
    assert data_frame[10:12] == b"\x01\x23"
    assert data_frame[12:32] == data
    assert int.from_bytes(data_frame[-2:], "little") == calculate_precir_crc16(data_frame[:-2])


def test_profile_builder_is_deterministic_and_metadata_is_separate() -> None:
    first = make_tagtinker_profile(PLID)
    second = make_tagtinker_profile(PLID)
    assert first == second
    assert [vector.repeats for vector in (first[0], first[1], first[2], first[-1])] == list(
        TAGTINKER_REPEAT_COUNTS
    )
    assert {vector.inter_repeat_gap_us for vector in first} == {TAGTINKER_GAP_US}
    assert all(vector.request().frame == vector.frame for vector in first)
    assert all(vector.request().modulation == MODULATION_PP4 for vector in first)
    assert all(vector.request().repeats == vector.repeats for vector in first)


def test_generated_tagtinker_manifest_and_binary_vectors() -> None:
    root = Path(__file__).parents[2]
    manifest = json.loads((root / "tests" / "vectors" / "manifest.json").read_text())
    profile = manifest["tagtinker_1327"]
    assert profile["barcode"] == TAGTINKER_BARCODE
    assert profile["plid_wire_hex"] == PLID.wire.hex()
    assert profile["page"] == TAGTINKER_PAGE
    assert profile["raw_bytes"] == TAGTINKER_RAW_BYTES
    assert profile["padded_bytes"] == TAGTINKER_PADDED_BYTES
    assert profile["packet_count"] == TAGTINKER_DATA_FRAME_COUNT
    vectors = profile["vectors"]
    generated = make_tagtinker_profile(PLID)
    assert len(vectors) == len(generated) == TAGTINKER_DATA_FRAME_COUNT + 3
    for entry, vector in zip(vectors, generated, strict=True):
        assert entry["finalized_hex"] == vector.frame.hex()
        assert (root / "tests" / "vectors" / entry["name"]).read_bytes() == vector.frame

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

import pytest
from scripts.generate_vectors import BARCODE, make_pricehax_vectors

from eslbridge.precir import derive_pricer_plid
from eslbridge.pricehax import (
    PRICEHAX_BYTES_PER_FRAME,
    PRICEHAX_HEIGHT,
    PRICEHAX_RAW_BITS,
    PRICEHAX_RAW_BYTES,
    PRICEHAX_TYPE_CODE,
    PRICEHAX_WIDTH,
    PricehaxProfileError,
    encode_pricehax_raw,
    encode_pricehax_rle,
    make_all_white_type_1327_image,
    make_all_white_type_1327_raw_image,
    make_pricehax_data_bodies,
)

EXACT_GOLDEN = {
    "pricehax-wake-97.bin": (
        "000000408502b3b73f97010000000101010101010101010101010101010101010101402c"
    ),
    "pricehax-params-page2.bin": (
        "000000408502b3b73f3400000005002800020200d000700000000000008800000000000028f4"
    ),
    "pricehax-data-0000.bin": (
        "000000408502b3b73f340000002000008000b5ff0000000000000000000000000000000000"
        "00000000000000000000000000000000000000cb1a"
    ),
    "pricehax-refresh.bin": (
        "000000408502b3b73f3400000001000000000000000000000000000000000000fbd5"
    ),
}


def test_type_1327_full_screen_profile_shape() -> None:
    assert PRICEHAX_TYPE_CODE == 1327
    assert (PRICEHAX_WIDTH, PRICEHAX_HEIGHT) == (208, 112)
    assert PRICEHAX_RAW_BITS == 46_592
    assert PRICEHAX_RAW_BYTES == 5_824


def _upstream_rle_reference(raw_bits: bytes) -> bytes:
    runs: list[int] = []
    last_index = len(raw_bits) - 1
    count = 1
    previous = raw_bits[0]
    for index in range(1, last_index + 1):
        current = raw_bits[index]
        if current == previous:
            count += 1
            if index == last_index - 1:
                runs.append(count)
        else:
            runs.append(count)
            count = 1
            if index == last_index - 1:
                runs.append(1)
        previous = current

    bit_string = str(raw_bits[0])
    for count in runs:
        binary = f"{count:b}"
        bit_string += "0" * (len(binary) - 1) + binary
    bit_string += "0" * (-len(bit_string) % 8)
    return int(bit_string, 2).to_bytes(len(bit_string) // 8, "big")


def test_all_white_image_uses_deterministic_rle_and_one_packet() -> None:
    encoded = make_all_white_type_1327_image()

    assert encoded.compression_type == 2
    assert encoded.payload.hex() == "8000b5ff"
    assert len(encoded.payload) == 4
    assert len(encoded.padded_payload) == PRICEHAX_BYTES_PER_FRAME
    assert encoded.announced_length == PRICEHAX_BYTES_PER_FRAME
    assert make_pricehax_data_bodies(encoded) == [b"\x00\x00" + encoded.padded_payload]


def test_exact_rle_matches_literal_upstream_control_flow() -> None:
    raw_bits = bytes((1,)) * PRICEHAX_RAW_BITS

    assert _upstream_rle_reference(raw_bits).hex() == "8000b5ff"
    assert encode_pricehax_rle(raw_bits).payload == _upstream_rle_reference(raw_bits)


def test_raw_profile_announces_unpadded_length_and_packetizes_146_frames() -> None:
    raw_bits = bytes((1,)) * PRICEHAX_RAW_BITS
    encoded = encode_pricehax_raw(raw_bits)

    assert encoded == make_all_white_type_1327_raw_image()
    assert encoded.compression_type == 0
    assert encoded.announced_length == 5_824
    assert len(encoded.payload) == 5_824
    assert len(encoded.padded_payload) == 5_840
    assert len(make_pricehax_data_bodies(encoded)) == 146


def test_pricehax_encoder_rejects_wrong_shape_and_non_bits() -> None:
    with pytest.raises(PricehaxProfileError, match="must contain 46592 bits"):
        encode_pricehax_rle(b"\x01")
    with pytest.raises(PricehaxProfileError, match="only 0 or 1"):
        encode_pricehax_rle(bytes((2,)) * PRICEHAX_RAW_BITS)


def test_exact_vectors_match_independent_golden_values() -> None:
    vectors = make_pricehax_vectors(derive_pricer_plid(BARCODE))

    assert {vector.name: vector.frame.hex() for vector in vectors} == EXACT_GOLDEN
    assert [(vector.command, vector.repeats) for vector in vectors] == [
        (0x97, 500),
        (0x05, 10),
        (0x20, 3),
        (0x01, 50),
    ]
    assert len(vectors[0].body) == 24
    assert len(vectors[2].body[2:]) == 40
    assert len(vectors[-1].body) == 18


def test_page1_variant_changes_only_page_field() -> None:
    plid = derive_pricer_plid(BARCODE)
    exact = make_pricehax_vectors(plid)
    page1 = make_pricehax_vectors(plid, page=1)

    assert page1[0] == exact[0]
    assert page1[1].body[:4] == exact[1].body[:4]
    assert page1[1].body[4] == 1
    assert exact[1].body[4] == 2
    assert page1[2:] == exact[2:]


def test_manifest_retains_lengths_crc_and_repeat_metadata() -> None:
    root = Path(__file__).parents[2]
    manifest = json.loads((root / "tests" / "vectors" / "manifest.json").read_text())
    profile = manifest["pricehax_1327"]

    assert manifest["profile_revision"] == "T008E-r1"
    assert profile["image"] == {
        "description": "full-screen all-white, upstream-exact compressed two planes",
        "width": 208,
        "height": 112,
        "raw_bit_count": 46_592,
        "raw_byte_count": 5_824,
        "encoded_unpadded_length": 4,
        "encoded_padded_length": 40,
        "announced_length": 40,
        "frame_count": 1,
    }
    for entry in profile["vectors"]:
        frame = bytes.fromhex(entry["finalized_hex"])
        assert (root / "tests" / "vectors" / entry["name"]).read_bytes() == frame
        assert frame[-2:].hex() == entry["crc16_le_hex"]

    raw_profile = manifest["pricehax_1327_raw"]
    assert raw_profile["image"] == {
        "description": "full-screen all-white, raw two planes",
        "width": 208,
        "height": 112,
        "raw_bit_count": 46_592,
        "raw_byte_count": 5_824,
        "encoded_unpadded_length": 5_824,
        "encoded_padded_length": 5_840,
        "announced_length": 5_824,
        "frame_count": 146,
    }
    assert len(raw_profile["vectors"]) == 149

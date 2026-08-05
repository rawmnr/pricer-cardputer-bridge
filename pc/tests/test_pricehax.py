from __future__ import annotations

import json
from pathlib import Path

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
    encode_pricehax_rle,
    make_all_white_type_1327_image,
    make_pricehax_data_bodies,
)

EXACT_GOLDEN = {
    "pricehax-wake-97.bin": (
        "000000408502b3b73f97010000000101010101010101010101010101010101010101402c"
    ),
    "pricehax-params-page2.bin": (
        "000000408502b3b73f3400000005000400020200d00070000000000000880000000000000f47"
    ),
    "pricehax-data-0000.bin": (
        "000000408502b3b73f340000002000008000b6000000000000000000000000000000000000"
        "000000000000000000000000000000000000007d18"
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


def test_all_white_image_uses_deterministic_rle_and_one_packet() -> None:
    encoded = make_all_white_type_1327_image()

    assert encoded.compression_type == 2
    assert encoded.payload.hex() == "8000b600"
    assert len(encoded.payload) == 4
    assert len(encoded.padded_payload) == PRICEHAX_BYTES_PER_FRAME
    assert make_pricehax_data_bodies(encoded) == [b"\x00\x00" + encoded.padded_payload]


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


def test_wake17_and_page1_variants_change_only_the_isolated_field() -> None:
    plid = derive_pricer_plid(BARCODE)
    exact = make_pricehax_vectors(plid)
    wake17 = make_pricehax_vectors(plid, wake_command=0x17)
    page1 = make_pricehax_vectors(plid, page=1)

    assert wake17[0].command == 0x17
    assert len(wake17[0].body) == 26
    assert wake17[1:] == exact[1:]
    assert page1[0] == exact[0]
    assert page1[1].body[:4] == exact[1].body[:4]
    assert page1[1].body[4] == 1
    assert exact[1].body[4] == 2
    assert page1[2:] == exact[2:]


def test_manifest_retains_lengths_crc_and_repeat_metadata() -> None:
    root = Path(__file__).parents[2]
    manifest = json.loads((root / "tests" / "vectors" / "manifest.json").read_text())
    profile = manifest["pricehax_1327"]

    assert manifest["profile_revision"] == "T008D-r1"
    assert profile["image"] == {
        "description": "full-screen all-white, two planes",
        "width": 208,
        "height": 112,
        "raw_bit_count": 46_592,
        "raw_byte_count": 5_824,
        "encoded_unpadded_length": 4,
        "encoded_padded_length": 40,
        "frame_count": 1,
    }
    for entry in profile["vectors"]:
        frame = bytes.fromhex(entry["finalized_hex"])
        assert (root / "tests" / "vectors" / entry["name"]).read_bytes() == frame
        assert frame[-2:].hex() == entry["crc16_le_hex"]

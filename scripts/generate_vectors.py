"""Generate retained PrecIR and PricehaxBT type-1327 vectors."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pc" / "src"))

from eslbridge.airframe import (
    TAGTINKER_BARCODE,
    TAGTINKER_DATA_FRAME_COUNT,
    TAGTINKER_HEIGHT,
    TAGTINKER_PADDED_BYTES,
    TAGTINKER_PAGE,
    TAGTINKER_PLANE_BYTES,
    TAGTINKER_RAW_BYTES,
    TAGTINKER_TYPE_CODE,
    TAGTINKER_WIDTH,
    AirFrame,
    make_tagtinker_profile,
)
from eslbridge.precir import (
    BYTES_PER_FRAME,
    PricerPlid,
    derive_pricer_plid,
    make_mcu_frame,
    make_raw_frame,
    pad_image_payload,
)
from eslbridge.pricehax import (
    PRICEHAX_BYTES_PER_FRAME,
    PRICEHAX_HEIGHT,
    PRICEHAX_RAW_BITS,
    PRICEHAX_RAW_BYTES,
    PRICEHAX_TYPE_CODE,
    PRICEHAX_UPSTREAM_COMMIT,
    PRICEHAX_WIDTH,
    EncodedImage,
    make_all_white_type_1327_image,
    make_all_white_type_1327_raw_image,
    make_pricehax_data_bodies,
)

BARCODE = TAGTINKER_BARCODE
PROFILE_REVISION = "T008E-r1"
AIRFRAME_PROFILE_REVISION = "T008F-r1"
VECTOR_DIR = ROOT / "tests" / "vectors"
ORIENTATION_SOURCE = ROOT / "firmware" / "src" / "orientation_test.cpp"
RAW_IMAGE_PAYLOAD = bytes.fromhex("f00ff00ff00ff00ff00ff00ff00ff00f")


@dataclass(frozen=True, slots=True)
class Vector:
    name: str
    command: int
    body: bytes
    frame: bytes
    repeats: int
    inter_repeat_gap_us: int


def make_image_data_bodies(payload: bytes) -> list[bytes]:
    padded_payload = pad_image_payload(payload)
    return [
        packet_index.to_bytes(2, "big")
        + padded_payload[offset : offset + BYTES_PER_FRAME]
        for packet_index, offset in enumerate(
            range(0, len(padded_payload), BYTES_PER_FRAME)
        )
    ]


def cpp_bytes(frame: bytes) -> str:
    rows = []
    for offset in range(0, len(frame), 13):
        values = ", ".join(f"0x{value:02X}" for value in frame[offset : offset + 13])
        rows.append(f"    {values},")
    return "\n".join(rows)


def make_precir_vectors(plid: PricerPlid) -> list[Vector]:
    padded_image = pad_image_payload(RAW_IMAGE_PAYLOAD)
    image_data_bodies = make_image_data_bodies(RAW_IMAGE_PAYLOAD)
    assert len(image_data_bodies) == 1
    definitions = (
        (
            "precir-wake.bin",
            0x17,
            bytes.fromhex("01000000" + "01" * 22),
            400,
            2_000,
            False,
        ),
        (
            "precir-params-8x8-color.bin",
            0x05,
            len(padded_image).to_bytes(2, "big")
            + bytes.fromhex("0000010008000800000000000088000000000000"),
            1,
            0,
            True,
        ),
        ("precir-data-8x8-color.bin", 0x20, image_data_bodies[0], 1, 0, True),
        ("precir-refresh.bin", 0x01, b"\x00" * 22, 1, 0, True),
    )
    return [
        Vector(
            name,
            command,
            body,
            make_mcu_frame(plid, command, body)
            if mcu
            else make_raw_frame(plid, command, body),
            repeats,
            gap,
        )
        for name, command, body, repeats, gap, mcu in definitions
    ]


def make_vectors() -> tuple[PricerPlid, dict[str, bytes], dict[str, bytes]]:
    """Return the retained T008C control vectors under historical names."""
    plid = derive_pricer_plid(BARCODE)
    vectors = make_precir_vectors(plid)
    historical_names = (
        "wake.bin",
        "params-8x8-color.bin",
        "data-8x8-color.bin",
        "refresh.bin",
    )
    bodies = {
        name: vector.body
        for name, vector in zip(historical_names, vectors, strict=True)
    }
    frames = {
        name: vector.frame
        for name, vector in zip(historical_names, vectors, strict=True)
    }
    return plid, bodies, frames


def make_pricehax_vectors(
    plid: PricerPlid,
    *,
    page: int = 2,
    raw: bool = False,
) -> list[Vector]:
    encoded = (
        make_all_white_type_1327_raw_image()
        if raw
        else make_all_white_type_1327_image()
    )
    packets = make_pricehax_data_bodies(encoded)
    assert encoded.announced_length <= 0xFFFF
    profile_name = "pricehax-raw" if raw else "pricehax"
    params_body = (
        encoded.announced_length.to_bytes(2, "big")
        + bytes((0, encoded.compression_type, page))
        + PRICEHAX_WIDTH.to_bytes(2, "big")
        + PRICEHAX_HEIGHT.to_bytes(2, "big")
        + bytes.fromhex("00000000000088000000000000")
    )
    wake_body = bytes.fromhex("01000000" + "01" * 20)
    definitions: list[tuple[str, int, bytes, int, bool]] = [
        ("pricehax-wake-97.bin", 0x97, wake_body, 500, False),
        (f"{profile_name}-params-page{page}.bin", 0x05, params_body, 10, True),
    ]
    definitions.extend(
        (f"{profile_name}-data-{index:04d}.bin", 0x20, body, 3, True)
        for index, body in enumerate(packets)
    )
    definitions.append(("pricehax-refresh.bin", 0x01, b"\x00" * 18, 50, True))
    return [
        Vector(
            name,
            command,
            body,
            make_mcu_frame(plid, command, body)
            if mcu
            else make_raw_frame(plid, command, body),
            repeats,
            2_000,
        )
        for name, command, body, repeats, mcu in definitions
    ]


def vector_manifest(vector: Vector) -> dict[str, object]:
    return {
        "name": vector.name,
        "command": f"0x{vector.command:02x}",
        "frame_length": len(vector.frame),
        "payload_hex": vector.body.hex(),
        "finalized_hex": vector.frame.hex(),
        "crc16_le_hex": vector.frame[-2:].hex(),
        "repeats": vector.repeats,
        "inter_repeat_gap_us": vector.inter_repeat_gap_us,
    }


def airframe_manifest(vector: AirFrame) -> dict[str, object]:
    return {
        "name": vector.name,
        "command": f"0x{vector.command:02x}",
        "frame_length": len(vector.frame),
        "finalized_hex": vector.frame.hex(),
        "crc16_le_hex": vector.frame[-2:].hex(),
        "repeats": vector.repeats,
        "inter_repeat_gap_us": vector.inter_repeat_gap_us,
    }


def image_manifest(description: str, encoded: EncodedImage) -> dict[str, object]:
    return {
        "description": description,
        "width": PRICEHAX_WIDTH,
        "height": PRICEHAX_HEIGHT,
        "raw_bit_count": PRICEHAX_RAW_BITS,
        "raw_byte_count": PRICEHAX_RAW_BYTES,
        "encoded_unpadded_length": len(encoded.payload),
        "encoded_padded_length": len(encoded.padded_payload),
        "announced_length": encoded.announced_length,
        "frame_count": len(encoded.padded_payload) // PRICEHAX_BYTES_PER_FRAME,
    }

def write_manifest(
    plid: PricerPlid,
    precir: list[Vector],
    compressed: list[Vector],
    raw: list[Vector],
    airframes: list[AirFrame],
) -> None:
    historical_names = (
        "legacy-precir-wake.bin",
        "legacy-precir-params-8x8-color.bin",
        "legacy-precir-data-8x8-color.bin",
        "legacy-precir-refresh.bin",
    )
    manifest = {
        "target": {
            "marking": "#19523-01",
            "barcode": BARCODE,
            "type_code": PRICEHAX_TYPE_CODE,
            "profile": "SmartTag HD M Red 208x112",
            "plid_internal_order": plid.internal.hex(),
            "plid_formula_result": plid.wire.hex(),
            "raw_frame_plid_order": plid.wire.hex(),
            "modulation": 16,
        },
        "profile_revision": AIRFRAME_PROFILE_REVISION,
        "legacy_profile_revision": PROFILE_REVISION,
        "vectors": [
            {**vector_manifest(vector), "name": historical_name}
            for historical_name, vector in zip(historical_names, precir, strict=True)
        ],
        "precir_control": {
            "vectors": [
                {**vector_manifest(vector), "name": f"legacy-{vector.name}"}
                for vector in precir
            ]
        },
        "pricehax_1327": {
            "upstream_commit": PRICEHAX_UPSTREAM_COMMIT,
            "image": image_manifest(
                "full-screen all-white, upstream-exact compressed two planes",
                make_all_white_type_1327_image(),
            ),
            "vectors": [
                {**vector_manifest(vector), "name": f"legacy-{vector.name}"}
                for vector in compressed
            ],
        },
        "pricehax_1327_raw": {
            "upstream_commit": PRICEHAX_UPSTREAM_COMMIT,
            "image": image_manifest(
                "full-screen all-white, raw two planes",
                make_all_white_type_1327_raw_image(),
            ),
            "vectors": [
                {**vector_manifest(vector), "name": f"legacy-{vector.name}"}
                for vector in raw
            ],
        },
        "tagtinker_1327": {
            "profile_revision": AIRFRAME_PROFILE_REVISION,
            "source": "i12bp8/TagTinker protocol/tagtinker_proto.c",
            "barcode": TAGTINKER_BARCODE,
            "type_code": TAGTINKER_TYPE_CODE,
            "plid_wire_hex": plid.wire.hex(),
            "page": TAGTINKER_PAGE,
            "width": TAGTINKER_WIDTH,
            "height": TAGTINKER_HEIGHT,
            "plane_bytes": TAGTINKER_PLANE_BYTES,
            "raw_bytes": TAGTINKER_RAW_BYTES,
            "padded_bytes": TAGTINKER_PADDED_BYTES,
            "packet_bytes": 20,
            "packet_count": TAGTINKER_DATA_FRAME_COUNT,
            "compression_type": 0,
            "vectors": [airframe_manifest(vector) for vector in airframes],
        },
    }
    (VECTOR_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def array_definition(symbol: str, frame: bytes) -> str:
    return f"constexpr std::uint8_t {symbol}[] = {{\n{cpp_bytes(frame)}\n}};"


def frame_entry(
    symbol: str,
    vector: Vector,
    *,
    repeats: int | None = None,
    pre_gap_us: int = 0,
) -> str:
    repeat_count = vector.repeats if repeats is None else repeats
    return (
        f"    {{{symbol}, sizeof({symbol}), {repeat_count}, "
        f"{vector.inter_repeat_gap_us}, {pre_gap_us}}},"
    )


def plan_definition(
    symbol: str,
    vectors: list[Vector],
    frame_symbols: list[str],
) -> str:
    entries = [
        frame_entry(frame_symbols[0], vectors[0], repeats=250),
        frame_entry(frame_symbols[0], vectors[0], repeats=250, pre_gap_us=2_000),
    ]
    entries.extend(
        frame_entry(frame_symbol, vector)
        for frame_symbol, vector in zip(frame_symbols[1:], vectors[1:], strict=True)
    )
    entries_source = "\n".join(entries)
    return f"""constexpr OrientationTestFrame {symbol}Frames[] = {{
{entries_source}
}};
constexpr OrientationTestPlan {symbol}Plan = {{
    {symbol}Frames,
    sizeof({symbol}Frames) / sizeof({symbol}Frames[0]),
}};"""


def write_orientation_source(
    precir: list[Vector],
    compressed: list[Vector],
    raw: list[Vector],
    page1: list[Vector],
) -> None:
    arrays: dict[str, bytes] = {
        "kPrecirWakeFrame": precir[0].frame,
        "kPrecirParamsFrame": precir[1].frame,
        "kPrecirDataFrame": precir[2].frame,
        "kPrecirRefreshFrame": precir[3].frame,
        "kPricehaxWake97Frame": compressed[0].frame,
        "kPricehaxParamsPage2Frame": compressed[1].frame,
        "kPricehaxDataFrame": compressed[2].frame,
        "kPricehaxRefreshFrame": compressed[-1].frame,
        "kPricehaxParamsPage1Frame": page1[1].frame,
        "kPricehaxRawParamsFrame": raw[1].frame,
    }
    raw_data_symbols = []
    for index, vector in enumerate(raw[2:-1]):
        symbol = f"kPricehaxRawData{index:04d}Frame"
        arrays[symbol] = vector.frame
        raw_data_symbols.append(symbol)

    array_source = "\n\n".join(
        array_definition(symbol, frame) for symbol, frame in arrays.items()
    )
    precir_entries = "\n".join(
        frame_entry(symbol, vector)
        for symbol, vector in zip(
            (
                "kPrecirWakeFrame",
                "kPrecirParamsFrame",
                "kPrecirDataFrame",
                "kPrecirRefreshFrame",
            ),
            precir,
            strict=True,
        )
    )
    compressed_symbols = [
        "kPricehaxWake97Frame",
        "kPricehaxParamsPage2Frame",
        "kPricehaxDataFrame",
        "kPricehaxRefreshFrame",
    ]
    raw_symbols = [
        "kPricehaxWake97Frame",
        "kPricehaxRawParamsFrame",
        *raw_data_symbols,
        "kPricehaxRefreshFrame",
    ]
    page1_symbols = [
        "kPricehaxWake97Frame",
        "kPricehaxParamsPage1Frame",
        "kPricehaxDataFrame",
        "kPricehaxRefreshFrame",
    ]
    source = f"""#include "orientation_test.hpp"

#include <Arduino.h>

#include "ir_transmitter.hpp"

// Generated by scripts/generate_vectors.py; do not edit frame arrays manually.
namespace eslbridge {{
namespace {{

{array_source}

constexpr OrientationTestFrame kPrecirControlFrames[] = {{
{precir_entries}
}};
constexpr OrientationTestPlan kPrecirControlPlan = {{
    kPrecirControlFrames,
    sizeof(kPrecirControlFrames) / sizeof(kPrecirControlFrames[0]),
}};

{plan_definition("kPricehaxExact", compressed, compressed_symbols)}

{plan_definition("kPricehaxRaw", raw, raw_symbols)}

{plan_definition("kPricehaxPage1", page1, page1_symbols)}

}}  // namespace

const OrientationTestPlan& orientation_test_plan(const OrientationTest test) {{
    switch (test) {{
        case OrientationTest::kOne:
            return kPrecirControlPlan;
        case OrientationTest::kTwo:
            return kPricehaxExactPlan;
        case OrientationTest::kThree:
            return kPricehaxRawPlan;
        case OrientationTest::kFour:
            return kPricehaxPage1Plan;
        default:
            return kPrecirControlPlan;
    }}
}}

const char* orientation_test_name(const OrientationTest test) {{
    switch (test) {{
        case OrientationTest::kOne:
            return "PRECIR_CONTROL";
        case OrientationTest::kTwo:
            return "PRICEHAX_EXACT";
        case OrientationTest::kThree:
            return "PRICEHAX_RAW";
        case OrientationTest::kFour:
            return "PRICEHAX_PAGE1";
        default:
            return "NONE";
    }}
}}

protocol::Status run_orientation_test(
    IrTransmitter& transmitter,
    const OrientationTest test) {{
    if (test == OrientationTest::kNone) {{
        return protocol::Status::kInvalidArgument;
    }}
    const auto& plan = orientation_test_plan(test);
    for (std::size_t index = 0; index < plan.frame_count; ++index) {{
        const auto& frame = plan.frames[index];
        if (frame.pre_transmit_gap_us != 0) {{
            delayMicroseconds(frame.pre_transmit_gap_us);
        }}
        const auto status = transmitter.send_pricer_frame(
            16, frame.repeats, frame.inter_repeat_gap_us, frame.data, frame.length);
        if (status != protocol::Status::kOk) {{
            return status;
        }}
    }}
    return protocol::Status::kOk;
}}

}}  // namespace eslbridge
"""
    ORIENTATION_SOURCE.write_text(source, encoding="utf-8")


def write_tagtinker_orientation_source(vectors: list[AirFrame]) -> None:
    symbols = [f"kTagTinker1327Frame{index:04d}" for index in range(len(vectors))]
    arrays = "\n\n".join(
        array_definition(symbol, vector.frame) for symbol, vector in zip(symbols, vectors, strict=True)
    )
    entries = "\n".join(
        f"    {{{symbol}, sizeof({symbol}), {vector.repeats}, "
        f"{vector.inter_repeat_gap_us}, 0}},"
        for symbol, vector in zip(symbols, vectors, strict=True)
    )
    source = f"""#include "orientation_test.hpp"

#include <Arduino.h>

#include "ir_transmitter.hpp"

// Generated by scripts/generate_vectors.py; direct TagTinker AirFrames only.
namespace eslbridge {{
namespace {{

{arrays}

constexpr OrientationTestFrame kTagTinker1327Frames[] = {{
{entries}
}};
constexpr OrientationTestPlan kTagTinker1327Plan = {{
    kTagTinker1327Frames,
    sizeof(kTagTinker1327Frames) / sizeof(kTagTinker1327Frames[0]),
}};

}}  // namespace

const OrientationTestPlan& orientation_test_plan(const OrientationTest test) {{
    switch (test) {{
        case OrientationTest::kOne:
        case OrientationTest::kTwo:
        case OrientationTest::kThree:
        case OrientationTest::kFour:
            return kTagTinker1327Plan;
        default:
            return kTagTinker1327Plan;
    }}
}}

const char* orientation_test_name(const OrientationTest test) {{
    return test == OrientationTest::kNone ? "NONE" : "TAGTINKER_1327";
}}

protocol::Status run_orientation_test(
    IrTransmitter& transmitter,
    const OrientationTest test) {{
    if (test == OrientationTest::kNone) {{
        return protocol::Status::kInvalidArgument;
    }}
    const auto& plan = orientation_test_plan(test);
    for (std::size_t index = 0; index < plan.frame_count; ++index) {{
        const auto& frame = plan.frames[index];
        if (frame.pre_transmit_gap_us != 0) {{
            delayMicroseconds(frame.pre_transmit_gap_us);
        }}
        const auto status = transmitter.send_pricer_frame(
            16, frame.repeats, frame.inter_repeat_gap_us, frame.data, frame.length);
        if (status != protocol::Status::kOk) {{
            return status;
        }}
    }}
    return protocol::Status::kOk;
}}

}}  // namespace eslbridge
"""
    ORIENTATION_SOURCE.write_text(source, encoding="utf-8")


def main() -> None:
    plid = derive_pricer_plid(BARCODE)
    assert plid == PricerPlid(internal=b"\x3f\xb7\xb3\x02", wire=b"\x02\xb3\xb7\x3f")
    precir = make_precir_vectors(plid)
    compressed = make_pricehax_vectors(plid)
    raw = make_pricehax_vectors(plid, raw=True)
    page1 = make_pricehax_vectors(plid, page=1)
    airframes = make_tagtinker_profile(plid)

    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    _, _, historical_frames = make_vectors()
    retained = {
        **{f"legacy-precir-{name}": frame for name, frame in historical_frames.items()},
        **{
            f"legacy-{vector.name}": vector.frame
            for vector in (*precir, *compressed, *raw, *page1[1:2])
        },
        **{vector.name: vector.frame for vector in airframes},
    }
    for name, frame in retained.items():
        (VECTOR_DIR / name).write_bytes(frame)
    write_manifest(plid, precir, compressed, raw, airframes)
    write_tagtinker_orientation_source(airframes)


if __name__ == "__main__":
    main()

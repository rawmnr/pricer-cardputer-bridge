"""Generate retained PrecIR and PricehaxBT type-1327 vectors."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pc" / "src"))

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
    make_all_white_type_1327_image,
    make_pricehax_data_bodies,
)

BARCODE = "N4163114582613272"
PROFILE_REVISION = "T008D-r1"
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
    """Return the retained T008C control vectors under their historical names."""
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
    plid: PricerPlid, *, page: int = 2, wake_command: int = 0x97
) -> list[Vector]:
    encoded = make_all_white_type_1327_image()
    packets = make_pricehax_data_bodies(encoded)
    assert len(encoded.payload) <= 0xFFFF
    params_body = (
        len(encoded.payload).to_bytes(2, "big")
        + bytes((0, encoded.compression_type, page))
        + PRICEHAX_WIDTH.to_bytes(2, "big")
        + PRICEHAX_HEIGHT.to_bytes(2, "big")
        + bytes.fromhex("00000000000088000000000000")
    )
    wake_body = (
        bytes.fromhex("01000000" + "01" * 22)
        if wake_command == 0x17
        else bytes.fromhex("01000000" + "01" * 20)
    )
    definitions: list[tuple[str, int, bytes, int, bool]] = [
        (f"pricehax-wake-{wake_command:02x}.bin", wake_command, wake_body, 500, False),
        (f"pricehax-params-page{page}.bin", 0x05, params_body, 10, True),
    ]
    definitions.extend(
        (f"pricehax-data-{index:04d}.bin", 0x20, body, 3, True)
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


def write_manifest(
    plid: PricerPlid, precir: list[Vector], pricehax: list[Vector]
) -> None:
    encoded = make_all_white_type_1327_image()
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
        "profile_revision": PROFILE_REVISION,
        "transmission": {
            "wake_repeats": 400,
            "wake_repeat_gap_us": 2_000,
            "image_repeats": 1,
            "image_repeat_gap_us": 0,
        },
        "vectors": [
            {
                **vector_manifest(vector),
                "name": historical_name,
            }
            for historical_name, vector in zip(
                (
                    "wake.bin",
                    "params-8x8-color.bin",
                    "data-8x8-color.bin",
                    "refresh.bin",
                ),
                precir,
                strict=True,
            )
        ],
        "precir_control": {"vectors": [vector_manifest(vector) for vector in precir]},
        "pricehax_1327": {
            "upstream_commit": PRICEHAX_UPSTREAM_COMMIT,
            "image": {
                "description": "full-screen all-white, two planes",
                "width": PRICEHAX_WIDTH,
                "height": PRICEHAX_HEIGHT,
                "raw_bit_count": PRICEHAX_RAW_BITS,
                "raw_byte_count": PRICEHAX_RAW_BYTES,
                "encoded_unpadded_length": len(encoded.payload),
                "encoded_padded_length": len(encoded.padded_payload),
                "frame_count": len(encoded.padded_payload) // PRICEHAX_BYTES_PER_FRAME,
            },
            "vectors": [vector_manifest(vector) for vector in pricehax],
        },
    }
    (VECTOR_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


def array_definition(symbol: str, frame: bytes) -> str:
    return f"constexpr std::uint8_t {symbol}[] = {{\n{cpp_bytes(frame)}\n}};"


def write_orientation_source(
    precir: list[Vector], exact: list[Vector], wake17: list[Vector], page1: list[Vector]
) -> None:
    arrays = {
        "kPrecirWakeFrame": precir[0].frame,
        "kPrecirParamsFrame": precir[1].frame,
        "kPrecirDataFrame": precir[2].frame,
        "kPrecirRefreshFrame": precir[3].frame,
        "kPricehaxWake97Frame": exact[0].frame,
        "kPricehaxWake17Frame": wake17[0].frame,
        "kPricehaxParamsPage2Frame": exact[1].frame,
        "kPricehaxParamsPage1Frame": page1[1].frame,
        "kPricehaxDataFrame": exact[2].frame,
        "kPricehaxRefreshFrame": exact[-1].frame,
    }
    array_source = "\n\n".join(
        array_definition(symbol, frame) for symbol, frame in arrays.items()
    )
    source = f"""#include "orientation_test.hpp"

#include <Arduino.h>

#include "ir_transmitter.hpp"

// Generated by scripts/generate_vectors.py; do not edit the frame arrays manually.
namespace eslbridge {{
namespace {{

{array_source}

constexpr OrientationTestPlan kPrecirControlPlan = {{
    std::array<OrientationTestFrame, 5>{{{{
        {{kPrecirWakeFrame, sizeof(kPrecirWakeFrame), 400, 2'000, 0}},
        {{kPrecirParamsFrame, sizeof(kPrecirParamsFrame), 1, 0, 0}},
        {{kPrecirDataFrame, sizeof(kPrecirDataFrame), 1, 0, 0}},
        {{kPrecirRefreshFrame, sizeof(kPrecirRefreshFrame), 1, 0, 0}},
        {{}},
    }}}},
    4,
}};

#define PRICEHAX_PLAN(name, wake, params) \\
constexpr OrientationTestPlan name = {{ \\
    std::array<OrientationTestFrame, 5>{{{{ \\
        {{wake, sizeof(wake), 250, 2'000, 0}}, \\
        {{wake, sizeof(wake), 250, 2'000, 2'000}}, \\
        {{params, sizeof(params), 10, 2'000, 0}}, \\
        {{kPricehaxDataFrame, sizeof(kPricehaxDataFrame), 3, 2'000, 0}}, \\
        {{kPricehaxRefreshFrame, sizeof(kPricehaxRefreshFrame), 50, 2'000, 0}}, \\
    }}}}, \\
    5, \\
}}

PRICEHAX_PLAN(kPricehaxExactPlan, kPricehaxWake97Frame, kPricehaxParamsPage2Frame);
PRICEHAX_PLAN(kPricehaxWake17Plan, kPricehaxWake17Frame, kPricehaxParamsPage2Frame);
PRICEHAX_PLAN(kPricehaxPage1Plan, kPricehaxWake97Frame, kPricehaxParamsPage1Frame);

#undef PRICEHAX_PLAN
}}  // namespace

const OrientationTestPlan& orientation_test_plan(const OrientationTest test) {{
    switch (test) {{
        case OrientationTest::kOne:
            return kPrecirControlPlan;
        case OrientationTest::kTwo:
            return kPricehaxExactPlan;
        case OrientationTest::kThree:
            return kPricehaxWake17Plan;
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
            return "PRICEHAX_WAKE17";
        case OrientationTest::kFour:
            return "PRICEHAX_PAGE1";
        default:
            return "NONE";
    }}
}}

protocol::Status run_orientation_test(IrTransmitter& transmitter, const OrientationTest test) {{
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
    exact = make_pricehax_vectors(plid)
    wake17 = make_pricehax_vectors(plid, wake_command=0x17)
    page1 = make_pricehax_vectors(plid, page=1)

    VECTOR_DIR.mkdir(parents=True, exist_ok=True)
    _, _, historical_frames = make_vectors()
    retained = {
        **historical_frames,
        **{
            vector.name: vector.frame
            for vector in (*precir, *exact, *wake17[0:1], *page1[1:2])
        },
    }
    for name, frame in retained.items():
        (VECTOR_DIR / name).write_bytes(frame)
    write_manifest(plid, precir, exact)
    write_orientation_source(precir, exact, wake17, page1)


if __name__ == "__main__":
    main()

"""Clean-room PricehaxBT type-1327 image profile helpers.

The application framing and RLE behavior are derived from PricehaxBT commit
3043f964595f90fdb6835640275751277523f809. Physical compatibility with the
target ESL remains unverified.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final

PRICEHAX_UPSTREAM_COMMIT: Final[str] = "3043f964595f90fdb6835640275751277523f809"
PRICEHAX_TYPE_CODE: Final[int] = 1327
PRICEHAX_WIDTH: Final[int] = 208
PRICEHAX_HEIGHT: Final[int] = 112
PRICEHAX_PLANES: Final[int] = 2
PRICEHAX_RAW_BITS: Final[int] = PRICEHAX_WIDTH * PRICEHAX_HEIGHT * PRICEHAX_PLANES
PRICEHAX_RAW_BYTES: Final[int] = PRICEHAX_RAW_BITS // 8
PRICEHAX_BYTES_PER_FRAME: Final[int] = 40


class PricehaxProfileError(ValueError):
    """Raised when type-1327 image data does not satisfy the profile."""


@dataclass(frozen=True, slots=True)
class EncodedImage:
    """Unpadded Pricehax payload plus its 40-byte packet representation."""

    payload: bytes
    padded_payload: bytes
    compression_type: int


def _pack_bits(bits: Sequence[int]) -> bytes:
    if len(bits) % 8:
        raise PricehaxProfileError("encoded bit count must be byte-aligned")
    output = bytearray(len(bits) // 8)
    for index, bit in enumerate(bits):
        output[index // 8] |= bit << (7 - (index % 8))
    return bytes(output)


def encode_pricehax_rle(raw_bits: Sequence[int]) -> EncodedImage:
    """Encode two image planes with PricehaxBT's binary Elias-gamma RLE.

    The first bit stores the initial color. Each run length follows as an
    Elias-gamma integer. The encoded bytes are then zero-padded to complete
    40-byte data packets; the returned ``payload`` remains unpadded for the
    parameter-frame length field.
    """
    if len(raw_bits) != PRICEHAX_RAW_BITS:
        raise PricehaxProfileError(
            f"raw image must contain {PRICEHAX_RAW_BITS} bits, got {len(raw_bits)}"
        )
    if any(bit not in (0, 1) for bit in raw_bits):
        raise PricehaxProfileError("raw image bits must contain only 0 or 1")

    encoded_bits: list[int] = [raw_bits[0]]
    run_length = 1
    previous = raw_bits[0]
    for bit in raw_bits[1:]:
        if bit == previous:
            run_length += 1
            continue
        binary = f"{run_length:b}"
        encoded_bits.extend((0,) * (len(binary) - 1))
        encoded_bits.extend(int(value) for value in binary)
        previous = bit
        run_length = 1
    binary = f"{run_length:b}"
    encoded_bits.extend((0,) * (len(binary) - 1))
    encoded_bits.extend(int(value) for value in binary)

    encoded_bits.extend((0,) * (-len(encoded_bits) % 8))
    payload = _pack_bits(encoded_bits)
    padded_length = (
        (len(payload) + PRICEHAX_BYTES_PER_FRAME - 1) // PRICEHAX_BYTES_PER_FRAME
    ) * PRICEHAX_BYTES_PER_FRAME
    return EncodedImage(
        payload=payload,
        padded_payload=payload + bytes(padded_length - len(payload)),
        compression_type=2,
    )


def make_all_white_type_1327_image() -> EncodedImage:
    """Create a deterministic full-screen white image in both color planes."""
    return encode_pricehax_rle(bytes((1,)) * PRICEHAX_RAW_BITS)


def make_pricehax_data_bodies(encoded: EncodedImage) -> list[bytes]:
    """Packetize an encoded image into indexed 40-byte command bodies."""
    if len(encoded.padded_payload) == 0 or len(encoded.padded_payload) % PRICEHAX_BYTES_PER_FRAME:
        raise PricehaxProfileError("padded payload must contain complete 40-byte packets")
    return [
        index.to_bytes(2, "big")
        + encoded.padded_payload[offset : offset + PRICEHAX_BYTES_PER_FRAME]
        for index, offset in enumerate(
            range(0, len(encoded.padded_payload), PRICEHAX_BYTES_PER_FRAME)
        )
    ]

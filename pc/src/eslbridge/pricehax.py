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
    """Pricehax image bytes and their transport metadata."""

    payload: bytes
    padded_payload: bytes
    announced_length: int
    compression_type: int


def _validate_raw_bits(raw_bits: Sequence[int]) -> None:
    if len(raw_bits) != PRICEHAX_RAW_BITS:
        raise PricehaxProfileError(
            f"raw image must contain {PRICEHAX_RAW_BITS} bits, got {len(raw_bits)}"
        )
    if any(bit not in (0, 1) for bit in raw_bits):
        raise PricehaxProfileError("raw image bits must contain only 0 or 1")


def _pack_bits(bits: Sequence[int]) -> bytes:
    if len(bits) % 8:
        raise PricehaxProfileError("encoded bit count must be byte-aligned")
    output = bytearray(len(bits) // 8)
    for index, bit in enumerate(bits):
        output[index // 8] |= bit << (7 - (index % 8))
    return bytes(output)


def _pad_packets(payload: bytes) -> bytes:
    padded_length = (
        (len(payload) + PRICEHAX_BYTES_PER_FRAME - 1) // PRICEHAX_BYTES_PER_FRAME
    ) * PRICEHAX_BYTES_PER_FRAME
    return payload + bytes(padded_length - len(payload))


def encode_pricehax_rle(raw_bits: Sequence[int]) -> EncodedImage:
    """Transcribe PricehaxBT's published binary Elias-gamma RLE control flow.

    The upstream loop records the terminal run at ``m == j - 1``. This retains
    its historical all-one output ``80 00 B5 FF`` rather than correcting the
    apparent off-by-one. Compressed mode pads to 320-bit groups before assigning
    both ``datalen`` and ``padded_datalen``, so the announced length is padded.
    """
    _validate_raw_bits(raw_bits)

    run_lengths: list[int] = []
    last_index = len(raw_bits) - 1
    run_length = 1
    previous = raw_bits[0]
    for index in range(1, last_index + 1):
        bit = raw_bits[index]
        if bit == previous:
            run_length += 1
            if index == last_index - 1:
                run_lengths.append(run_length)
        else:
            run_lengths.append(run_length)
            run_length = 1
            if index == last_index - 1:
                run_lengths.append(1)
        previous = bit

    encoded_bits: list[int] = [raw_bits[0]]
    for length in run_lengths:
        binary = f"{length:b}"
        encoded_bits.extend((0,) * (len(binary) - 1))
        encoded_bits.extend(int(value) for value in binary)
    encoded_bits.extend((0,) * (-len(encoded_bits) % 8))

    payload = _pack_bits(encoded_bits)
    padded_payload = _pad_packets(payload)
    return EncodedImage(
        payload=payload,
        padded_payload=padded_payload,
        announced_length=len(padded_payload),
        compression_type=2,
    )


def encode_pricehax_raw(raw_bits: Sequence[int]) -> EncodedImage:
    """Pack an uncompressed image and pad only its transport packets."""
    _validate_raw_bits(raw_bits)
    payload = _pack_bits(raw_bits)
    return EncodedImage(
        payload=payload,
        padded_payload=_pad_packets(payload),
        announced_length=len(payload),
        compression_type=0,
    )


def make_all_white_type_1327_image() -> EncodedImage:
    """Create PricehaxBT-exact compressed full-screen white image data."""
    return encode_pricehax_rle(bytes((1,)) * PRICEHAX_RAW_BITS)


def make_all_white_type_1327_raw_image() -> EncodedImage:
    """Create uncompressed full-screen white image data in both planes."""
    return encode_pricehax_raw(bytes((1,)) * PRICEHAX_RAW_BITS)


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

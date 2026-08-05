"""Unit tests for PP16 symbol encoder and timing profiles."""

from __future__ import annotations

import pytest

from eslbridge.pp16 import (
    MAX_FRAME_BYTES,
    PRECIR_CARRIER_HZ,
    PRECIR_NIBBLE_GAPS_US,
    PRECIR_PROVENANCE,
    PP16EncoderError,
    PP16TimingProfile,
    SymbolTiming,
    calculate_frame_duration_us,
    encode_pp16_rmt_ticks,
    encode_pp16_symbols,
    precir_pp16_profile,
    provisional_pp16_profile,
)


def burst_starts(symbols: list[SymbolTiming]) -> list[int]:
    starts: list[int] = []
    elapsed = 0
    for symbol in symbols:
        starts.append(elapsed)
        elapsed += symbol.total_us
    return starts


def test_provisional_and_precir_profiles_are_marked_and_valid() -> None:
    profile = provisional_pp16_profile()
    assert profile.is_provisional is True
    assert profile.carrier_frequency_hz == PRECIR_CARRIER_HZ
    assert profile.symbol_burst_us == 21
    assert profile.duty_percent == 50
    assert PRECIR_PROVENANCE in profile.provenance
    profile.validate()

    precir = precir_pp16_profile()
    assert precir.symbol_burst_us == 21
    for n in range(16):
        assert precir.symbol_gap_us(n) == PRECIR_NIBBLE_GAPS_US[n]
        assert precir.symbol_timing(n).total_us == 21 + PRECIR_NIBBLE_GAPS_US[n]


def test_invalid_profile_carrier_and_duty() -> None:
    with pytest.raises(PP16EncoderError, match="carrier_frequency_hz"):
        PP16TimingProfile(carrier_frequency_hz=400_000).validate()
    with pytest.raises(PP16EncoderError, match="carrier_frequency_hz"):
        PP16TimingProfile(carrier_frequency_hz=2_500_000).validate()
    with pytest.raises(PP16EncoderError, match="duty_percent"):
        PP16TimingProfile(duty_percent=5).validate()
    with pytest.raises(PP16EncoderError, match="duty_percent"):
        PP16TimingProfile(duty_percent=70).validate()


def test_invalid_profile_nibble_gaps() -> None:
    with pytest.raises(PP16EncoderError, match="must contain exactly 16 values"):
        PP16TimingProfile(nibble_gaps_us=(27, 51, 35)).validate()

    bad_gaps = list(PRECIR_NIBBLE_GAPS_US)
    bad_gaps[0] = 0
    with pytest.raises(PP16EncoderError, match="nibble_gaps_us"):
        PP16TimingProfile(nibble_gaps_us=tuple(bad_gaps)).validate()


def test_nibble_gap_and_timing_mapping() -> None:
    profile = precir_pp16_profile()
    for n in range(16):
        expected_gap = PRECIR_NIBBLE_GAPS_US[n]
        assert profile.symbol_gap_us(n) == expected_gap
        assert profile.symbol_timing(n) == SymbolTiming(21, expected_gap)
        assert profile.symbol_timing(n).total_us == 21 + expected_gap

    with pytest.raises(PP16EncoderError, match="nibble -1 out of range"):
        profile.symbol_gap_us(-1)
    with pytest.raises(PP16EncoderError, match="nibble 16 out of range"):
        profile.symbol_gap_us(16)


@pytest.mark.parametrize(
    ("payload", "expected_starts"),
    [
        (b"\x00", [0, 48, 96]),
        (b"\x01", [0, 72, 120]),
        (b"\x12", [0, 56, 128]),
    ],
)
def test_golden_cumulative_burst_starts(payload: bytes, expected_starts: list[int]) -> None:
    symbols = encode_pp16_symbols(payload)
    assert burst_starts(symbols) == expected_starts
    assert len(symbols) == len(payload) * 2 + 1
    assert symbols[-1] == SymbolTiming(21, 0)


def test_encode_multiple_bytes_and_optional_preamble() -> None:
    profile = precir_pp16_profile()
    symbols = encode_pp16_symbols(b"\xa5\x0f", profile)
    assert len(symbols) == 5
    assert symbols[:4] == [
        profile.symbol_timing(5),
        profile.symbol_timing(10),
        profile.symbol_timing(15),
        profile.symbol_timing(0),
    ]
    assert symbols[-1] == SymbolTiming(21, 0)

    profile_pt = PP16TimingProfile(
        preamble_burst_us=500,
        preamble_gap_us=500,
    )
    symbols_pt = encode_pp16_symbols(b"\x12", profile_pt)
    assert symbols_pt == [
        SymbolTiming(500, 500),
        profile_pt.symbol_timing(2),
        profile_pt.symbol_timing(1),
        SymbolTiming(21, 0),
    ]


def test_calculate_frame_duration_us() -> None:
    profile = precir_pp16_profile()
    payload = b"\x00\xff"
    symbols = encode_pp16_symbols(payload, profile)
    assert calculate_frame_duration_us(payload, profile) == sum(s.total_us for s in symbols)


def test_invalid_payload_input_rejected() -> None:
    profile = precir_pp16_profile()
    with pytest.raises(PP16EncoderError, match="payload must not be empty"):
        encode_pp16_symbols(b"", profile)
    with pytest.raises(PP16EncoderError, match="byte value 256 out of range"):
        encode_pp16_symbols([256], profile)


def test_long_frame_capacity_boundary() -> None:
    profile = precir_pp16_profile()
    max_payload = b"\xaa" * MAX_FRAME_BYTES
    symbols = encode_pp16_symbols(max_payload, profile)
    assert len(symbols) == MAX_FRAME_BYTES * 2 + 1
    assert symbols[-1] == SymbolTiming(21, 0)
    assert calculate_frame_duration_us(max_payload, profile) == (
        MAX_FRAME_BYTES * 2 * (21 + PRECIR_NIBBLE_GAPS_US[10]) + 21
    )

    oversized_payload = b"\xaa" * (MAX_FRAME_BYTES + 1)
    with pytest.raises(PP16EncoderError, match="exceeds maximum allowed capacity"):
        encode_pp16_symbols(oversized_payload, profile)


def test_rmt_ticks_conversion() -> None:
    profile = precir_pp16_profile()
    ticks = encode_pp16_rmt_ticks(b"\x12", profile)
    symbols = encode_pp16_symbols(b"\x12", profile)
    assert len(ticks) == len(symbols)
    for (high_t, low_t), symbol in zip(ticks, symbols, strict=True):
        assert high_t == symbol.burst_us * 10
        assert low_t == symbol.gap_us * 10
    assert ticks[-1] == (210, 0)

    overflow_profile = PP16TimingProfile(preamble_burst_us=4000)
    with pytest.raises(PP16EncoderError, match="exceed max limit"):
        encode_pp16_rmt_ticks(b"\x00", overflow_profile)

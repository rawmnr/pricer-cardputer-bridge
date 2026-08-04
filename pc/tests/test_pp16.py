"""Unit tests for PP16 symbol encoder and timing profiles."""

from __future__ import annotations

import pytest

from eslbridge.pp16 import (
    MAX_FRAME_BYTES,
    PRECIR_CARRIER_HZ,
    PRECIR_NIBBLE_TOTAL_DURATIONS_US,
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
        assert precir.symbol_timing(n).total_us == PRECIR_NIBBLE_TOTAL_DURATIONS_US[n]


def test_invalid_profile_carrier_and_duty() -> None:
    with pytest.raises(PP16EncoderError, match="carrier_frequency_hz"):
        PP16TimingProfile(carrier_frequency_hz=400_000).validate()

    with pytest.raises(PP16EncoderError, match="carrier_frequency_hz"):
        PP16TimingProfile(carrier_frequency_hz=2_500_000).validate()

    with pytest.raises(PP16EncoderError, match="duty_percent"):
        PP16TimingProfile(duty_percent=5).validate()

    with pytest.raises(PP16EncoderError, match="duty_percent"):
        PP16TimingProfile(duty_percent=70).validate()


def test_invalid_profile_nibble_durations() -> None:
    with pytest.raises(PP16EncoderError, match="must contain exactly 16 values"):
        PP16TimingProfile(nibble_durations_us=(27, 51, 35)).validate()

    with pytest.raises(PP16EncoderError, match="invalid for burst"):
        # nibble total 20 us <= burst 21 us
        bad_durations = list(PRECIR_NIBBLE_TOTAL_DURATIONS_US)
        bad_durations[0] = 20
        PP16TimingProfile(nibble_durations_us=tuple(bad_durations)).validate()


def test_nibble_gap_and_timing_mapping() -> None:
    profile = precir_pp16_profile()
    for n in range(16):
        expected_total = PRECIR_NIBBLE_TOTAL_DURATIONS_US[n]
        expected_gap = expected_total - 21
        assert profile.symbol_gap_us(n) == expected_gap
        symbol = profile.symbol_timing(n)
        assert symbol == SymbolTiming(21, expected_gap)
        assert symbol.total_us == expected_total

    with pytest.raises(PP16EncoderError, match="nibble -1 out of range"):
        profile.symbol_gap_us(-1)

    with pytest.raises(PP16EncoderError, match="nibble 16 out of range"):
        profile.symbol_gap_us(16)


def test_encode_single_and_multiple_bytes() -> None:
    profile = precir_pp16_profile()

    # Payload 0x12 -> low nibble 2, high nibble 1 (no preamble/trailer by default)
    symbols = encode_pp16_symbols(b"\x12", profile)
    assert len(symbols) == 2
    assert symbols[0] == profile.symbol_timing(2)
    assert symbols[1] == profile.symbol_timing(1)

    # Payload 0xA5 0x0F -> (5, 10), (15, 0)
    symbols_multi = encode_pp16_symbols(b"\xa5\x0f", profile)
    assert len(symbols_multi) == 4
    assert symbols_multi[0] == profile.symbol_timing(5)
    assert symbols_multi[1] == profile.symbol_timing(10)
    assert symbols_multi[2] == profile.symbol_timing(15)
    assert symbols_multi[3] == profile.symbol_timing(0)

    profile_pt = PP16TimingProfile(
        preamble_burst_us=500,
        preamble_gap_us=500,
        trailer_burst_us=200,
        trailer_gap_us=500,
    )
    symbols_pt = encode_pp16_symbols(b"\x12", profile_pt)
    assert len(symbols_pt) == 4
    assert symbols_pt[0] == SymbolTiming(500, 500)
    assert symbols_pt[1] == profile_pt.symbol_timing(2)
    assert symbols_pt[2] == profile_pt.symbol_timing(1)
    assert symbols_pt[3] == SymbolTiming(200, 500)


def test_calculate_frame_duration_us() -> None:
    profile = precir_pp16_profile()
    payload = b"\x00\xff"
    symbols = encode_pp16_symbols(payload, profile)
    expected_total = sum(s.total_us for s in symbols)
    assert calculate_frame_duration_us(payload, profile) == expected_total


def test_invalid_payload_input_rejected() -> None:
    profile = precir_pp16_profile()

    with pytest.raises(PP16EncoderError, match="payload must not be empty"):
        encode_pp16_symbols(b"", profile)

    with pytest.raises(PP16EncoderError, match="byte value 256 out of range"):
        encode_pp16_symbols([256], profile)


def test_long_frame_capacity_boundary() -> None:
    profile = precir_pp16_profile()

    # Max capacity payload (256 bytes)
    max_payload = b"\xaa" * MAX_FRAME_BYTES
    symbols = encode_pp16_symbols(max_payload, profile)
    # (256 * 2) = 512 symbols
    assert len(symbols) == MAX_FRAME_BYTES * 2

    # Exceeding capacity payload (257 bytes)
    oversized_payload = b"\xaa" * (MAX_FRAME_BYTES + 1)
    with pytest.raises(PP16EncoderError, match="exceeds maximum allowed capacity"):
        encode_pp16_symbols(oversized_payload, profile)


def test_rmt_ticks_conversion() -> None:
    profile = precir_pp16_profile()
    ticks = encode_pp16_rmt_ticks(b"\x12", profile)
    symbols = encode_pp16_symbols(b"\x12", profile)

    assert len(ticks) == len(symbols)
    for (high_t, low_t), s in zip(ticks, symbols, strict=True):
        assert high_t == s.burst_us * 10
        assert low_t == s.gap_us * 10

    # Profile with excessive preamble duration causing RMT tick overflow (>32767)
    overflow_profile = PP16TimingProfile(preamble_burst_us=4000)
    with pytest.raises(PP16EncoderError, match="exceed max limit"):
        encode_pp16_rmt_ticks(b"\x00", overflow_profile)

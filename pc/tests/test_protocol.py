from __future__ import annotations

import random
import struct
import zlib

import pytest

from eslbridge.protocol import (
    MAX_PAYLOAD,
    Command,
    Message,
    ProtocolError,
    Status,
    decode_message,
    encode_message,
    expected_frame_size,
)


def test_round_trip() -> None:
    message = Message(
        command=Command.CARRIER_TEST,
        sequence=42,
        payload=b"abc",
        status=Status.OK,
    )
    assert decode_message(encode_message(message)) == message


def test_crc_corruption_is_rejected() -> None:
    frame = bytearray(encode_message(Message(Command.HELLO, sequence=1)))
    frame[8] ^= 0x01
    with pytest.raises(ProtocolError, match="CRC mismatch"):
        decode_message(bytes(frame))


def test_wrong_magic_is_rejected() -> None:
    frame = b"NOPE" + encode_message(Message(Command.HELLO, sequence=1))[4:]
    with pytest.raises(ProtocolError, match="bad magic"):
        decode_message(frame)


def test_oversized_payload_is_rejected() -> None:
    with pytest.raises(ProtocolError, match="payload exceeds"):
        encode_message(Message(Command.HELLO, sequence=1, payload=b"x" * (MAX_PAYLOAD + 1)))


def test_expected_frame_size() -> None:
    frame = encode_message(Message(Command.HELLO, sequence=1, payload=b"1234"))
    assert expected_frame_size(frame[:12]) == len(frame)


def test_encode_decode_round_trip_property() -> None:
    """Property-based round-trip invariants test across boundaries."""
    sequences = [0, 1, 127, 32767, 65535]
    flags_list = [0, 1, 127, 255]
    payloads = [
        b"",
        b"a",
        b"\x00\xff" * 4,
        b"x" * 4095,
        b"y" * MAX_PAYLOAD,
    ]

    for seq in sequences:
        for flag in flags_list:
            for payload in payloads:
                for cmd in Command:
                    for st in Status:
                        msg = Message(
                            command=cmd,
                            sequence=seq,
                            payload=payload,
                            status=st,
                            flags=flag,
                        )
                        encoded = encode_message(msg)
                        assert len(encoded) == 12 + len(payload) + 4
                        assert expected_frame_size(encoded[:12]) == len(encoded)
                        decoded = decode_message(encoded)
                        assert decoded == msg

    # Fixed-seed pseudo-random fuzzing
    rng = random.Random(1337)
    all_cmds = list(Command)
    all_st = list(Status)
    for _ in range(100):
        msg = Message(
            command=rng.choice(all_cmds),
            sequence=rng.randint(0, 0xFFFF),
            payload=bytes(rng.randint(0, 255) for _ in range(rng.randint(0, MAX_PAYLOAD))),
            status=rng.choice(all_st),
            flags=rng.randint(0, 0xFF),
        )
        assert decode_message(encode_message(msg)) == msg


def test_one_bit_corruption_rejection_property() -> None:
    """Exhaustive single-bit corruption rejection test."""
    rng = random.Random(42)
    sample_messages = [
        Message(Command.HELLO, sequence=1, payload=b""),
        Message(Command.SEND_PRICER_FRAME, sequence=65535, payload=b"test payload", flags=0xFF),
        Message(
            Command.GET_STATUS, sequence=100, payload=bytes(rng.randint(0, 255) for _ in range(128))
        ),
    ]

    for msg in sample_messages:
        encoded = encode_message(msg)
        for byte_idx in range(len(encoded)):
            for bit in range(8):
                corrupted = bytearray(encoded)
                corrupted[byte_idx] ^= 1 << bit
                with pytest.raises(ProtocolError):
                    decode_message(bytes(corrupted))


def test_malformed_length_version_status_command_handling() -> None:
    """Test rejection of malformed lengths, versions, commands, and statuses."""
    # Version != 1
    msg = Message(Command.HELLO, sequence=1)
    encoded = bytearray(encode_message(msg))
    encoded[4] = 2  # Set version to 2
    # Recalculate CRC so CRC passes, testing version check specifically
    crc = zlib.crc32(encoded[4:-4]) & 0xFFFFFFFF
    struct.pack_into("<I", encoded, len(encoded) - 4, crc)
    with pytest.raises(ProtocolError, match="unsupported protocol version"):
        decode_message(bytes(encoded))

    # Oversized payload header
    header_oversized = b"ESLI\x01\x01\x00\x00\x01\x00\x01\x10"  # payload length 4097 (0x1001)
    with pytest.raises(ProtocolError, match="payload length exceeds"):
        expected_frame_size(header_oversized)

    # Short frame
    with pytest.raises(ProtocolError, match="shorter than the fixed header"):
        decode_message(b"ESLI123")

    # Frame length mismatch
    frame = encode_message(Message(Command.HELLO, sequence=1))
    with pytest.raises(ProtocolError, match="frame length mismatch"):
        decode_message(frame + b"extra")

    # Unknown command
    encoded_cmd = bytearray(encode_message(msg))
    encoded_cmd[5] = 0xFF
    crc = zlib.crc32(encoded_cmd[4:-4]) & 0xFFFFFFFF
    struct.pack_into("<I", encoded_cmd, len(encoded_cmd) - 4, crc)
    with pytest.raises(ProtocolError, match="unknown command"):
        decode_message(bytes(encoded_cmd))

    # Unknown status
    encoded_st = bytearray(encode_message(msg))
    encoded_st[7] = 0xFF
    crc = zlib.crc32(encoded_st[4:-4]) & 0xFFFFFFFF
    struct.pack_into("<I", encoded_st, len(encoded_st) - 4, crc)
    with pytest.raises(ProtocolError, match="unknown status"):
        decode_message(bytes(encoded_st))

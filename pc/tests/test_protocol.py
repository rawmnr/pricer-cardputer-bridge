from __future__ import annotations

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

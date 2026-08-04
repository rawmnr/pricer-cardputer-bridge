from __future__ import annotations

import struct
from dataclasses import dataclass, field

import pytest

from eslbridge.models import HelloInfo
from eslbridge.protocol import (
    Command,
    CrcMismatchError,
    Message,
    Status,
    decode_message,
    encode_message,
)
from eslbridge.transport import (
    AccessDeniedError,
    BridgeTransport,
    CrcResponseError,
    DeviceStatusError,
    InvalidDeviceError,
    MissingPortError,
    MultiplePortsError,
    ResponseTimeoutError,
    discover_bridge,
)


@dataclass
class FakeSerial:
    response_factory: object
    incoming: bytearray = field(default_factory=bytearray)
    outgoing: bytearray = field(default_factory=bytearray)
    closed: bool = False

    @property
    def in_waiting(self) -> int:
        return len(self.incoming)

    def read(self, size: int = 1) -> bytes:
        data = bytes(self.incoming[:size])
        del self.incoming[:size]
        return data

    def write(self, data: bytes) -> int:
        self.outgoing.extend(data)
        request = decode_message(data)
        payload = (
            bytes([1, 0, 1, 0])
            + (9).to_bytes(4, "little")
            + (4096).to_bytes(2, "little")
            + bytes([44, 0])
        )
        self.incoming.extend(
            encode_message(
                Message(
                    command=request.command,
                    sequence=request.sequence,
                    payload=payload,
                    status=Status.OK,
                )
            )
        )
        return len(data)

    def flush(self) -> None:
        return None

    def reset_input_buffer(self) -> None:
        self.incoming.clear()

    def close(self) -> None:
        self.closed = True


class FakeClock:
    def __init__(self, start: float = 100.0) -> None:
        self.now = start

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += max(0.0, seconds)


@dataclass
class ConfigurableFakeSerial:
    response_bytes: bytes = field(default_factory=bytes)
    chunk_sizes: list[int] | None = None
    read_delay_s: float = 0.0
    clock: FakeClock | None = None
    closed: bool = False
    outgoing: bytearray = field(default_factory=bytearray)

    @property
    def in_waiting(self) -> int:
        return len(self.response_bytes)

    def read(self, size: int = 1) -> bytes:
        if self.clock and self.read_delay_s:
            self.clock.sleep(self.read_delay_s)
        if not self.response_bytes:
            return b""
        if self.chunk_sizes:
            chunk_size = self.chunk_sizes.pop(0) if self.chunk_sizes else size
            take = min(chunk_size, len(self.response_bytes))
        else:
            take = min(size, len(self.response_bytes))
        data = self.response_bytes[:take]
        self.response_bytes = self.response_bytes[take:]
        return data

    def write(self, data: bytes) -> int:
        self.outgoing.extend(data)
        return len(data)

    def flush(self) -> None:
        pass

    def reset_input_buffer(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True


def make_valid_hello_payload(
    protocol: int = 1,
    firmware: tuple[int, int, int] = (0, 1, 0),
    capabilities: int = 0x09,
    max_payload: int = 4096,
    ir_gpio: int = 44,
    reserved: int = 0,
) -> bytes:
    return struct.pack(
        "<BBBBIHBB",
        protocol,
        firmware[0],
        firmware[1],
        firmware[2],
        capabilities,
        max_payload,
        ir_gpio,
        reserved,
    )


def make_hello_frame(
    sequence: int = 1,
    payload: bytes | None = None,
    status: Status = Status.OK,
    corrupt_crc: bool = False,
) -> bytes:
    if payload is None:
        payload = make_valid_hello_payload()
    msg = Message(command=Command.HELLO, sequence=sequence, payload=payload, status=status)
    frame = encode_message(msg)
    if corrupt_crc:
        frame = frame[:-1] + bytes([frame[-1] ^ 0xFF])
    return frame


def test_request_matches_sequence_and_decodes_hello() -> None:
    serial = FakeSerial(object())
    transport = BridgeTransport(serial_port=serial, timeout_s=0.1)
    response = transport.request(Command.HELLO)
    info = HelloInfo.decode(response.payload)
    assert info.ir_gpio == 44
    assert decode_message(bytes(serial.outgoing)).command is Command.HELLO


def test_discover_bridge_explicit_port_success() -> None:
    clock = FakeClock()
    frame = make_hello_frame(sequence=1)
    serial = ConfigurableFakeSerial(response_bytes=frame, clock=clock)

    def opener(_port: str, timeout_s: float) -> BridgeTransport:
        return BridgeTransport(
            serial_port=serial,
            timeout_s=timeout_s,
            clock=clock.time,
        )

    with discover_bridge(
        port="COM5",
        timeout_s=3.0,
        clock=clock.time,
        sleep=clock.sleep,
        opener=opener,
    ) as bridge:
        assert bridge.port == "COM5"
        assert bridge.hello.ir_gpio == 44
        assert bridge.hello.max_payload == 4096

    assert serial.closed is True


def test_discover_bridge_auto_discovery_reenumeration_success() -> None:
    clock = FakeClock()
    enum_calls = 0

    def port_enumerator() -> list[str]:
        nonlocal enum_calls
        enum_calls += 1
        return [] if enum_calls == 1 else ["COM3"]

    frame = make_hello_frame(sequence=1)
    serial = ConfigurableFakeSerial(response_bytes=frame, clock=clock)

    def opener(_port: str, timeout_s: float) -> BridgeTransport:
        return BridgeTransport(
            serial_port=serial,
            timeout_s=timeout_s,
            clock=clock.time,
        )

    with discover_bridge(
        port=None,
        timeout_s=3.0,
        clock=clock.time,
        sleep=clock.sleep,
        port_enumerator=port_enumerator,
        opener=opener,
        retry_interval_s=0.1,
    ) as bridge:
        assert bridge.port == "COM3"
        assert bridge.hello.ir_gpio == 44

    assert enum_calls == 2
    assert serial.closed is True


def test_discover_bridge_fragmented_response() -> None:
    clock = FakeClock()
    frame = make_hello_frame(sequence=1)
    serial = ConfigurableFakeSerial(response_bytes=frame, chunk_sizes=[2, 5, 3, 100], clock=clock)

    def opener(_port: str, timeout_s: float) -> BridgeTransport:
        return BridgeTransport(
            serial_port=serial,
            timeout_s=timeout_s,
            clock=clock.time,
        )

    with discover_bridge(
        port="COM3",
        timeout_s=3.0,
        clock=clock.time,
        sleep=clock.sleep,
        opener=opener,
    ) as bridge:
        assert bridge.hello.ir_gpio == 44
        assert bridge.hello.capabilities == 0x09


def test_discover_bridge_multiple_port_ambiguity() -> None:
    clock = FakeClock()

    def enumerator() -> list[str]:
        return ["COM1", "COM2"]

    with pytest.raises(MultiplePortsError) as exc_info:
        discover_bridge(
            port=None,
            timeout_s=3.0,
            clock=clock.time,
            sleep=clock.sleep,
            port_enumerator=enumerator,
        )

    assert "COM1, COM2" in str(exc_info.value)
    assert "--port" in str(exc_info.value)


def test_discover_bridge_missing_port_deadline() -> None:
    clock = FakeClock()

    def enumerator() -> list[str]:
        return []

    with pytest.raises(MissingPortError) as exc_info:
        discover_bridge(
            port=None,
            timeout_s=1.0,
            clock=clock.time,
            sleep=clock.sleep,
            port_enumerator=enumerator,
            retry_interval_s=0.2,
        )

    assert clock.now >= 101.0
    assert "No serial ports found" in str(exc_info.value)


def test_discover_bridge_access_denied() -> None:
    clock = FakeClock()

    def failing_opener(port: str, timeout_s: float) -> BridgeTransport:
        raise AccessDeniedError(f"Access is denied to {port}")

    with pytest.raises(AccessDeniedError) as exc_info:
        discover_bridge(
            port="COM3",
            timeout_s=3.0,
            clock=clock.time,
            sleep=clock.sleep,
            opener=failing_opener,
        )

    assert "Access is denied" in str(exc_info.value)


def test_discover_bridge_response_timeout_closes_transport() -> None:
    clock = FakeClock()
    serial = ConfigurableFakeSerial(response_bytes=b"", read_delay_s=0.5, clock=clock)

    def opener(_port: str, timeout_s: float) -> BridgeTransport:
        return BridgeTransport(
            serial_port=serial,
            timeout_s=timeout_s,
            clock=clock.time,
        )

    with pytest.raises(ResponseTimeoutError):
        discover_bridge(
            port="COM3",
            timeout_s=1.0,
            clock=clock.time,
            sleep=clock.sleep,
            opener=opener,
            retry_interval_s=0.2,
        )

    assert serial.closed is True


def test_discover_bridge_crc_mismatch_closes_transport() -> None:
    clock = FakeClock()
    bad_crc_frame = make_hello_frame(sequence=1, corrupt_crc=True)
    serial = ConfigurableFakeSerial(response_bytes=bad_crc_frame, clock=clock)

    def opener(_port: str, timeout_s: float) -> BridgeTransport:
        return BridgeTransport(
            serial_port=serial,
            timeout_s=timeout_s,
            clock=clock.time,
        )

    with pytest.raises(CrcResponseError):
        discover_bridge(
            port="COM3",
            timeout_s=3.0,
            clock=clock.time,
            sleep=clock.sleep,
            opener=opener,
        )

    assert serial.closed is True


def test_discover_bridge_wrong_hello_identity_closes_transport() -> None:
    clock = FakeClock()
    bad_payload = make_valid_hello_payload(protocol=2)
    frame = make_hello_frame(sequence=1, payload=bad_payload)
    serial = ConfigurableFakeSerial(response_bytes=frame, clock=clock)

    def opener(_port: str, timeout_s: float) -> BridgeTransport:
        return BridgeTransport(
            serial_port=serial,
            timeout_s=timeout_s,
            clock=clock.time,
        )

    with pytest.raises(InvalidDeviceError) as exc_info:
        discover_bridge(
            port="COM3",
            timeout_s=3.0,
            clock=clock.time,
            sleep=clock.sleep,
            opener=opener,
        )

    assert "unsupported protocol version 2" in str(exc_info.value)
    assert serial.closed is True


def test_discover_bridge_non_ok_device_status_closes_transport() -> None:
    clock = FakeClock()
    frame = make_hello_frame(sequence=1, status=Status.UNSUPPORTED_COMMAND)
    serial = ConfigurableFakeSerial(response_bytes=frame, clock=clock)

    def opener(_port: str, timeout_s: float) -> BridgeTransport:
        return BridgeTransport(
            serial_port=serial,
            timeout_s=timeout_s,
            clock=clock.time,
        )

    with pytest.raises(DeviceStatusError) as exc_info:
        discover_bridge(
            port="COM3",
            timeout_s=3.0,
            clock=clock.time,
            sleep=clock.sleep,
            opener=opener,
        )

    assert exc_info.value.status == Status.UNSUPPORTED_COMMAND
    assert serial.closed is True


def test_transport_fragmentation() -> None:
    """Verify host transport reassembles fragmented frames across small chunks."""
    clock = FakeClock()
    msg = Message(Command.GET_STATUS, sequence=1, payload=b"fragmented payload")
    frame = encode_message(msg)
    # Deliver in 1-byte, 2-byte, 5-byte chunks
    serial = ConfigurableFakeSerial(
        response_bytes=frame, chunk_sizes=[1, 2, 5, 3, 100], clock=clock
    )
    transport = BridgeTransport(serial_port=serial, timeout_s=5.0, clock=clock.time)
    res = transport._read_frame()
    assert res == msg


def test_transport_concatenation() -> None:
    """Verify host transport retains concatenated frames without dropping bytes."""
    clock = FakeClock()
    msg1 = Message(Command.HELLO, sequence=1, payload=b"first")
    msg2 = Message(Command.GET_STATUS, sequence=2, payload=b"second")
    msg3 = Message(Command.CARRIER_TEST, sequence=3, payload=b"third")
    concatenated = encode_message(msg1) + encode_message(msg2) + encode_message(msg3)

    serial = ConfigurableFakeSerial(response_bytes=concatenated, clock=clock)
    transport = BridgeTransport(serial_port=serial, timeout_s=5.0, clock=clock.time)

    r1 = transport._read_frame()
    assert r1 == msg1
    r2 = transport._read_frame()
    assert r2 == msg2
    r3 = transport._read_frame()
    assert r3 == msg3
    assert len(transport._recv_buffer) == 0


def test_transport_noisy_prefixes() -> None:
    """Verify host transport trims arbitrary noise and partial magic prefixes."""
    clock = FakeClock()
    msg = Message(Command.HELLO, sequence=10)
    valid_frame = encode_message(msg)

    noise_cases = [
        b"GARBAGE_NOISE_BYTES" + valid_frame,
        b"E" + valid_frame,
        b"ES" + valid_frame,
        b"ESL" + valid_frame,
        b"ESLX_NOT_MAGIC" + valid_frame,
        b"ESLESLI" + valid_frame[4:],  # Partial magic false start followed by real magic
    ]

    for noise in noise_cases:
        serial = ConfigurableFakeSerial(response_bytes=noise, clock=clock)
        transport = BridgeTransport(serial_port=serial, timeout_s=5.0, clock=clock.time)
        assert transport._read_frame() == msg


def test_transport_oversized_header() -> None:
    """Verify oversized header (payload_length > 4096) is immediately rejected without waiting."""
    clock = FakeClock()
    msg_valid = Message(Command.HELLO, sequence=99)
    valid_frame = encode_message(msg_valid)

    # Oversized header: MAGIC + header with payload length 5000 (0x1388)
    oversized_header = b"ESLI\x01\x01\x00\x00\x01\x00\x88\x13"
    stream = oversized_header + valid_frame

    serial = ConfigurableFakeSerial(response_bytes=stream, clock=clock)
    transport = BridgeTransport(serial_port=serial, timeout_s=5.0, clock=clock.time)

    # Should drop oversized header and return valid frame immediately
    res = transport._read_frame()
    assert res == msg_valid


def test_transport_timeout_cleanup() -> None:
    """Verify host transport clears partial state on timeout."""
    clock = FakeClock()
    # Partial frame (magic + 4 bytes header) without enough data to complete
    partial = b"ESLI\x01\x01\x00\x00"

    serial = ConfigurableFakeSerial(response_bytes=partial, read_delay_s=6.0, clock=clock)
    transport = BridgeTransport(serial_port=serial, timeout_s=5.0, clock=clock.time)

    with pytest.raises(ResponseTimeoutError):
        transport._read_frame()

    assert len(transport._recv_buffer) == 0

    # Subsequent call with complete frame succeeds
    valid_msg = Message(Command.HELLO, sequence=5)
    serial.response_bytes = encode_message(valid_msg)
    assert transport._read_frame() == valid_msg


def test_transport_recovery_after_errors() -> None:
    """Verify host transport recovers after noise, CRC error, oversized header, and timeout."""
    clock = FakeClock()
    serial = ConfigurableFakeSerial(clock=clock)
    transport = BridgeTransport(serial_port=serial, timeout_s=5.0, clock=clock.time)

    # 1. Noise recovery
    valid1 = Message(Command.HELLO, sequence=1)
    serial.response_bytes = b"NOISE" + encode_message(valid1)
    assert transport._read_frame() == valid1

    # 2. CRC error recovery
    bad_crc_frame = bytearray(encode_message(Message(Command.HELLO, sequence=2)))
    bad_crc_frame[-1] ^= 0xFF
    valid2 = Message(Command.GET_STATUS, sequence=3)
    serial.response_bytes = bytes(bad_crc_frame) + encode_message(valid2)

    with pytest.raises(CrcMismatchError):
        transport._read_frame()

    # Next frame in buffer or subsequent call succeeds
    assert transport._read_frame() == valid2

    # 3. Oversized header recovery
    oversized = b"ESLI\x01\x01\x00\x00\x01\x00\x00\x20"  # length 8192
    valid3 = Message(Command.CARRIER_TEST, sequence=4)
    serial.response_bytes = oversized + encode_message(valid3)
    assert transport._read_frame() == valid3

    # 4. Timeout recovery
    serial.response_bytes = b"ESLI\x01"
    serial.read_delay_s = 6.0
    with pytest.raises(ResponseTimeoutError):
        transport._read_frame()

    assert len(transport._recv_buffer) == 0
    serial.read_delay_s = 0.0
    valid4 = Message(Command.SEND_PRICER_FRAME, sequence=5, payload=b"ok")
    serial.response_bytes = encode_message(valid4)
    assert transport._read_frame() == valid4


def test_transport_read_size_capped() -> None:
    """Verify serial reads are capped at MAX_FRAME_SIZE (4112)."""

    class SizeCheckingSerial(ConfigurableFakeSerial):
        def read(self, size: int = 1) -> bytes:
            assert size <= 4112, f"read size {size} exceeds max frame size 4112"
            return super().read(size)

    clock = FakeClock()
    msg = Message(Command.HELLO, sequence=1)
    serial = SizeCheckingSerial(response_bytes=encode_message(msg), clock=clock)
    # Set in_waiting to 10000 bytes
    serial.response_bytes = encode_message(msg) + b"X" * 10000
    transport = BridgeTransport(serial_port=serial, timeout_s=5.0, clock=clock.time)
    assert transport._read_frame() == msg

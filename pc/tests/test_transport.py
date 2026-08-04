from __future__ import annotations

import struct
from dataclasses import dataclass, field

import pytest

from eslbridge.models import HelloInfo
from eslbridge.protocol import Command, Message, Status, decode_message, encode_message
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

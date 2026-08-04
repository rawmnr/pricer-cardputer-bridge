"""Serial transport for the Cardputer bridge."""

from __future__ import annotations

import itertools
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, cast

from .protocol import MAGIC, Command, Message, ProtocolError, Status, decode_message, encode_message


class SerialLike(Protocol):
    @property
    def in_waiting(self) -> int: ...

    def read(self, size: int = 1) -> bytes: ...

    def write(self, data: bytes) -> int: ...

    def flush(self) -> None: ...

    def reset_input_buffer(self) -> None: ...

    def close(self) -> None: ...


@dataclass(slots=True)
class BridgeTransport:
    serial_port: SerialLike
    timeout_s: float = 3.0
    _sequences: itertools.count = field(default_factory=lambda: itertools.count(1), init=False)
    clock: Callable[[], float] = time.monotonic

    @classmethod
    def open(cls, port: str, timeout_s: float = 3.0) -> BridgeTransport:
        try:
            import serial

            connection = cast(
                SerialLike,
                serial.Serial(port=port, baudrate=115200, timeout=0.05, write_timeout=1.0),
            )
        except ImportError as exc:
            raise RuntimeError("pyserial is required for real serial connections") from exc
        except serial.SerialException as exc:
            raise ConnectionError(f"cannot open {port}: {exc}") from exc
        connection.reset_input_buffer()
        return cls(connection, timeout_s=timeout_s)

    def close(self) -> None:
        self.serial_port.close()

    def __enter__(self) -> BridgeTransport:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def request(self, command: Command, payload: bytes = b"") -> Message:
        sequence = next(self._sequences) & 0xFFFF
        request = encode_message(Message(command=command, sequence=sequence, payload=payload))
        written = self.serial_port.write(request)
        if written != len(request):
            raise ConnectionError(f"short serial write: {written}/{len(request)} bytes")
        self.serial_port.flush()

        response = self._read_frame()
        if response.sequence != sequence:
            raise ProtocolError(
                f"sequence mismatch: expected {sequence}, received {response.sequence}"
            )
        if response.command != command:
            raise ProtocolError(
                f"command mismatch: expected {command.name}, received {response.command.name}"
            )
        if response.status is not Status.OK:
            raise RuntimeError(f"device rejected {command.name}: {response.status.name}")
        return response

    def _read_frame(self) -> Message:
        deadline = self.clock() + self.timeout_s
        buffer = bytearray()
        expected_size: int | None = None

        while self.clock() < deadline:
            chunk = self.serial_port.read(max(1, self.serial_port.in_waiting))
            if not chunk:
                continue
            buffer.extend(chunk)

            magic_index = buffer.find(MAGIC)
            if magic_index < 0:
                if len(buffer) > len(MAGIC):
                    del buffer[: -len(MAGIC) + 1]
                continue
            if magic_index > 0:
                del buffer[:magic_index]

            if expected_size is None and len(buffer) >= 12:
                payload_length = int.from_bytes(buffer[10:12], "little")
                expected_size = 12 + payload_length + 4
            if expected_size is not None and len(buffer) >= expected_size:
                return decode_message(bytes(buffer[:expected_size]))

        raise TimeoutError(f"no complete bridge response within {self.timeout_s:.1f}s")


def candidate_ports() -> list[str]:
    """Return available Windows/serial ports without claiming device identity."""
    try:
        from serial.tools import list_ports
    except ImportError as exc:
        raise RuntimeError("pyserial is required to enumerate serial ports") from exc
    return [port.device for port in list_ports.comports()]

"""Serial transport for the Cardputer bridge."""

from __future__ import annotations

import itertools
import struct
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, cast

from .models import HelloInfo
from .protocol import (
    MAGIC,
    MAX_FRAME_SIZE,
    MAX_PAYLOAD,
    Command,
    CrcMismatchError,
    Message,
    ProtocolError,
    Status,
    decode_message,
    encode_message,
)


class BridgeError(Exception):
    """Base exception for all Cardputer bridge transport and discovery errors."""


class MissingPortError(BridgeError):
    """Raised when no serial ports are found or specified port is missing."""


class MultiplePortsError(BridgeError):
    """Raised when multiple candidate serial ports are found without explicit port."""


class AccessDeniedError(BridgeError):
    """Raised when opening a serial port fails due to access/permission denied."""


class ResponseTimeoutError(BridgeError, TimeoutError):
    """Raised when waiting for a bridge response times out."""


class InvalidDeviceError(BridgeError):
    """Raised when a probed serial port is not a valid Cardputer bridge."""


class CrcResponseError(BridgeError, CrcMismatchError):
    """Raised when a response frame fails CRC verification."""


class DeviceStatusError(BridgeError):
    """Raised when the bridge device returns a non-OK status."""

    def __init__(self, command: Command, status: Status, message: str | None = None) -> None:
        self.command = command
        self.status = status
        super().__init__(message or f"device rejected {command.name}: {status.name}")


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
    _recv_buffer: bytearray = field(default_factory=bytearray, init=False)
    clock: Callable[[], float] = time.monotonic

    @classmethod
    def open(
        cls,
        port: str,
        timeout_s: float = 3.0,
        *,
        serial_factory: Callable[[str], SerialLike] | None = None,
    ) -> BridgeTransport:
        try:
            if serial_factory is not None:
                connection = serial_factory(port)
            else:
                import serial

                connection = cast(
                    SerialLike,
                    serial.Serial(port=port, baudrate=115200, timeout=0.05, write_timeout=1.0),
                )
        except ImportError as exc:
            raise RuntimeError("pyserial is required for real serial connections") from exc
        except PermissionError as exc:
            raise AccessDeniedError(f"access denied opening {port}: {exc}") from exc
        except Exception as exc:
            msg = str(exc)
            if (
                "Access is denied" in msg
                or "PermissionError" in msg
                or "permission denied" in msg.lower()
            ):
                raise AccessDeniedError(f"access denied opening {port}: {exc}") from exc
            raise MissingPortError(f"cannot open {port}: {exc}") from exc

        try:
            connection.reset_input_buffer()
        except Exception:
            connection.close()
            raise

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
        try:
            written = self.serial_port.write(request)
        except PermissionError as exc:
            raise AccessDeniedError(f"access denied writing to serial port: {exc}") from exc
        except Exception as exc:
            msg = str(exc)
            if (
                "Access is denied" in msg
                or "PermissionError" in msg
                or "permission denied" in msg.lower()
            ):
                raise AccessDeniedError(f"access denied writing to serial port: {exc}") from exc
            raise

        if written != len(request):
            raise MissingPortError(f"short serial write: {written}/{len(request)} bytes")
        self.serial_port.flush()

        try:
            response = self._read_frame()
        except TimeoutError as exc:
            raise ResponseTimeoutError(
                f"no complete bridge response within {self.timeout_s:.1f}s"
            ) from exc
        except CrcMismatchError as exc:
            raise CrcResponseError(f"CRC mismatch in response from device: {exc}") from exc

        if response.sequence != sequence:
            raise ProtocolError(
                f"sequence mismatch: expected {sequence}, received {response.sequence}"
            )
        if response.command != command:
            raise ProtocolError(
                f"command mismatch: expected {command.name}, received {response.command.name}"
            )
        if response.status is not Status.OK:
            raise DeviceStatusError(command, response.status)
        return response

    def _trim_noise(self) -> None:
        idx = self._recv_buffer.find(MAGIC)
        if idx >= 0:
            if idx > 0:
                del self._recv_buffer[:idx]
            return
        for prefix_len in (3, 2, 1):
            prefix = MAGIC[:prefix_len]
            if self._recv_buffer.endswith(prefix):
                del self._recv_buffer[:-prefix_len]
                return
        self._recv_buffer.clear()

    def _read_frame(self) -> Message:
        deadline = self.clock() + self.timeout_s
        try:
            while True:
                self._trim_noise()
                if len(self._recv_buffer) >= 12:
                    payload_length = struct.unpack_from("<H", self._recv_buffer, 10)[0]
                    if payload_length > MAX_PAYLOAD:
                        del self._recv_buffer[:1]
                        continue
                    expected_size = 12 + payload_length + 4
                    if len(self._recv_buffer) >= expected_size:
                        frame_bytes = bytes(self._recv_buffer[:expected_size])
                        del self._recv_buffer[:expected_size]
                        return decode_message(frame_bytes)

                if self.clock() >= deadline:
                    self._recv_buffer.clear()
                    raise ResponseTimeoutError(
                        f"no complete bridge response within {self.timeout_s:.1f}s"
                    )

                in_waiting = getattr(self.serial_port, "in_waiting", 0)
                to_read = min(max(1, in_waiting), MAX_FRAME_SIZE)
                chunk = self.serial_port.read(to_read)
                if chunk:
                    self._recv_buffer.extend(chunk)
        except ResponseTimeoutError:
            self._recv_buffer.clear()
            raise
        except TimeoutError as exc:
            self._recv_buffer.clear()
            raise ResponseTimeoutError(
                f"no complete bridge response within {self.timeout_s:.1f}s"
            ) from exc


def candidate_ports() -> list[str]:
    """Return available Windows/serial ports without claiming device identity."""
    try:
        from serial.tools import list_ports
    except ImportError as exc:
        raise RuntimeError("pyserial is required to enumerate serial ports") from exc
    return [port.device for port in list_ports.comports()]


@dataclass(slots=True)
class DiscoveredBridge:
    port: str
    transport: BridgeTransport
    hello: HelloInfo

    def close(self) -> None:
        self.transport.close()

    def __enter__(self) -> DiscoveredBridge:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def discover_bridge(
    port: str | None = None,
    timeout_s: float = 3.0,
    *,
    port_enumerator: Callable[[], list[str]] = candidate_ports,
    opener: Callable[[str, float], BridgeTransport] = BridgeTransport.open,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    retry_interval_s: float = 0.1,
) -> DiscoveredBridge:
    deadline = clock() + timeout_s

    if port is not None:
        last_exception: Exception | None = None
        while True:
            now = clock()
            if now >= deadline:
                if last_exception is not None:
                    if isinstance(last_exception, BridgeError):
                        raise last_exception
                    raise ResponseTimeoutError(
                        f"Timed out probing bridge on port {port}"
                    ) from last_exception
                raise ResponseTimeoutError(f"Timed out probing bridge on port {port}")

            remaining = max(0.05, deadline - clock())
            try:
                transport = opener(port, remaining)
            except (AccessDeniedError, MultiplePortsError):
                raise
            except Exception as exc:
                last_exception = exc
                if clock() + retry_interval_s >= deadline:
                    raise MissingPortError(
                        f"Port {port} not found or failed to open: {exc}"
                    ) from exc
                sleep(min(retry_interval_s, max(0.0, deadline - clock())))
                continue

            try:
                response = transport.request(Command.HELLO)
                hello_info = HelloInfo.decode(response.payload)
                hello_info.validate_identity(port=port)
                return DiscoveredBridge(port=port, transport=transport, hello=hello_info)
            except (InvalidDeviceError, CrcResponseError, DeviceStatusError, AccessDeniedError):
                transport.close()
                raise
            except ResponseTimeoutError as exc:
                transport.close()
                last_exception = exc
                if clock() + retry_interval_s >= deadline:
                    raise ResponseTimeoutError(f"Timed out probing bridge on port {port}") from exc
                sleep(min(retry_interval_s, max(0.0, deadline - clock())))
            except Exception:
                transport.close()
                raise

    last_exception = None
    while True:
        now = clock()
        if now >= deadline:
            if last_exception is not None:
                if isinstance(last_exception, BridgeError):
                    raise last_exception
                raise ResponseTimeoutError(
                    "Timed out auto-discovering Cardputer bridge"
                ) from last_exception
            raise MissingPortError("No serial ports found within timeout period.")

        ports = port_enumerator()
        if len(ports) == 0:
            remaining_sleep = min(retry_interval_s, max(0.0, deadline - clock()))
            if remaining_sleep > 0:
                sleep(remaining_sleep)
            continue

        if len(ports) > 1:
            candidates_str = ", ".join(sorted(ports))
            raise MultiplePortsError(
                f"Multiple candidate serial ports found: {candidates_str}. "
                "Please specify one explicitly using --port."
            )

        cand = ports[0]
        remaining = max(0.05, deadline - clock())
        try:
            transport = opener(cand, remaining)
        except AccessDeniedError:
            raise
        except Exception as exc:
            last_exception = exc
            if clock() + retry_interval_s >= deadline:
                raise MissingPortError(f"Could not open candidate port {cand}: {exc}") from exc
            sleep(min(retry_interval_s, max(0.0, deadline - clock())))
            continue

        try:
            response = transport.request(Command.HELLO)
            hello_info = HelloInfo.decode(response.payload)
            hello_info.validate_identity(port=cand)
            return DiscoveredBridge(port=cand, transport=transport, hello=hello_info)
        except (InvalidDeviceError, CrcResponseError, DeviceStatusError, AccessDeniedError):
            transport.close()
            raise
        except ResponseTimeoutError as exc:
            transport.close()
            last_exception = exc
            if clock() + retry_interval_s >= deadline:
                raise ResponseTimeoutError(f"Timed out probing candidate port {cand}") from exc
            sleep(min(retry_interval_s, max(0.0, deadline - clock())))
        except Exception:
            transport.close()
            raise

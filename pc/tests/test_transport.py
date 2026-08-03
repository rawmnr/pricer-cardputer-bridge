from __future__ import annotations

from dataclasses import dataclass, field

from eslbridge.models import HelloInfo
from eslbridge.protocol import Command, Message, Status, decode_message, encode_message
from eslbridge.transport import BridgeTransport


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
        payload = bytes([1, 0, 1, 0]) + (9).to_bytes(4, "little") + (4096).to_bytes(2, "little") + bytes([44, 0])
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


def test_request_matches_sequence_and_decodes_hello() -> None:
    serial = FakeSerial(object())
    transport = BridgeTransport(serial_port=serial, timeout_s=0.1)
    response = transport.request(Command.HELLO)
    info = HelloInfo.decode(response.payload)
    assert info.ir_gpio == 44
    assert decode_message(bytes(serial.outgoing)).command is Command.HELLO

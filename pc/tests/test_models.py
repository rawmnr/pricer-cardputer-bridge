from __future__ import annotations

import pytest

from eslbridge.models import CarrierTestRequest, HelloInfo
from eslbridge.protocol import ProtocolError


def test_carrier_request_is_12_bytes() -> None:
    assert len(CarrierTestRequest().encode()) == 12


@pytest.mark.parametrize(
    "carrier_request",
    [
        CarrierTestRequest(duration_us=0),
        CarrierTestRequest(duration_us=5001),
        CarrierTestRequest(frequency_hz=100_000),
        CarrierTestRequest(duty_percent=100),
    ],
)
def test_unsafe_carrier_request_is_rejected(carrier_request: CarrierTestRequest) -> None:
    with pytest.raises(ProtocolError):
        carrier_request.encode()


def test_hello_decode() -> None:
    payload = (
        bytes([1, 0, 1, 0])
        + (9).to_bytes(4, "little")
        + (4096).to_bytes(2, "little")
        + bytes([44, 0])
    )
    info = HelloInfo.decode(payload)
    assert info.firmware_version == (0, 1, 0)
    assert info.ir_gpio == 44

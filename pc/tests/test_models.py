from __future__ import annotations

import pytest

from eslbridge.models import CarrierTestRequest, HelloInfo
from eslbridge.protocol import ProtocolError
from eslbridge.transport import InvalidDeviceError


def test_carrier_request_is_12_bytes() -> None:
    encoded = CarrierTestRequest().encode()
    assert len(encoded) == 12
    assert encoded[9:12] == b"\x00\x00\x00"


@pytest.mark.parametrize(
    "carrier_request",
    [
        CarrierTestRequest(frequency_hz=499_999),
        CarrierTestRequest(frequency_hz=2_000_001),
        CarrierTestRequest(duration_us=0),
        CarrierTestRequest(duration_us=5001),
        CarrierTestRequest(duty_percent=9),
        CarrierTestRequest(duty_percent=61),
    ],
)
def test_unsafe_carrier_request_is_rejected(carrier_request: CarrierTestRequest) -> None:
    with pytest.raises(ProtocolError):
        carrier_request.encode()


def test_carrier_request_accepted_min_max_boundaries() -> None:
    min_req = CarrierTestRequest(frequency_hz=500_000, duration_us=1, duty_percent=10)
    encoded_min = min_req.encode()
    assert len(encoded_min) == 12
    assert encoded_min[9:12] == b"\x00\x00\x00"

    max_req = CarrierTestRequest(frequency_hz=2_000_000, duration_us=5000, duty_percent=60)
    encoded_max = max_req.encode()
    assert len(encoded_max) == 12
    assert encoded_max[9:12] == b"\x00\x00\x00"


def test_hello_decode_and_identity_valid() -> None:
    payload = (
        bytes([1, 0, 1, 0])
        + (9).to_bytes(4, "little")
        + (4096).to_bytes(2, "little")
        + bytes([44, 0])
    )
    info = HelloInfo.decode(payload)
    assert info.firmware_version == (0, 1, 0)
    assert info.ir_gpio == 44
    assert info.reserved == 0
    valid, reason = info.is_valid_identity()
    assert valid is True
    assert reason == ""
    info.validate_identity(port="COM3")


def test_hello_identity_valid_with_future_capability_bits() -> None:
    info = HelloInfo(
        protocol_version=1,
        firmware_version=(0, 2, 0),
        capabilities=0x0D,  # bits 0 and 3 set plus bit 2
        max_payload=4096,
        ir_gpio=44,
        reserved=0,
    )
    valid, _ = info.is_valid_identity()
    assert valid is True
    info.validate_identity()


@pytest.mark.parametrize(
    "invalid_info",
    [
        HelloInfo(2, (0, 1, 0), 0x09, 4096, 44, 0),  # wrong protocol version
        HelloInfo(1, (0, 1, 0), 0x09, 2048, 44, 0),  # wrong max payload
        HelloInfo(1, (0, 1, 0), 0x09, 4096, 15, 0),  # wrong IR GPIO
        HelloInfo(1, (0, 1, 0), 0x09, 4096, 44, 1),  # non-zero reserved
        HelloInfo(1, (0, 1, 0), 0x01, 4096, 44, 0),  # missing bit 3 capability
        HelloInfo(1, (0, 1, 0), 0x08, 4096, 44, 0),  # missing bit 0 capability
    ],
)
def test_hello_invalid_identity_raises_invalid_device_error(invalid_info: HelloInfo) -> None:
    valid, reason = invalid_info.is_valid_identity()
    assert valid is False
    assert len(reason) > 0
    with pytest.raises(InvalidDeviceError) as exc_info:
        invalid_info.validate_identity(port="COM7")
    assert "COM7" in str(exc_info.value)

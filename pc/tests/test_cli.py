from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from eslbridge.cli import app
from eslbridge.models import HelloInfo
from eslbridge.transport import (
    DiscoveredBridge,
    MissingPortError,
    MultiplePortsError,
)

runner = CliRunner()


class FakeTransport:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def __enter__(self) -> FakeTransport:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def request(self, command: object, payload: bytes = b"") -> object:
        return None


def test_cli_probe_autodiscovery_uses_reported_port() -> None:
    hello = HelloInfo(
        protocol_version=1,
        firmware_version=(0, 1, 0),
        capabilities=0x09,
        max_payload=4096,
        ir_gpio=44,
        reserved=0,
    )
    fake_transport = FakeTransport()
    fake_discovered = DiscoveredBridge(port="COM3", transport=fake_transport, hello=hello)  # type: ignore[arg-type]

    with patch("eslbridge.cli.discover_bridge", return_value=fake_discovered) as mock_discover:
        result = runner.invoke(app, ["probe"])
        assert result.exit_code == 0
        assert "COM3" in result.stdout
        mock_discover.assert_called_once_with(port=None, timeout_s=3.0)
        assert fake_transport.closed is True


def test_cli_probe_explicit_port() -> None:
    hello = HelloInfo(
        protocol_version=1,
        firmware_version=(0, 1, 0),
        capabilities=0x09,
        max_payload=4096,
        ir_gpio=44,
        reserved=0,
    )
    fake_transport = FakeTransport()
    fake_discovered = DiscoveredBridge(port="COM7", transport=fake_transport, hello=hello)  # type: ignore[arg-type]

    with patch("eslbridge.cli.discover_bridge", return_value=fake_discovered) as mock_discover:
        result = runner.invoke(app, ["probe", "--port", "COM7"])
        assert result.exit_code == 0
        assert "COM7" in result.stdout
        mock_discover.assert_called_once_with(port="COM7", timeout_s=3.0)
        assert fake_transport.closed is True


def test_cli_probe_missing_port_error_exits_code_2() -> None:
    with patch(
        "eslbridge.cli.discover_bridge",
        side_effect=MissingPortError("No serial ports found."),
    ):
        result = runner.invoke(app, ["probe"])
        assert result.exit_code == 2
        assert "No serial ports found" in result.stdout


def test_cli_probe_multiple_ports_error_exits_code_2() -> None:
    with patch(
        "eslbridge.cli.discover_bridge",
        side_effect=MultiplePortsError(
            "Multiple candidate serial ports found: COM1, COM2. "
            "Please specify one explicitly using --port."
        ),
    ):
        result = runner.invoke(app, ["probe"])
        assert result.exit_code == 2
        assert "Multiple candidate serial ports found" in result.stdout
        assert "--port" in result.stdout


def test_cli_carrier_test_requires_explicit_port() -> None:
    result = runner.invoke(app, ["carrier-test"])
    assert result.exit_code != 0


def test_cli_send_frame_requires_explicit_port() -> None:
    result = runner.invoke(app, ["send-frame", "nonexistent.bin"])
    assert result.exit_code != 0


def test_cli_send_frame_success_logs_metadata(tmp_path: Path) -> None:
    frame_file = tmp_path / "frame.bin"
    frame_file.write_bytes(b"\x12\x34\x56\x78")

    fake_transport = FakeTransport()
    fake_transport.request = lambda cmd, payload: None  # type: ignore[attr-defined]

    with patch("eslbridge.cli.BridgeTransport.open", return_value=fake_transport):
        result = runner.invoke(
            app,
            [
                "send-frame",
                str(frame_file),
                "--port",
                "COM5",
                "--modulation",
                "16",
                "--repeats",
                "2",
                "--inter-repeat-gap-us",
                "1000",
            ],
        )
        assert result.exit_code == 0
        assert "Raw Pricer frame transmitted locally" in result.stdout
        assert "modulation=PP16" in result.stdout
        assert "length=4 bytes" in result.stdout
        assert "repeats=2" in result.stdout
        assert "gap=1000 us" in result.stdout
        assert "This does not prove that the ESL received the signal." in result.stdout

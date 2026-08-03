"""Command-line interface for the Cardputer bridge."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .models import CarrierTestRequest, HelloInfo
from .protocol import Command
from .transport import BridgeTransport, candidate_ports

app = typer.Typer(no_args_is_help=True, help="Control a Cardputer-Adv Pricer ESL bridge.")
console = Console()

PortOption = Annotated[str, typer.Option("--port", help="Windows COM port, for example COM7")]
TimeoutOption = Annotated[
    float, typer.Option("--timeout", min=0.1, max=30.0, help="Response timeout in seconds")
]


@app.command()
def ports() -> None:
    """List serial ports visible to Windows."""
    found = candidate_ports()
    if not found:
        console.print("No serial ports found.")
        raise typer.Exit(code=1)
    for port in found:
        console.print(port)


@app.command()
def probe(port: PortOption, timeout: TimeoutOption = 3.0) -> None:
    """Perform a HELLO round trip and print bridge capabilities."""
    try:
        with BridgeTransport.open(port, timeout_s=timeout) as bridge:
            response = bridge.request(Command.HELLO)
        info = HelloInfo.decode(response.payload)
    except Exception as exc:
        console.print(f"[red]Probe failed:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    table = Table(title=f"Cardputer bridge on {port}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Protocol", str(info.protocol_version))
    table.add_row("Firmware", ".".join(map(str, info.firmware_version)))
    table.add_row("Capabilities", f"0x{info.capabilities:08X}")
    table.add_row("Max payload", str(info.max_payload))
    table.add_row("IR GPIO", str(info.ir_gpio))
    console.print(table)


@app.command("carrier-test")
def carrier_test(
    port: PortOption,
    frequency_hz: Annotated[
        int, typer.Option("--frequency-hz", min=500_000, max=2_000_000)
    ] = 1_245_000,
    duration_us: Annotated[int, typer.Option("--duration-us", min=1, max=5_000)] = 2_000,
    duty_percent: Annotated[int, typer.Option("--duty-percent", min=10, max=60)] = 50,
    timeout: TimeoutOption = 3.0,
) -> None:
    """Request one bounded carrier burst; this is not a PP16 transmission."""
    request = CarrierTestRequest(frequency_hz, duration_us, duty_percent)
    try:
        with BridgeTransport.open(port, timeout_s=timeout) as bridge:
            bridge.request(Command.CARRIER_TEST, request.encode())
    except Exception as exc:
        console.print(f"[red]Carrier test failed:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    console.print(
        f"[green]Carrier test completed locally:[/green] {frequency_hz} Hz, "
        f"{duration_us} us, {duty_percent}% duty."
    )
    console.print("This does not prove that the ESL received the signal.")


if __name__ == "__main__":
    app()

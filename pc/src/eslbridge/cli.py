"""Command-line interface for the Cardputer bridge."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .models import CarrierTestRequest, PricerFrameRequest
from .protocol import Command
from .transport import BridgeError, BridgeTransport, candidate_ports, discover_bridge

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
def probe(
    port: Annotated[
        str | None, typer.Option("--port", help="Windows COM port, for example COM7")
    ] = None,
    timeout: TimeoutOption = 3.0,
) -> None:
    """Perform a HELLO round trip and print bridge capabilities."""
    try:
        with discover_bridge(port=port, timeout_s=timeout) as discovered:
            info = discovered.hello
            actual_port = discovered.port
    except BridgeError as exc:
        console.print(f"[red]Probe failed:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    except Exception as exc:
        console.print(f"[red]Probe failed:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    table = Table(title=f"Cardputer bridge on {actual_port}")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Protocol", str(info.protocol_version))
    table.add_row("Firmware", ".".join(map(str, info.firmware_version)))
    table.add_row("Git SHA", info.git_sha)
    table.add_row("Build provenance", info.build_provenance)
    table.add_row("PP16 profile", info.pp16_profile_revision)
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


@app.command("send-frame")
def send_frame(
    frame_path: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            help="Path to raw binary Pricer frame file",
        ),
    ],
    port: PortOption,
    modulation: Annotated[
        int, typer.Option("--modulation", help="Modulation scheme (4 for PP4, 16 for PP16)")
    ] = 16,
    repeats: Annotated[
        int, typer.Option("--repeats", min=1, max=100, help="Number of frame repetitions")
    ] = 1,
    inter_repeat_gap_us: Annotated[
        int,
        typer.Option(
            "--inter-repeat-gap-us",
            min=0,
            max=1_000_000,
            help="Gap between repetitions in microseconds",
        ),
    ] = 0,
    timeout: TimeoutOption = 3.0,
) -> None:
    """Send a raw Pricer frame over IR using the specified modulation."""
    try:
        frame_bytes = frame_path.read_bytes()
        request = PricerFrameRequest(
            frame=frame_bytes,
            modulation=modulation,
            repeats=repeats,
            inter_repeat_gap_us=inter_repeat_gap_us,
        )
        with BridgeTransport.open(port, timeout_s=timeout) as bridge:
            bridge.request(Command.SEND_PRICER_FRAME, request.encode())
    except Exception as exc:
        console.print(f"[red]Send frame failed:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    console.print(
        f"[green]Raw Pricer frame transmitted locally:[/green] modulation=PP{modulation}, "
        f"length={len(frame_bytes)} bytes, repeats={repeats}, gap={inter_repeat_gap_us} us."
    )
    console.print("This does not prove that the ESL received the signal.")


if __name__ == "__main__":
    app()

# Pricer Cardputer Bridge

Experimental USB-to-infrared bridge that uses an **M5Stack Cardputer-Adv** as the IR transmitter for Pricer electronic shelf labels (ESLs), with a **Windows host** performing image preparation and Pricer frame generation.

> **Status:** research scaffold. USB framing and a bounded carrier-test path are scaffolded; PP16 encoding and validated ESL image transfer are not implemented yet.

## Goal

```text
Windows host (MSI Claw 8 AI+)
  image/template + Pricer framing
              |
              | USB CDC
              v
M5Stack Cardputer-Adv
  framed command parser + ESP32-S3 RMT
              |
              | IR, target carrier ~1.245 MHz
              v
Pricer SmartTAG ESL
```

The first target is the photographed Pricer SmartTAG HD M+ Red unit, provisionally treated as a 208 x 112 black/white/red tag. That model identification and all protocol timings remain hypotheses until verified on hardware.

## Why this split

The Windows application owns the fast-changing and testable logic: image conversion, addressing, compression, CRCs, Pricer command assembly, logging, and later Home Assistant integration. The Cardputer firmware stays small and deterministic: receive a bounded command, generate a precisely timed waveform, return structured status.

## Repository layout

```text
firmware/        PlatformIO firmware for Cardputer-Adv
pc/              Python 3.12+ Windows host package managed with uv
docs/            architecture, protocol, hardware notes, ADRs, task briefs
scripts/         PowerShell bootstrap and verification scripts
.github/         CI, pull-request template, issue templates
AGENTS.md        operating contract for Codex-style coding agents
```

## Hardware assumptions

Verified from M5Stack documentation:

- Cardputer-Adv uses a Stamp-S3A / ESP32-S3FN8.
- The built-in IR transmitter is connected to **GPIO 44**.
- Native USB CDC is enabled with `ARDUINO_USB_CDC_ON_BOOT=1` and `ARDUINO_USB_MODE=1`.
- The official PlatformIO baseline uses `esp32-s3-devkitc-1` and `espressif32@6.7.0`.

Project hypotheses requiring bench validation:

- Pricer carrier frequency near 1.245 MHz.
- PP16 symbol timings and frame preamble.
- Sufficient optical output from the built-in Cardputer IR LED at short range.
- Target tag geometry, color planes, addressing, and wake-up behavior.

See [`docs/hardware-notes.md`](docs/hardware-notes.md) and [`docs/research-log.md`](docs/research-log.md).

## Safety constraints

- The firmware hard-limits carrier tests to **5 ms** per command.
- No continuous-carrier command is permitted.
- Start at 1-2 cm from the ESL receiver and avoid direct sunlight.
- Do not remove the ESL batteries or open the enclosure during the protocol-first phase.
- Do not connect 5 V logic directly to ESP32 or ESL test pads.

## Windows quick start

Prerequisites:

- Git
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PlatformIO Core (`pipx install platformio` or the VS Code extension)

```powershell
# From the repository root
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1

# Run host tests
uv run --project .\pc pytest

# Build firmware
pio run -d .\firmware

# Upload, then inspect the USB serial port
pio run -d .\firmware -t upload
pio device list

# Probe the bridge
uv run --project .\pc eslbridge probe --port COM7

# Bounded optical smoke test: 2 ms at 1.245 MHz
uv run --project .\pc eslbridge carrier-test --port COM7 --duration-us 2000
```

The carrier test proves only that the firmware accepted and attempted the request. A phone camera may show IR emission, but it cannot validate carrier frequency or timing. A logic analyzer or photodiode measurement remains the proper validation method.

## Host protocol

The host/device protocol is versioned, CRC-protected, little-endian, and independent of Pricer PP4/PP16 details. See [`docs/protocol.md`](docs/protocol.md).

Implemented scaffold commands:

- `HELLO`: firmware identity and capabilities.
- `GET_STATUS`: last command and transmitter status.
- `CARRIER_TEST`: bounded burst for optical smoke tests.
- `SEND_PRICER_FRAME`: reserved; returns `NOT_IMPLEMENTED` until the PP16 encoder is validated.

## Development sequence

1. Compile and flash the Cardputer firmware.
2. Validate USB CDC framing and CRC behavior.
3. Validate GPIO 44 carrier bursts at ~1.245 MHz.
4. Implement PP16 waveform generation from independently verified timings.
5. Add a clean host adapter around Pricer frame generation.
6. Transfer a monochrome test pattern, then a red/black/white pattern.
7. Add templates, image pipeline, and Home Assistant/MQTT integration.

The agent-ready backlog is in [`docs/backlog.md`](docs/backlog.md).

## PrecIR and licensing

[PrecIR](https://github.com/furrtek/PrecIR) is essential prior art and is licensed GPL-3.0. This repository is therefore GPL-3.0-only. PrecIR is **not vendored** in this scaffold. Any copied or adapted code must retain attribution, license notices, and a precise provenance record in [`THIRD_PARTY.md`](THIRD_PARTY.md).

Do not paste protocol implementation from unrelated repositories without checking its license and recording provenance.

## Legal and ethical scope

This project is intended for personally owned or legitimately acquired ESL hardware and interoperability research. Do not use it to modify labels deployed in stores or equipment you do not own or have explicit permission to test.

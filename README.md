# Pricer Cardputer Bridge

Experimental USB-to-infrared bridge that uses an **M5Stack Cardputer-Adv** as the IR transmitter for Pricer electronic shelf labels (ESLs), with a **Windows host** performing image preparation and Pricer frame generation.

> **Status:** research implementation. USB framing, bounded carrier-test, provisional PP4/PP16 symbol encoding, and bounded raw-frame transmission are implemented and tested in software. Physical carrier accuracy, optical emission, PP4/PP16 timing on this Cardputer, and validated ESL image transfer remain unverified.

## Goal

```text
Windows host (MSI Claw 8 AI+)
  image/template + Pricer framing
              |
              | USB CDC
              v
M5Stack Cardputer-Adv application
  framed command parser + ESP32-S3 RMT
              |
              | IR, target carrier ~1.245 MHz
              v
Pricer SmartTAG ESL
```

The first target is the photographed Pricer SmartTAG HD M+ Red unit, provisionally treated as a 208 x 112 black/white/red tag. That model identification and all protocol timings remain hypotheses until verified on hardware.

## Deployment model: keep M5Launcher installed

**M5Launcher is the primary deployment path.** The project is built as a normal ESP32-S3 application binary, then installed and launched by M5Launcher. Routine development must not erase the full flash or replace the Launcher installation.

```text
PlatformIO / GitHub Actions
        |
        | application-only .bin
        v
M5Launcher on Cardputer-Adv
  SD install or WebUI OTA upload
        |
        v
Pricer Cardputer Bridge application
```

M5Launcher can install normal application binaries produced by Arduino, PlatformIO, or ESP-IDF into an application partition. It remains resident and can boot the selected installed application. See [`docs/m5launcher-deployment.md`](docs/m5launcher-deployment.md).

The expected development artifact is:

```text
firmware/.pio/build/m5stack-cardputer-adv/firmware.bin
```

For distribution, rename it to an explicit application filename such as:

```text
pricer-cardputer-bridge-cardputer-adv-<version-or-sha>.bin
```

Use the application-only `firmware.bin`. Do not distribute a full flash dump or a merged image containing a bootloader and partition table unless a future task explicitly requires and documents that format.

## Cardputer keyboard orientation tests

The running application includes a local, PC-free minimal ESL test sequence.
After aligning the built-in IR emitter with the target, press one of the
number keys:

| Key | Action |
|---|---|
| `1` | `PRECIR_CONTROL`: retained T008C wake `0x17`, page 1, partial 8 × 8 image |
| `2` | `PRICEHAX_EXACT`: upstream-exact compressed type-1327 profile, wake `0x97`, page 2 |
| `3` | `PRICEHAX_RAW`: uncompressed full-screen 208 × 112 diagnostic profile |
| `4` | `PRICEHAX_PAGE1`: key 2 with page 1 |

The Pricehax plans split the 500-repeat wake into two bounded 250-repeat
transmissions separated by the same 2 ms repeat gap. Parameters repeat 10
times, each 40-byte data frame repeats 3 times, and refresh repeats 50 times.
The compressed profile reproduces the pinned upstream terminal-run behavior,
announces its padded 40-byte group, and sends one packet. The raw profile
announces 5,824 bytes and pads transport to 5,840 bytes across 146 packets.
All four tests remain finite and do not enable continuous carrier output.
Local completion does not prove IR emission or ESL compatibility; record the
selected profile, distance, alignment, ambient light, and visible response.

## Why this split

The Windows application owns the fast-changing and testable logic: image conversion, addressing, compression, CRCs, Pricer command assembly, logging, and later Home Assistant integration. The Cardputer firmware stays small and deterministic: receive a bounded command, generate a precisely timed waveform, return structured status.

## Repository layout

```text
firmware/        PlatformIO firmware for Cardputer-Adv
pc/              Python 3.12+ Windows host package managed with uv
docs/            architecture, deployment, protocol, hardware notes, ADRs, tasks
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

## Safety and flash-layout constraints

- The firmware hard-limits carrier tests to **5 ms** per command.
- No continuous-carrier command is permitted.
- Start at 1-2 cm from the ESL receiver and avoid direct sunlight.
- Do not remove the ESL batteries or open the enclosure during the protocol-first phase.
- Do not connect 5 V logic directly to ESP32 or ESL test pads.
- Do not erase the complete Cardputer flash during routine development.
- Do not rewrite the partition table, OTA metadata, or Launcher-owned partitions from application code.
- Do not erase all NVS; use a project-specific namespace such as `eslbridge` if persistence is added.

## Windows quick start

Prerequisites:

- Git
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- PlatformIO Core (`pipx install platformio` or the VS Code extension)
- M5Launcher already installed on the Cardputer-Adv

```powershell
# From the repository root
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1

# Run host tests
uv run --project .\pc pytest

# Build the application-only binary
pio run -d .\firmware

# Locate the M5Launcher-compatible application binary
Get-Item .\firmware\.pio\build\m5stack-cardputer-adv\firmware.bin
```

Install the `.bin` with either:

1. **M5Launcher SD browser:** copy the file to the microSD card, open `SD`, select the binary, and install it.
2. **M5Launcher WebUI:** start `WUI`, upload the binary from Windows, then install it through OTA.

After launching the bridge application, Windows may remove and recreate the USB CDC COM port. Discover the new port before probing:

```powershell
pio device list
uv run --project .\pc eslbridge probe --port COM7

# Bounded optical smoke test: 2 ms at 1.245 MHz
uv run --project .\pc eslbridge carrier-test --port COM7 --duration-us 2000
```

For normal development, **do not use** `pio run -d .\firmware -t upload`. Direct bootloader flashing is reserved for explicit recovery or low-level debugging tasks. If the Launcher installation is damaged, restore it with M5Burner using the Cardputer-Adv download-mode procedure documented by M5Stack.

The carrier test proves only that the firmware accepted and attempted the request. A phone camera may show IR emission, but it cannot validate carrier frequency or timing. A logic analyzer or photodiode measurement remains the proper validation method.

## CI artifacts

The firmware CI job builds `firmware.bin`, verifies that it is a non-empty ESP application image, renames it with the commit SHA, and uploads it as a GitHub Actions artifact. The artifact is intended for M5Launcher installation, not full-flash programming.

Tagged GitHub Release automation is intentionally deferred until version injection and a real M5Launcher install/return cycle are validated.

## Host protocol

The host/device protocol is versioned, CRC-protected, little-endian, and independent of Pricer PP4/PP16 details. See [`docs/protocol.md`](docs/protocol.md).

- `HELLO`: firmware identity and capabilities.
- `GET_STATUS`: last command and transmitter status.
- `CARRIER_TEST`: bounded burst for optical smoke tests.
- `SEND_PRICER_FRAME`: raw PP4 and PP16 frame transmission via RMT; PP4 uses the TagTinker raw-symbol mapping and remains physically unvalidated.

## Development sequence

1. Make the Windows/Python and PlatformIO toolchains reproducible.
2. Produce and validate an application-only M5Launcher artifact.
3. Install, boot, and return to M5Launcher without full-device reflashing.
4. Validate USB CDC framing and COM-port reconnection behavior.
5. Validate GPIO 44 carrier bursts at ~1.245 MHz.
6. Implement PP16 waveform generation from independently verified timings.
7. Add a clean host adapter around Pricer frame generation.
8. Transfer a monochrome test pattern, then a red/black/white pattern.
9. Add templates, image pipeline, and Home Assistant/MQTT integration.

The agent-ready backlog is in [`docs/backlog.md`](docs/backlog.md).

## PrecIR and licensing

[PrecIR](https://github.com/furrtek/PrecIR) is essential prior art and is licensed GPL-3.0. This repository is therefore GPL-3.0-only. PrecIR is **not vendored** in this scaffold. Any copied or adapted code must retain attribution, license notices, and a precise provenance record in [`THIRD_PARTY.md`](THIRD_PARTY.md).

Do not paste protocol implementation from unrelated repositories without checking its license and recording provenance.

## Legal and ethical scope

This project is intended for personally owned or legitimately acquired ESL hardware and interoperability research. Do not use it to modify labels deployed in stores or equipment you do not own or have explicit permission to test.

# Bench record: T001A M5Launcher deployment and USB handoff

- Date/time: 2026-08-04; exact local time not recorded
- Operator: repository owner, assisted remotely
- Repository commit: `7848574ac0b8b5d4fd260945c6bdec5a8df2bc97` plus uncommitted working-tree fixes represented by the artifact hash below
- Firmware version: `0.1.0`
- Host package version: `0.1.0`
- Cardputer hardware: M5Stack Cardputer-Adv, SKU K132-Adv; exact board revision not recorded
- M5Launcher version: `2.6.9`
- ESL markings/identifier: not applicable; no ESL transmission attempted
- Power state/battery notes: USB connected; battery state not recorded

## Objective

Verify that the application-only bridge binary can be installed and launched through M5Launcher, enumerates a usable USB CDC port on Windows, answers a real `HELLO` probe, and still permits returning to M5Launcher.

## Equipment

- M5Stack Cardputer-Adv, SKU K132-Adv, with M5Launcher 2.6.9
- Windows 11 MSI Claw 8 AI+ host
- USB-C data cable
- Cardputer microSD exposed to Windows as FAT32 volume `CARDPUTER`

## Setup

- Install route: M5Launcher SD browser
- Application filename: `pricer-cardputer-bridge-cardputer-adv-hwcdc.bin`
- Application size: 469,024 bytes
- Application SHA-256: `71127BC866F235F7D4B432336E8847F6053548BF52BEE71EB2268DF55FAE3D91`
- ESP image first byte: `0xE9`
- COM port before application launch: none observed while the SD transfer volume was exposed
- COM port after application launch: `COM3`
- Distance: not applicable
- Alignment: not applicable
- Ambient light: not recorded
- Measurement point: Windows USB/PnP enumeration and host bridge protocol
- Instrument settings: not applicable

## Command/input

```text
uv tool run --from platformio pio run -d firmware
uv run --project pc eslbridge probe --port COM3
```

USB feedback loop inspected `System.IO.Ports.SerialPort.GetPortNames()` and Windows PnP entities matching `USB\\VID_303A*`.

## Expected result

- The application boots from M5Launcher without a full-flash erase.
- Windows enumerates the ESP32-S3 USB composite device and a CDC COM port.
- `eslbridge probe` receives a valid protocol-v1 `HELLO` response.
- Rebooting or exiting the application leaves M5Launcher available.

## Observed result

- M5Launcher installed and launched the application-only binary.
- The Cardputer displayed `Pricer ESL Bridge`, `USB: waiting`, `IR GPIO: 44`, and `PP16: pending`.
- Windows enumerated `COM3` and three healthy PnP nodes: the USB composite parent, CDC interface `MI_00`, and JTAG interface `MI_02`.
- Two consecutive real `HELLO` probes succeeded on `COM3`.
- Both probes reported protocol 1, firmware 0.1.0, capabilities `0x00000009`, maximum payload 4096, and IR GPIO 44.
- The operator reported that M5Launcher 2.6.9 remained working after the application test.
- Partition-manager prompts or automatic partition changes were not recorded; their behavior remains unknown.
- No full-flash erase, direct PlatformIO upload, PP16 command, carrier test, or ESL transmission was performed.

## Measurements

| Quantity | Requested | Measured | Uncertainty/tolerance |
|---|---:|---:|---:|
| Application size | non-empty | 469,024 bytes | exact file length |
| ESP image magic | `0xE9` | `0xE9` | exact byte |
| Protocol version | 1 | 1 | exact decoded field |
| Maximum payload | 4096 bytes | 4096 bytes | exact decoded field |
| IR GPIO | 44 | 44 | reported configuration; electrical output not measured |

## Artifacts

- raw capture: none
- photo/video: operator-provided device screenshots in the interactive session; not stored in the repository
- host log: interactive command output; two successful `eslbridge probe --port COM3` runs
- serial log: decoded `HELLO` output only; raw serial bytes not retained

## Conclusion

For this artifact and setup, M5Launcher 2.6.9 installation, application boot, Windows CDC enumeration, a protocol-v1 `HELLO` round trip, and return-to-Launcher availability were observed. This confirms the tested T001A deployment path and the physical `HELLO` portion of T002. Partition-manager behavior remains unresolved because it was not recorded. No conclusion is made about GPIO 44 waveform quality, carrier frequency, PP16 timing, optical output, or ESL compatibility.

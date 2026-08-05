# Bench record: T009A corrected PP16 minimal image retest

- Date/time: 2026-08-05T12:29:02+02:00 (operator-local clock; sequence completed shortly afterward)
- Operator: repository owner, assisted remotely
- Repository commit: `9231bad`
- Firmware version: `0.1.0`
- Cardputer hardware: M5Stack Cardputer-Adv, SKU K132-Adv
- M5Launcher version: `2.6.9`
- Candidate artifact: `pricer-cardputer-bridge-cardputer-adv-9231bad.bin`
- Candidate size: `475088` bytes
- Candidate SHA-256: `164AEE98473FBCEF6C789E3E1423FA8489E3E99F9157832894279AAE306046D7`
- Git SHA / provenance / PP16 profile: `9231bad` / `clean` / `T006B-r1`
- ESL markings: `#19523-01`, `N4163114582613272`, `F16`, `2311`
- Expected PLID: `02 B3 B7 3F` from the current PrecIR-derived formula
- IR output: Cardputer built-in emitter on GPIO `44`
- Optical setup: emitter positioned approximately 1–2 cm from the ESL optical receiver; alignment held stable; no direct sunlight
- Host port: `COM3`

## Retained inputs

The exact binary inputs are committed under `tests/vectors/` and described by
`tests/vectors/manifest.json`:

| Vector | Command | Length | Repeats | Gap |
|---|---:|---:|---:|---:|
| `wake.bin` | `0x17` | 38 bytes | 400 | 2,000 us |
| `params-8x8-color.bin` | `0x05` | 33 bytes | 1 | 0 us |
| `data-8x8-color.bin` | `0x20` | 30 bytes | 1 | 0 us |
| `refresh.bin` | `0x01` | 34 bytes | 1 | 0 us |

The 8 × 8 data vector carries 8 bytes for the black/white plane, 8 bytes for
the red-mask plane, and compression type `0`. The final frame bytes and CRC16
values are recorded in the manifest.

## Procedure and observations

1. HELLO identity was verified before transmission: `9231bad`, `clean`, `T006B-r1`, GPIO 44.
2. The wake vector was accepted locally at 400 repetitions with a 2,000 us inter-repeat gap.
3. The params vector was accepted locally. One immediate consecutive send attempt returned a Windows `ClearCommError` device-command error; the bridge remained responsive and the exact data vector was retried once and accepted.
4. The data vector was accepted locally on retry.
5. The refresh vector was accepted locally.
6. After the e-paper refresh window, no visible display change was observed.

## Conclusion and next discriminator

This is a failed physical update trial. Local command acceptance proves only parser,
RMT scheduling, and USB command completion; it does not prove optical emission,
carrier correctness, PLID/ESL identification, or protocol compatibility. No ESL
compatibility claim is made. Per the issue follow-up order, the next discriminator
is T005 electrical/optical carrier measurement, followed by the external amplified
IR LED path if required. Phone-camera flicker was not used as evidence.

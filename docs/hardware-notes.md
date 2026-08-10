# Hardware notes

## Verified from official M5Stack documentation

| Item | Value | Status |
|---|---|---|
| Product | Cardputer-Adv, SKU K132-Adv | verified |
| Controller | Stamp-S3A, ESP32-S3FN8 | verified |
| Built-in IR output | GPIO 44 | verified |
| Display | ST7789V2, 240 x 135 | verified |
| USB mode | native USB CDC build flags documented | verified |
| PlatformIO baseline | `espressif32@6.7.0`, `esp32-s3-devkitc-1`, Arduino | verified |

Primary source: M5Stack Cardputer-Adv product documentation and schematics.

## Observed on the ESL photographs

| Marking | Observation | Interpretation status |
|---|---|---|
| PRICER | manufacturer | verified visually |
| `#19523-01` | product/revision marking | meaning unverified |
| `F16` | hardware/firmware family marking | meaning unverified |
| `2311` | printed code | date-code interpretation unverified |
| `N4163114582613272` | barcode text | likely serialized ESL identifier; unverified |
| screen | black/white/red content | verified visually |

## Working hypotheses

- Tag family: SmartTAG HD M+ Red.
- Resolution: 208 x 112 pixels.
- Communication: Pricer PP4 or PP16 over near-IR carrier near 1.245–1.255 MHz.
- The front black optical window contains the Pricer receiver.
- The Cardputer's built-in IR stage has adequate bandwidth and optical power at 1-2 cm.

Each hypothesis requires a reproducible test before it becomes a project fact.

## No-oscilloscope verification limits

Without an oscilloscope, logic analyzer, photodiode, or equivalent timing
instrument, verification is limited to software identity, bounded-command
behavior, camera-visible emission, and observable ESL symptoms:

- A phone or digital camera can show IR emission only if its sensor is
  sensitive to the wavelength. It cannot prove the 1.25 MHz carrier,
  frequency, duty cycle, PP4 symbol timing, optical power, or receiver
  behavior.
- A visible ESL response is end-to-end behavioral evidence for that trial. It
  cannot isolate carrier frequency, duty cycle, PP4 timing, optical power, or
  any other physical cause.
- Keep carrier frequency, duty cycle, symbol timings, and ESL compatibility as
  hypotheses pending measurement. No T005 physical claim is promoted here.

## Orientation-test plans and interpretation

Use these values to compare the selected key with the Cardputer screen. “Unique
encoded bytes” means plan payload bytes counted once per frame call; repeat
counts multiply AirFrames, not this byte total.

| Key/name | Frame calls | Repeated AirFrames | Unique encoded bytes | Intended observation |
|---|---:|---:|---:|---|
| `1` / `TAGTINKER_BLINK` | 2 | 242 | 45 | Addressed ping (161 repeats) plus addressed LED/flash (81 repeats); address/LED discriminator. No visible response is inconclusive unless the same ESL visibly responds to the original TagTinker LED Test. |
| `2` / `TAGTINKER_RLE_BLACK` | 4 | 121 | 130 | TagTinker Auto/RLE full-black primary plus blank accent; expected visible full black/refresh. |
| `3` / `TAGTINKER_RLE_WHITE` | 4 | 121 | 130 | TagTinker Auto/RLE all-white restore; expected visible white/refresh. |
| `4` / `TAGTINKER_1327_RAW` | 295 | 994 | 10024 | Existing all-white raw type-1327 page-0 plan. |

The preflight orientation screen identifies the selected `KEY` and name, then
shows `FRAMES`, `AIRFRAMES`, `BYTES`, `GPIO` (must be `44`), and
`PP4:1254.902->1250.000 D:50%` (requested/effective carrier, approximately
`1255->1250 kHz`, duty `50%`). It shows `STATE: SENDING` before transmission.
The final screen shows `OK 0x00 TX:+N` or `ERROR 0xHH TX:+N`, where `N` is the
completed TX-call delta, followed by current `GIT` SHA and `BUILD` provenance.
The ready screen also shows the current Git SHA and build provenance. The UI
redraws only before and after the plan; it does not redraw in the timing path.

An orientation status of `0x00` establishes only local RMT completion. A
`TX:+N` increase establishes completed local transmission calls, not ESL
receipt or physical waveform validity. Key 1 visibly changing an ESL is useful
discriminator evidence only when reproduced; no run is claimed here.

## No-oscilloscope sequence

This is a concise smoke sequence, not T005 measurement or ESL compatibility
validation:

1. Install the current **application-only** `firmware.bin` through M5Launcher
   SD browser or WebUI OTA. Do not use direct upload, a merged image, or a
   full-flash image.
2. Launch the bridge application. Confirm the displayed current Git SHA and
   build provenance match the selected artifact/build; stop on unknown or
   mismatched identity.
3. Align the built-in emitter and ESL receiver at `0-1 cm`, using only a
   personally owned or explicitly authorized ESL.
4. Run key `2` once and wait for the complete result.
5. If the ESL becomes black, run key `3` once to restore white and wait for
   the complete result.
6. Only then run key `4` raw. Do not treat a local `OK` as tag receipt.
7. A camera may confirm optical activity only; it cannot confirm the 1.25 MHz
   carrier, timing, duty, or optical power.
8. Record the exact selected key/name, `FRAMES`, `AIRFRAMES`, `BYTES`, GPIO,
   requested/effective carrier and duty, final status hex, `TX:+N`, Git SHA,
   build provenance, and visible ESL outcome.

## Unverified field report

User observation from previous commit `037b006`: key `1` completed
`STATUS 0x00` with TX delta `2` and camera-observed IR, but no ESL reaction.
This proves local RMT completion only; it does not prove a valid RF/optical
waveform or ESL receipt. No scope was available.


## Bench priorities

1. Confirm firmware can toggle GPIO 44 through RMT.
2. Measure actual carrier frequency and duty cycle.
3. Determine the frequency error produced by the ESP32 clock/divider combination.
4. Verify optical emission using a photodiode or camera as a weak smoke test.
5. Attempt wake-up frames only after PP16 timing evidence is documented.
6. Record distance, alignment, ambient light, repetitions, and observed ESL reaction.

## Fallback output path

If the built-in LED is too weak or its driver bandwidth is insufficient, retain the same firmware abstraction and route the RMT signal to an EXT-bus GPIO driving an external fast IR LED through a transistor/MOSFET stage. This is a fallback, not part of the minimum initial hardware.

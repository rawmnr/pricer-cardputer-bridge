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

## Bench priorities

1. Confirm firmware can toggle GPIO 44 through RMT.
2. Measure actual carrier frequency and duty cycle.
3. Determine the frequency error produced by the ESP32 clock/divider combination.
4. Verify optical emission using a photodiode or camera as a weak smoke test.
5. Attempt wake-up frames only after PP16 timing evidence is documented.
6. Record distance, alignment, ambient light, repetitions, and observed ESL reaction.

## Fallback output path

If the built-in LED is too weak or its driver bandwidth is insufficient, retain the same firmware abstraction and route the RMT signal to an EXT-bus GPIO driving an external fast IR LED through a transistor/MOSFET stage. This is a fallback, not part of the minimum initial hardware.

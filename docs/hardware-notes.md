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
behavior, and observable end-to-end symptoms:

- A phone or digital camera can show IR emission only if its sensor is
  sensitive to the wavelength. It cannot prove carrier frequency, duty cycle,
  PP4 symbol timing, or other physical waveform timing.
- A visible ESL response is end-to-end behavioral evidence that a complete
  trial produced an observable result. It cannot isolate carrier frequency,
  duty cycle, PP4 timing, optical power, receiver behavior, or any other
  physical cause.
- Keep the near-IR carrier frequency, duty cycle, symbol timings, and ESL
  compatibility as hypotheses pending measurement. Do not promote any T005
  physical claim without a recorded instrument measurement; no oscilloscope
  means T005 remains unvalidated.
- No physical run of the orientation test is claimed by this document.

## Orientation-test decision matrix

Use this as an interpretation guide, not as a bench record:

| Observation | Decision interpretation | Evidence label |
|---|---|---|
| Key `1` produces a visible ESL reaction | For that trial, carrier, address, PP4, and the basic command path worked; if the raw image plan still fails, investigate image parameters, data, or refresh. | **Verified only if reproduced; no run claimed here.** |
| Key `1` produces no reaction while a camera sees IR | Physical carrier frequency, duty, optical power, receiver compatibility, and target assumptions remain unresolved. Camera visibility is only weak optical-emission evidence. | **Hypotheses; camera cannot verify timing.** |
| Orientation command returns status `0x00` | Only local RMT completion is established; this does not mean the ESL accepted the frame. | **Verified firmware meaning.** |
| `GET_STATUS` `tx_count` increases | Key `1` increases the count by 2; the raw plan increases it by 295. These are completed local frame-transmission calls. | **Verified firmware behavior.** |

## Reproducible device smoke procedure

Use this ordered procedure for a device-only smoke check. It is not a substitute for T005 measurement or an ESL compatibility validation:

1. Install the current application-only `firmware.bin` through M5Launcher using its SD browser or WebUI OTA path. Do not use a merged image or full-flash upload.
2. Launch the bridge application and confirm the ready screen shows the expected seven-character Git SHA and the expected firmware profile. Stop if either identity is unknown or does not match the selected artifact.
3. Run the bounded carrier test on GPIO 44. Keep the firmware-enforced burst hard limit at or below 5 ms; never use a continuous-carrier mode.
4. If the camera sensor can see the emitter, observe the GPIO 44 IR output during the bounded burst and record whether emission was visible. Treat this as optical-emission smoke evidence only, not frequency or timing evidence.
5. Only on a personally owned or explicitly authorized ESL, optionally run the
   orientation test. Key `1` (`TAGTINKER_BLINK`) sends a direct ping 161 times
   with 5 ms gaps, pauses 20 ms, then sends the addressed flash command 81
   times with 5 ms gaps. Keys `2`/`3`/`4` select the same
   `TAGTINKER_1327_RAW` 295-AirFrame raw type-1327 page-0 image plan. Record
   whether the tag visibly responds, without treating a response or
   no-response as proof of physical timing correctness.
6. Using `docs/bench-template.md`, record the exact artifact path, device and firmware identity, distance, emitter/receiver alignment, ambient-light conditions, repetition settings, observed result, and raw artifact path. Mark unmeasured carrier frequency, duty, timing, and ESL compatibility as hypotheses.

The procedure may establish that the application boots, identifies itself, accepts a bounded request, and possibly produces visible optical or ESL behavior. It must not be used to promote T005 frequency/duty claims or any physical ESL compatibility claim without instrumented measurement.


## Bench priorities

1. Confirm firmware can toggle GPIO 44 through RMT.
2. Measure actual carrier frequency and duty cycle.
3. Determine the frequency error produced by the ESP32 clock/divider combination.
4. Verify optical emission using a photodiode or camera as a weak smoke test.
5. Attempt wake-up frames only after PP16 timing evidence is documented.
6. Record distance, alignment, ambient light, repetitions, and observed ESL reaction.

## Fallback output path

If the built-in LED is too weak or its driver bandwidth is insufficient, retain the same firmware abstraction and route the RMT signal to an EXT-bus GPIO driving an external fast IR LED through a transistor/MOSFET stage. This is a fallback, not part of the minimum initial hardware.

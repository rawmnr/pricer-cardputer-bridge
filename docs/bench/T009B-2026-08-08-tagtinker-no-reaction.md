# Bench record: T009B TagTinker settle-gap no-reaction retest

- Date/time: 2026-08-08; exact time not recorded
- Operator: not recorded
- Repository commit: not recorded
- Firmware version: not recorded
- Host package version: not recorded
- Cardputer hardware: not recorded in the retest notes
- ESL markings/identifier: not recorded in the retest notes
- Power state/battery notes: not recorded

## Objective

Exercise the repaired TagTinker type-1327 transmit scene and determine whether
preserving its settle gaps changes the previously observed no-reaction result.
Also record the software provenance comparison for the AirFrame bytes and PP4
symbol mapping.

## Equipment

- Cardputer IR transmitter and target ESL were used for the scene exercise.
- No photodiode, logic analyzer, or equivalent carrier/optical measurement
  instrument was used.
- Exact equipment details were not recorded.

## Setup

- Distance: not recorded
- Alignment: not recorded
- Ambient light: not recorded
- Measurement point: no electrical or optical measurement point
- Instrument settings: no measurement instrument used

## Command/input

```text
TagTinker type-1327 direct AirFrame scene; exact command and payload were not recorded.
Software comparison reference: local TagTinker upstream commit
81adb463eb9918b72a3acaabd5ef452960ba81ce.
Scene settle timing: 50 ms after ping, 50 ms after parameters, 1 ms after every
32 data frames, and 50 ms before refresh. Per-repeat metadata remains 81/16/3/21
with a 500 us inter-repeat gap.
```

## Expected result

The repaired scene should preserve the local TagTinker transmit ordering and
settle delays. Matching AirFrame bytes and PP4 raw-symbol mapping should be
reproducible against upstream commit
`81adb463eb9918b72a3acaabd5ef452960ba81ce`.

## Observed result

The local comparison matched the generated AirFrame bytes and PP4 raw-symbol
mapping. The repaired transmit scene was exercised, but the operator observed
no reaction from the target ESL. This result does not identify whether the
failure is in carrier generation, optical emission, receiver response, target
addressing, or protocol compatibility.

## Measurements

| Quantity | Requested | Measured | Uncertainty/tolerance |
|---|---:|---:|---:|
| AirFrame bytes vs. upstream | Match | Match | Software comparison; no physical inference |
| PP4 raw-symbol mapping vs. upstream | Match | Match | Software comparison; no physical inference |
| Ping/params settle delay | 50 ms each | Scene requirement recorded | GPIO timing not independently measured |
| Data-frame settle interval | 1 ms every 32 frames | Scene requirement recorded | GPIO timing not independently measured |
| Pre-refresh settle delay | 50 ms | Scene requirement recorded | GPIO timing not independently measured |
| Carrier frequency/duty | Not requested as a bench measurement | Not measured | No photodiode or equivalent instrument |
| Optical emission/power | Not requested as a bench measurement | Not measured | No photodiode or equivalent instrument |
| ESL reaction | Visible target response | No reaction observed | Operator observation only |
| Physical compatibility | Not established | Not established | No receiver feedback or qualified optical measurement |

## No-photodiode test matrix

| Check | Evidence | Result | Boundary |
|---|---|---|---|
| AirFrame byte generation | Local comparison with upstream commit | Match | Software correspondence only |
| PP4 symbol mapping | Local comparison with upstream commit | Match | Software correspondence only |
| Settle-gap repair | Transmit-scene definition | Delays recorded | Independent GPIO timing unmeasured |
| Target display reaction | Operator observation | No reaction | Does not identify failure layer |
| Carrier waveform | No photodiode/logic analyzer | Unmeasured | Frequency and duty unknown |
| Optical output | No photodiode | Unmeasured | Power and irradiance unknown |
| Physical ESL compatibility | No receiver feedback or qualified optical measurement | Unresolved | No compatibility claim |

## Artifacts

- raw capture: none; no photodiode or equivalent capture
- photo/video: not recorded
- host log: not recorded
- serial log: not recorded
- software reference: TagTinker upstream commit
  `81adb463eb9918b72a3acaabd5ef452960ba81ce`

## Conclusion

The local TagTinker comparison matches the generated AirFrame bytes and PP4
symbol mapping, and the transmit scene records the required 50 ms ping/params
settles, 1 ms every 32 data frames, and 50 ms pre-refresh delay. The operator's
known no-reaction result remains unresolved. Carrier and optical behavior were
not measured, so this record makes no claim of physical compatibility; distance,
alignment, ambient light, identity, port, artifact, and instrument details were
not recorded and must not be inferred.

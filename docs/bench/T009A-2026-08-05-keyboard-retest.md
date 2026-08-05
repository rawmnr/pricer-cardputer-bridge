# Bench record: T009A keyboard-triggered orientation retest

- Date/time: 2026-08-05; exact local time not recorded
- Operator: repository owner, assisted remotely
- Firmware commit / artifact: `b52aa4c` / `pricer-cardputer-bridge-cardputer-adv-b52aa4c.bin`
- Firmware version: `0.1.0`
- Cardputer hardware: M5Stack Cardputer-Adv, SKU K132-Adv
- M5Launcher version: `2.6.9`
- Artifact size: `475904` bytes
- Artifact SHA-256: `4A3E34224718C7F5D03BB99323F83613FAE4DC833A381E7632D94C097F6095CA`
- HELLO/UI identity: Git SHA `b52aa4c`, provenance `clean`, PP16 `T006B-r1`
- ESL markings: `#19523-01`, `N4163114582613272`, `F16`, `2311`
- Optical setup: Cardputer emitter positioned close to the ESL receiver; multiple key-triggered placements/orientations were attempted by the operator

## Keyboard mapping

Keys `1`, `2`, `3`, and `4` each trigger the same finite sequence retained in
`tests/vectors/`: one 400-repeat wake operation with a 2,000 us gap, followed by
params, 8 × 8 data, and refresh. The display labels the selected slot as
`TEST-1` through `TEST-4` and reports the local status and transmission count.

## Observations

The operator reports that the keyboard keys correctly triggered IR output for a
few seconds. The phone image shows visible camera response from the emitter;
this is weak emission smoke evidence only and is not carrier-frequency,
optical-power, or ESL-protocol evidence. The target e-paper display showed no
reaction.

## Conclusion and next discriminator

The PC-free key path and bounded local sequence are operational. The physical
ESL update still failed. No compatibility claim is made. The next discriminator
is T005 electrical/optical carrier measurement, followed by the external
amplified IR LED path if required.

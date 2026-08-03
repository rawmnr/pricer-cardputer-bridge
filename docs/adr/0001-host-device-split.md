# ADR 0001: Keep image and Pricer frame generation on the Windows host

- Status: accepted
- Date: 2026-08-03

## Context

The Cardputer must provide deterministic IR output, while the image and protocol research will evolve rapidly. Moving all logic into firmware would lengthen build/test cycles and make evidence capture harder.

## Decision

The Windows Python package owns image preparation, target profiles, Pricer addressing, frame generation, and transfer logging. Firmware owns bounded USB command handling and RMT waveform generation.

## Consequences

- USB is required for the first operational path.
- Host protocol must be stable and versioned.
- Pricer algorithms are unit-testable without hardware.
- A future standalone Cardputer mode is possible but not a phase-one requirement.

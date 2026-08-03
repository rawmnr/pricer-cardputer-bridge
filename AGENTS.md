# AGENTS.md

## Mission

Build a reproducible Windows-to-Cardputer-Adv bridge capable of updating personally owned Pricer ESLs. The host prepares content and Pricer frames; the Cardputer emits deterministic IR waveforms through GPIO 44.

The repository is deliberately staged. Do not jump directly to image transfer before USB framing and physical-layer measurements are proven.

## Read first

Before editing code, read in this order:

1. `README.md`
2. `docs/architecture.md`
3. `docs/protocol.md`
4. `docs/hardware-notes.md`
5. `docs/backlog.md`
6. the task brief under `docs/tasks/` matching the assigned issue
7. relevant ADRs under `docs/adr/`

Treat `docs/hardware-notes.md` as the boundary between **verified facts**, **working hypotheses**, and **unknowns**. Never silently promote a hypothesis to a fact.

## Repository boundaries

- `firmware/`: embedded transport, validation, UI, and deterministic RMT output only.
- `pc/`: serial discovery, protocol framing, Pricer frame preparation, image tooling, and user-facing CLI.
- `docs/`: decisions, measurements, protocol captures, provenance, and reproducible bench procedures.
- `vendor/`: absent by default. Do not vendor third-party code without an explicit issue and license review.

Do not move image rendering or Pricer data compression into firmware unless an ADR is accepted.

## Mandatory engineering constraints

### Safety

- Keep the firmware carrier-test hard limit at or below 5 ms.
- Never add an unbounded or continuous carrier mode.
- Validate all host-provided lengths, counts, frequencies, and durations before allocation or transmission.
- The default IR pin is GPIO 44; alternative pins must be compile-time or explicit configuration, never guessed.

### Protocol

- Host/device fields are little-endian.
- Every message carries magic, version, command, payload length, sequence number, and CRC32.
- Unknown commands must receive a structured `UNSUPPORTED_COMMAND` response.
- Malformed messages must not reset or block the device.
- Keep protocol constants synchronized between `firmware/include/bridge_protocol.hpp` and `pc/src/eslbridge/protocol.py`.
- Any protocol change requires tests and an update to `docs/protocol.md` in the same commit.

### Firmware

- Avoid heap allocation in the transmit hot path.
- No blocking wait without a documented timeout.
- Use the ESP32-S3 RMT peripheral for waveform output.
- Keep UI rendering out of timing-critical code.
- Return explicit error codes; do not collapse hardware and validation failures into a generic error.
- The firmware must compile with the pinned PlatformIO environment before completion.

### Python host

- Support Windows first; do not assume POSIX serial device names.
- Use type hints for public functions.
- Keep binary encoding/decoding pure and unit tested.
- Serial I/O must use explicit timeouts and close ports deterministically.
- CLI failures must return non-zero exit codes and actionable messages.
- Do not bury protocol constants inside CLI functions.

### Research and provenance

- Prefer primary sources: M5Stack schematics/docs, Espressif docs, and original reverse-engineering repositories.
- Record measurements with device, firmware commit, method, conditions, and raw artifact path.
- PrecIR is GPL-3.0. Copied/adapted code must retain notices and be recorded in `THIRD_PARTY.md` with source file and commit SHA.
- Do not copy code from a repository with an unknown or incompatible license.
- Clearly label clean-room reimplementations and the evidence used.

## Agent workflow

1. Restate the task and acceptance criteria in the work log or PR description.
2. Inspect existing tests and protocol docs before changing code.
3. Make the smallest coherent change that satisfies one task.
4. Add or update tests before declaring completion.
5. Run the relevant command set below.
6. Update docs for behavior, interface, measurement, or architecture changes.
7. Summarize risks and unresolved assumptions in the PR.

Preferred branches:

```text
feat/<task-id>-<slug>
fix/<task-id>-<slug>
docs/<task-id>-<slug>
```

Use conventional commit subjects where practical:

```text
feat(firmware): add bounded carrier test
fix(protocol): reject oversized payloads
test(pc): cover CRC mismatch
docs(research): record GPIO 44 measurement
```

Do not mix opportunistic refactors with hardware or protocol changes.

## Required checks

From the repository root:

```powershell
uv run --project .\pc ruff check .\pc
uv run --project .\pc mypy .\pc\src
uv run --project .\pc pytest
pio run -d .\firmware
```

For formatting:

```powershell
uv run --project .\pc ruff format --check .\pc
```

Hardware-dependent changes must also include a bench record using the template in `docs/bench-template.md`. CI passing is not evidence that an IR waveform is correct.

## Definition of done

A task is complete only when:

- acceptance criteria are met;
- automated tests cover normal and failure paths;
- firmware builds when firmware code changed;
- protocol/docs are synchronized;
- no safety limit was weakened;
- third-party provenance is recorded;
- hardware claims are backed by a bench record or explicitly remain hypotheses;
- the PR contains commands run and their results.

## Current implementation priorities

Work in dependency order unless the issue explicitly says otherwise:

1. `T001` reproducible toolchain and CI.
2. `T002` USB HELLO/probe round trip.
3. `T003` parser hardening and fuzz-style host tests.
4. `T004` bounded GPIO 44 carrier test.
5. `T005` physical carrier measurement and frequency calibration.
6. `T006` PP16 symbol encoder from verified timing evidence.
7. `T007` raw Pricer frame transmission.
8. `T008` PrecIR interoperability adapter and licensing audit.
9. `T009` monochrome image transfer.
10. `T010` tricolor image transfer and repeatability study.

Do not implement `T009` or `T010` before `T005-T008` have evidence and tests.

# Agent-ready backlog

## Dependency graph

```text
T001 -> T001A -> T002 -> T003
                  |       |
                  +-----> T004 -> T005 -> T006 -> T007 -> T008 -> T009 -> T010
```

## T001 - Reproducible toolchain, CI, and application artifact

Acceptance:

- `uv sync --project pc --all-groups` succeeds on Windows and CI;
- `pytest`, `ruff`, and `mypy` pass;
- PlatformIO builds the firmware in CI;
- CI verifies and uploads the application-only `firmware.bin` with an explicit Cardputer-Adv filename;
- dependency pins and update policy are documented.

Task brief: `docs/tasks/T001-toolchain-ci.md`

## T001A - M5Launcher deployment validation

Acceptance:

- the CI/local application-only binary is accepted by M5Launcher;
- SD-card and/or WebUI installation is documented with the exact Launcher version tested;
- the bridge application boots without a full flash erase;
- reboot can return to M5Launcher;
- COM-port behavior across Launcher-to-application handoff is recorded;
- no project code rewrites the partition table, OTA metadata, or all NVS;
- recovery through Cardputer-Adv download mode and M5Burner is documented but not used as the normal path.

Task brief: `docs/tasks/T001A-m5launcher-deployment.md`

## T002 - USB HELLO/probe round trip

Acceptance:

- firmware returns a valid HELLO response after being launched by M5Launcher;
- host discovers an explicit COM port and validates version/capabilities;
- reconnect/retry behavior handles USB CDC re-enumeration after Launcher handoff;
- timeout, CRC mismatch, and wrong-device failures are actionable;
- tests use a fake serial transport.

Task brief: `docs/tasks/T002-usb-hello.md`

## T003 - Parser hardening

Acceptance:

- fragmented, concatenated, malformed, oversized, and noisy streams are handled;
- parser cannot write beyond fixed buffers;
- fuzz/property-style host tests cover encode/decode invariants;
- parser timeout and resynchronization are documented.

## T004 - Bounded carrier test

Acceptance:

- RMT drives GPIO 44 at requested safe values;
- duration is hard-limited to 5 ms;
- invalid frequency/duty/duration requests are rejected;
- UI shows local attempt and result;
- no continuous carrier path exists.

Task brief: `docs/tasks/T004-carrier-test.md`

## T005 - Carrier measurement and calibration

Acceptance:

- measured frequency and duty cycle are recorded for at least three requested frequencies around 1.245 MHz;
- measurement method and uncertainty are documented;
- default setting is selected from evidence;
- raw captures are retained outside Git or as compressed release artifacts.

## T006 - PP16 symbol encoder

Acceptance:

- timing source is cited and distinguished from inference;
- pure encoder tests map known nibbles/bytes to expected symbol durations;
- RMT output is compared against expected timing with tolerances;
- long frames stream without buffer overflow.

## T007 - Raw Pricer frame command

Acceptance:

- host can send a raw frame with repeat count and gap;
- firmware enforces maximum frame/repeat/gap limits;
- local completion and timeout are distinct;
- complete transfer metadata is logged.

## T008 - PrecIR interoperability adapter and audit

Acceptance:

- exact PrecIR commit is pinned;
- license/provenance review is recorded;
- adapter can consume generated PrecIR frames or a clean equivalent;
- golden-vector tests preserve frame bytes;
- no unsupported claim of ESL compatibility is made.

## T009 - Monochrome image transfer

Acceptance:

- confirmed target dimensions and bit order;
- deterministic test image and raw frame artifacts;
- at least three repeatable successful updates;
- failed trials and settings retained.

## T010 - Tricolor transfer

Acceptance:

- black, white, and red regions render correctly;
- ghosting/refresh behavior recorded;
- repeated updates do not leave increasing artifacts in the short test series;
- validated tag profile is documented separately from generic assumptions.

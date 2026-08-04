# Firmware tests

Firmware protocol and stream parser behavior is validated locally using the PlatformIO Unity test framework (`test/test_stream_parser`).

## Test Environments & Guidance

- **Compile-Only & Host Unit Verification**:
  - Unit tests for protocol encoding/decoding, stream framing, noise resynchronization, and bounded buffer bounds execute locally via PlatformIO's Unity suite (`pio test -e native` or host unit test runner).
  - CI verifies firmware compilation across target environments without requiring connected hardware.

- **Hardware-in-the-Loop (HIL) Execution**:
  - Physical Cardputer hardware tests execute on real target boards connected via USB CDC.
  - Hardware tests validate physical serial timing, RMT carrier generation, button UI state, and end-to-end USB CDC communication against real hardware.

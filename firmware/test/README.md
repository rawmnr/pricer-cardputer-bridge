# Firmware tests

The host-compatible firmware suites run with PlatformIO's Unity test
framework. From the repository root on Windows:

```powershell
pio test -d firmware -e native
```

This command currently runs all five suites:

- `test_bridge_protocol`
- `test_ir_transmitter`
- `test_orientation_test`
- `test_pp16_encoder`
- `test_pp4_encoder`

The native environment requires a C++17-capable GCC/G++ compiler on `PATH`.
CI also verifies firmware compilation across target environments without
requiring connected hardware.

## Hardware-in-the-Loop (HIL) Execution

Physical Cardputer hardware tests execute on real target boards connected via
USB CDC. Hardware tests validate physical serial timing, RMT carrier
generation, button UI state, and end-to-end USB CDC communication against real
hardware.

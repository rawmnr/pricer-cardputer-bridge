# ADR 0002: Use PlatformIO + Arduino with direct ESP-IDF RMT access

- Status: accepted for scaffold
- Date: 2026-08-03

## Context

M5Stack publishes an official PlatformIO baseline for Cardputer-Adv and its Arduino library simplifies display/keyboard support. Precise optical timing still requires the ESP32-S3 RMT peripheral.

## Decision

Use the official M5Stack PlatformIO baseline (`espressif32@6.7.0`, `esp32-s3-devkitc-1`, Arduino) and call the RMT driver exposed by the bundled ESP-IDF version directly.

## Consequences

- UI integration remains simple.
- RMT code is isolated behind `IrTransmitter` to ease a future ESP-IDF 5 migration.
- Dependency updates require a compile and physical timing regression.
- Agents must not mix old and new RMT APIs in the same build.

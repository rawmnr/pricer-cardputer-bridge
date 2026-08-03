# ADR 0003: Use M5Launcher as the primary deployment path

- Status: accepted
- Date: 2026-08-03

## Context

The Cardputer-Adv already runs M5Launcher, which can install and launch normal application binaries from microSD, WebUI OTA, and online sources. Replacing the complete flash for every iteration would slow development and risk losing the existing Launcher environment.

## Decision

Keep M5Launcher installed. Build the bridge as an application-only PlatformIO binary and install it through M5Launcher. Treat direct bootloader upload and full-flash recovery as exceptional paths.

## Consequences

- CI publishes a clearly named application `.bin` artifact.
- Deployment acceptance includes install, boot, USB re-enumeration, and return to Launcher.
- The application must not rewrite partition tables, OTA metadata, Launcher metadata, or all NVS.
- Windows tooling must tolerate COM-port changes after Launcher starts the application.
- Tagged release automation waits until versioning and physical Launcher compatibility are validated.
- M5Burner recovery remains documented as a fallback.

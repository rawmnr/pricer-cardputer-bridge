# Architecture

## Context

The system must update a Pricer ESL using only:

- a Windows MSI Claw 8 AI+;
- an M5Stack Cardputer-Adv connected by USB;
- M5Launcher already installed on the Cardputer;
- the Cardputer's built-in IR emitter;
- the target ESL.

There is no reference ESL Blaster, external IR dongle, or logic analyzer assumed in the minimum setup. Measurement tools remain strongly recommended before trusting PP16 timing.

## Components

### Windows host

Responsibilities:

- build or download the application-only Cardputer binary;
- install it through M5Launcher WebUI or place it on the microSD card;
- discover and open the Cardputer USB CDC port after application boot;
- prepare images and templates;
- derive or accept the ESL identifier/address;
- generate Pricer wake-up, parameter, data, and refresh frames;
- request IR transmission with repeat count and inter-repeat gap;
- log every transfer and preserve raw payloads for reproducibility;
- later expose Home Assistant/MQTT integration.

The host must remain usable without a GUI. The CLI is the reference interface.

### M5Launcher

M5Launcher is the resident deployment and application-selection layer. It installs a normal application binary into an application partition, keeps its own system components available, and starts the selected application.

Project assumptions and constraints:

- the input artifact is the PlatformIO application-only `firmware.bin`;
- Launcher SD install and WebUI OTA are the normal deployment paths;
- full-flash erase, partition-table replacement, and merged-image flashing are not part of routine development;
- returning to Launcher is a required deployment acceptance test;
- Launcher and the bridge application may enumerate USB differently, so Windows COM-port identity cannot be assumed stable across the handoff.

### Cardputer firmware

Responsibilities:

- boot correctly as an application installed by M5Launcher;
- advertise firmware/protocol capabilities;
- validate framed USB commands and CRCs;
- enforce safety limits;
- translate a validated PP4 or PP16 request into RMT symbols;
- drive GPIO 44;
- report completion or a precise failure code;
- display minimal connection and transmission state;
- avoid modifying Launcher-managed partitions or global NVS state.

The firmware does not understand images or Home Assistant entities.

### Pricer ESL

Treated as a black box during the first phase. We communicate through the original optical receiver and retain the factory e-paper controller and waveforms.

## Deployment flow

```text
source checkout or CI
        |
        v
PlatformIO build
        |
        v
application-only firmware.bin
        |
        +-------------------+
        |                   |
        v                   v
M5Launcher SD install   M5Launcher WebUI OTA
        |                   |
        +---------+---------+
                  v
       installed application partition
                  |
                  v
       Pricer Cardputer Bridge boots
                  |
                  v
       USB CDC re-enumerates on Windows
```

A local firmware completion response proves only that the application executed the requested operation. It does not prove the ESL accepted the optical frame.

## Runtime data flow

```text
PNG/template
   |
   v
host image quantizer (future)
   |
   v
Pricer frame builder (future)
   |
   v
USB bridge message + CRC32
   |
   v
firmware parser and bounds validation
   |
   v
PP4/PP16 encoder -> RMT symbols
   |
   v
GPIO 44 -> built-in IR LED -> ESL receiver
```

## Reliability model

The initial Cardputer design is transmit-only. A successful device response proves the Cardputer completed its local RMT operation; it does not prove the ESL received or accepted a frame. ESL success is initially visual and later may be inferred through an added optical receive path if hardware permits.

Every host transfer should therefore retain:

- bridge firmware version and commit;
- M5Launcher version and installation path when relevant;
- protocol version;
- target identifier;
- exact frames and repeat settings;
- timestamps;
- observed ESL result;
- environmental notes such as distance and ambient light.

Every deployment validation should retain:

- produced binary filename, byte size, and hash;
- PlatformIO environment;
- install method: SD or WebUI;
- whether the application booted;
- observed COM ports before and after handoff;
- whether reboot returned to Launcher;
- any Launcher partition changes or warnings.

## Security model

- No network listener in the initial bridge firmware.
- M5Launcher WebUI is used only as a deployment mechanism and should not be exposed to an untrusted network.
- USB commands are unauthenticated because the physical USB connection is the trust boundary.
- Host-supplied sizes and durations are untrusted and bounded.
- Future MQTT/Home Assistant credentials belong on the host or a separate gateway layer, not in the first firmware.

## Recovery model

Routine development never requires a full flash erase. If Launcher is damaged or the device no longer boots normally, use the documented Cardputer-Adv download mode and M5Burner to restore firmware. Recovery is distinct from normal application deployment.

## Extension points

- tagged GitHub Releases containing versioned M5Launcher application binaries;
- alternative IR output GPIO and external transistor driver;
- optional optical receiver for acknowledgements;
- local Cardputer templates from microSD;
- host image pipeline and device registry;
- MQTT service around the CLI/library;
- multiple known Pricer tag profiles.

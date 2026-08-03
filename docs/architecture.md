# Architecture

## Context

The system must update a Pricer ESL using only:

- a Windows MSI Claw 8 AI+;
- an M5Stack Cardputer-Adv connected by USB;
- the Cardputer's built-in IR emitter;
- the target ESL.

There is no reference ESL Blaster, external IR dongle, or logic analyzer assumed in the minimum setup. Measurement tools remain strongly recommended before trusting PP16 timing.

## Components

### Windows host

Responsibilities:

- discover and open the Cardputer USB CDC port;
- prepare images and templates;
- derive or accept the ESL identifier/address;
- generate Pricer wake-up, parameter, data, and refresh frames;
- request IR transmission with repeat count and inter-repeat gap;
- log every transfer and preserve raw payloads for reproducibility;
- later expose Home Assistant/MQTT integration.

The host must remain usable without a GUI. The CLI is the reference interface.

### Cardputer firmware

Responsibilities:

- advertise firmware/protocol capabilities;
- validate framed USB commands and CRCs;
- enforce safety limits;
- translate a validated PP16 request into RMT symbols;
- drive GPIO 44;
- report completion or a precise failure code;
- display minimal connection and transmission state.

The firmware does not understand images or Home Assistant entities.

### Pricer ESL

Treated as a black box during the first phase. We communicate through the original optical receiver and retain the factory e-paper controller and waveforms.

## Data flow

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
PP16 encoder -> RMT symbols
   |
   v
GPIO 44 -> built-in IR LED -> ESL receiver
```

## Reliability model

The initial Cardputer design is transmit-only. A successful device response proves the Cardputer completed its local RMT operation; it does not prove the ESL received or accepted a frame. ESL success is initially visual and later may be inferred through an added optical receive path if hardware permits.

Every host transfer should therefore retain:

- bridge firmware version;
- protocol version;
- target identifier;
- exact frames and repeat settings;
- timestamps;
- observed ESL result;
- environmental notes such as distance and ambient light.

## Security model

- No network listener in the initial firmware.
- USB commands are unauthenticated because the physical USB connection is the trust boundary.
- Host-supplied sizes and durations are untrusted and bounded.
- Future MQTT/Home Assistant credentials belong on the host or a separate gateway layer, not in the first firmware.

## Extension points

- alternative IR output GPIO and external transistor driver;
- optional optical receiver for acknowledgements;
- local Cardputer templates from microSD;
- host image pipeline and device registry;
- MQTT service around the CLI/library;
- multiple known Pricer tag profiles.

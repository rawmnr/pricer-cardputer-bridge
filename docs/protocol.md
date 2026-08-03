# USB bridge protocol v1

This protocol transports commands between the Windows host and the Cardputer. It is intentionally independent from Pricer PP4/PP16 packet formats.

## Byte order

All multi-byte integers are unsigned little-endian.

## Frame

| Offset | Size | Field | Description |
|---:|---:|---|---|
| 0 | 4 | magic | ASCII `ESLI` |
| 4 | 1 | version | `0x01` |
| 5 | 1 | command | request or response command |
| 6 | 1 | flags | reserved; must be zero in v1 |
| 7 | 1 | status | zero for requests; response status code |
| 8 | 2 | sequence | host-selected request identifier |
| 10 | 2 | payload_length | 0..4096 bytes |
| 12 | N | payload | command-specific bytes |
| 12+N | 4 | crc32 | IEEE CRC32 over bytes 4 through 11+N |

The magic is excluded from CRC calculation so a receiver can resynchronize by scanning for `ESLI`. The CRC covers version, command, flags, status, sequence, length, and payload.

## Commands

### `0x01 HELLO`

Request payload: empty.

Response payload:

| Field | Size | Meaning |
|---|---:|---|
| protocol_version | 1 | host protocol version |
| firmware_major | 1 | semantic version major |
| firmware_minor | 1 | semantic version minor |
| firmware_patch | 1 | semantic version patch |
| capabilities | 4 | bit mask |
| max_payload | 2 | accepted payload bytes |
| ir_gpio | 1 | configured IR GPIO |
| reserved | 1 | zero |

Capability bits:

- bit 0: bounded carrier test;
- bit 1: PP4 transmission;
- bit 2: PP16 transmission;
- bit 3: device display/status UI.

Only bit 0 and bit 3 are expected in the initial scaffold.

### `0x02 GET_STATUS`

Request payload: empty.

Response payload:

| Field | Size | Meaning |
|---|---:|---|
| last_command | 1 | most recent command byte |
| transmitter_state | 1 | idle, busy, or fault |
| last_error | 1 | status code |
| reserved | 1 | zero |
| tx_count | 4 | completed local transmissions |

### `0x10 CARRIER_TEST`

Request payload:

| Field | Size | Meaning |
|---|---:|---|
| frequency_hz | 4 | requested carrier frequency |
| duration_us | 4 | requested burst duration, max 5000 us |
| duty_percent | 1 | 10..60 |
| reserved | 3 | zero |

The device rejects unsafe values. The initial host defaults are 1,245,000 Hz, 2,000 us, and 50%.

Response payload is empty on success.

### `0x11 SEND_PRICER_FRAME`

Reserved payload shape:

| Field | Size | Meaning |
|---|---:|---|
| modulation | 1 | `4` for PP4 or `16` for PP16 |
| reserved | 1 | zero |
| repeats | 2 | number of frame repetitions |
| inter_repeat_gap_us | 4 | gap between repetitions |
| frame_length | 2 | raw Pricer bytes that follow |
| frame | N | raw Pricer frame bytes |

Until PP16 is validated, the firmware returns `NOT_IMPLEMENTED`.

## Status codes

| Value | Name | Meaning |
|---:|---|---|
| 0x00 | OK | command completed |
| 0x01 | BAD_MAGIC | internal/debug use; receiver normally resynchronizes |
| 0x02 | BAD_VERSION | unsupported host protocol version |
| 0x03 | BAD_CRC | CRC mismatch |
| 0x04 | BAD_LENGTH | payload length invalid or too large |
| 0x05 | UNSUPPORTED_COMMAND | command unknown |
| 0x06 | INVALID_ARGUMENT | command payload invalid |
| 0x07 | BUSY | transmitter unavailable |
| 0x08 | HARDWARE_ERROR | RMT or GPIO operation failed |
| 0x09 | NOT_IMPLEMENTED | reserved command not implemented |
| 0x0A | TIMEOUT | bounded operation timed out |

## Stream behavior

- The receiver scans for the four-byte magic.
- A partial frame is retained until complete or until a parser timeout.
- On CRC, version, or argument errors, the device returns a response with the same command and sequence when recoverable.
- The host sends one request at a time in v1.
- Maximum payload is 4096 bytes even if the transport can carry more.

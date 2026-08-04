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

Maximum payload size is 4096 bytes. Header size is 12 bytes and CRC is 4 bytes, yielding a maximum total frame size of 4112 bytes (`kMaxFrameSize`).
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

### Parser Contract

1. **Bounded Buffers and Reads**:
   - Host (`BridgeTransport`) and firmware (`StreamParser`) enforce strictly bounded buffers with zero heap allocation in the parsing hot path.
   - The maximum allowed frame size is 4112 bytes (`kMaxFrameSize` = 12-byte header + 4096-byte payload + 4-byte CRC).
   - All transport reads are capped, and frame encoding/decoding is strictly guarded against buffer overflow.

2. **Immediate Oversized Length Rejection**:
   - When the parser ingests the 12-byte header, it inspects `payload_length` immediately.
   - If `payload_length > 4096`, the frame is rejected at the header boundary (`BAD_LENGTH`) without attempting to ingest or allocate buffer memory for the payload.

3. **Concatenated & Fragmented Frame Preservation**:
   - The host maintains a persistent, bounded receive buffer across reads. If multiple frames arrive concatenated in a single transport stream read, unconsumed bytes are retained in the buffer so trailing frames survive and parse deterministically.
   - Fragmented frames received across multiple reads/pushes accumulate in the parser buffer until complete or timed out.

4. **Resynchronization and Noise Handling**:
   - The receiver continuously scans incoming bytes for the 4-byte magic pattern `ESLI` (`0x45 0x53 0x4C 0x49`).
   - Unrecognized leading bytes or bytes corrupting the magic pattern are discarded as noise.
   - **Fast Magic Resynchronization**: When a byte breaks the magic prefix sequence, if that byte is `'E'` (the first magic byte), it is retained as the start of a candidate magic sequence rather than resetting to index zero.
   - Unrecoverable noise and short partial headers (where magic fails before a full header is assembled) are discarded silently without returning an error frame.

5. **Timeout & Inactivity Handling**:
   - **Firmware Inactivity Timeout**: Firmware `StreamParser` exposes a non-blocking `poll(now_ms)` method executed periodically from the main loop `loop()`. If an incomplete frame remains in the buffer without receiving new bytes for longer than `kParserTimeoutMs` (500 ms), the partial state is reset and an inactivity timeout occurs.
   - **Host Timeout Clearing**: If a transport read times out before a complete response frame is parsed, partial buffer state is cleared deterministically to prevent cross-request stream corruption.

6. **Recoverable Error Responses**:
   - Structured error responses (such as `BAD_VERSION`, `BAD_CRC`, `BAD_LENGTH`, or `TIMEOUT`) are sent by the device **only when `command` and `sequence` fields are recoverable** from a completed 12-byte header.
   - If `command` and `sequence` are available, the firmware returns a response frame containing the matching `command` and `sequence` with the appropriate non-zero `status` code, and then resets parser state.
   - Silent dropping applies to unrecoverable noise or incomplete headers to prevent feedback loops over corrupted transport lines.
   - `BAD_CRC` (`0x03`) is returned as a distinct error status code when header and payload are complete but CRC validation fails.

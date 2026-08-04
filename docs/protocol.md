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

The current implementation advertises bits 0, 2, and 3. PP16 support remains provisional until physical carrier and target-ESL validation is complete.

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
| frequency_hz | 4 | requested carrier frequency (500,000..2,000,000 Hz) |
| duration_us | 4 | requested burst duration, max 5000 us |
| duty_percent | 1 | 10..60 |
| reserved | 3 | zero |

The device rejects unsafe values outside allowed frequency (500,000 Hz .. 2,000,000 Hz), duration (1 us .. 5000 us), or duty percent (10% .. 60%). The initial host defaults are 1,245,000 Hz, 2,000 us, and 50%.

The 5000 us duration limit applies to the complete scheduled RMT envelope with no extra trailing interval. After burst completion or operation timeout, output returns to idle low. Carrier transmission wait is bounded (`rmt_wait_tx_done`), and `TIMEOUT` (`0x0A`) is returned as a distinct status error if the transmission wait deadline expires. Hardware output frequency/optical characteristics remain uncalibrated without external measurement; no claim is made regarding measured frequency or optical output power.

Response payload is empty on success.
### `0x11 SEND_PRICER_FRAME`

Request payload format:

| Field | Size | Meaning | Valid Range / Constraint |
|---|---:|---|---|
| modulation | 1 | Modulation scheme | `4` for PP4 or `16` for PP16 |
| reserved | 1 | Reserved byte | Must be zero (`0`) |
| repeats | 2 | Number of frame repetitions | 1..100 (must be > 0; continuous mode prohibited) |
| inter_repeat_gap_us | 4 | Gap between repetitions | 0..1,000,000 us (max 1 second) |
| frame_length | 2 | Raw Pricer frame bytes count | 1..256 bytes (must match payload length - 10) |
| frame | N | Raw Pricer frame bytes | `frame_length` bytes |

The payload length MUST equal `10 + frame_length`. If payload length != `10 + frame_length`, or if `reserved != 0`, `repeats` is not in 1..100, `inter_repeat_gap_us > 1,000,000`, or `frame_length` is not in 1..256, the device returns `INVALID_ARGUMENT` (`0x06`).

For `modulation = 16` (PP16), transmission is executed through ESP32 RMT using fixed storage (`eslbridge::pp16::encode_frame`) with explicit bounded waits per repeat (`rmt_wait_tx_done`). If transmission wait deadline expires, `TIMEOUT` (`0x0A`) is returned. Continuous RMT loop mode is prohibited.

For `modulation = 4` (PP4), transmission is not yet implemented and returns `NOT_IMPLEMENTED` (`0x09`).

Response payload is empty on success (`OK`, `0x00`).

> **PROVISIONAL / INFERRED WARNING:**
> Transmission of raw PP16 frames is software-integrated and verified against waveform timing models, but remains **untested against physical Pricer ESL target tags in this setup**. No claim of tag or physical carrier compatibility is made.

## PP16 Symbol Encoder

A profile-driven PP16 symbol-duration encoder is implemented in Python (`eslbridge.pp16`) and C++ (`eslbridge::pp16`).

### Timing Profile Specification & Provenance

Default profile timing values are derived directly from published **PrecIR** prior art:
- **Source:** PrecIR commit `b09951e2b3d2741e4ca08f929eafef849f6fc006` (`hardware/esl_blaster/FW02/Src/main.c`), under **GPL-3.0** license.
- **Reference:** Furrtek RE documentation (`https://www.furrtek.org/index.php?a=esl`).

| Attribute | Value / Constraint | Meaning |
|---|:-:|---|
| `carrier_frequency_hz` | 1,250,000 Hz | Nominal IR carrier frequency (range 500 kHz .. 2 MHz) |
| `duty_percent` | 50% | Nominal duty cycle (range 10% .. 60%) |
| `symbol_burst_us` | 21 us | Fixed carrier pulse width per data symbol |
| `is_provisional` | `true` | Indicates profile is untested on target hardware |

### Nibble Symbol Duration Table

Each 4-bit nibble $n \in [0, 15]$ maps directly to a 16-entry total symbol duration table in microseconds:

| Nibble | Hex | Total Symbol Duration (us) | Gap Duration (us) = Total - 21 us |
|:-:|:-:|:-:|:-:|
| 0 | `0x0` | 27 | 6 |
| 1 | `0x1` | 51 | 30 |
| 2 | `0x2` | 35 | 14 |
| 3 | `0x3` | 43 | 22 |
| 4 | `0x4` | 147 | 126 |
| 5 | `0x5` | 123 | 102 |
| 6 | `0x6` | 139 | 118 |
| 7 | `0x7` | 131 | 110 |
| 8 | `0x8` | 83 | 62 |
| 9 | `0x9` | 59 | 38 |
| 10 | `0xA` | 75 | 54 |
| 11 | `0xB` | 67 | 46 |
| 12 | `0xC` | 91 | 70 |
| 13 | `0xD` | 115 | 94 |
| 14 | `0xE` | 99 | 78 |
| 15 | `0xF` | 107 | 86 |

### Byte & Symbol Mapping

1. Each payload byte is split into high-nibble `(byte >> 4) & 0x0F` then low-nibble `byte & 0x0F`.
2. Each nibble $n$ emits an IR carrier burst of `symbol_burst_us` (21 us) followed by space/gap of `nibble_durations_us[n] - symbol_burst_us`.
3. Optional preamble and trailer symbols may be configured if required by future tag profiles; by default, no preamble/trailer is assumed.

### PrecIR Interoperability Adapter & Frame Finalization

The Python host library provides a clean-room PrecIR adapter module (`eslbridge.precir`) for formatting raw Pricer PP16 frames matching PrecIR driver conventions (`tools_python/pr.py`):

1. **Header & Frame Layout**:
   - PP16 header prefix: 4 bytes `b"\x00\x00\x00\x40"` (`PRECIR_PP16_HEADER`).
   - PP4 has no extra header prefix (`PRECIR_PP4_HEADER = b""`).
   - Variable raw payload bytes.
   - 16-bit little-endian trailer CRC16 (`calculate_precir_crc16`).

2. **CRC16 Algorithm**:
   - Polynomial: $0x8408$ (reflected $0x1021$).
   - Initial value: $0x8408$.
   - Calculated over raw payload bytes **before** prepending the 4-byte header prefix.

3. **Repeat Metadata Separation**:
   - Frame finalization (`finalize_precir_frame`) outputs raw Pricer frame bytes (`1..256` bytes).
   - Transmission metadata (`repeats` count in `1..100` and `inter_repeat_gap_us` in `0..1,000,000`) is passed in the host bridge request envelope (`PricerFrameRequest`) and is **never embedded inside raw frame payload bytes**.

4. **Provenance & Licensing**:
   - Derived from published PrecIR prior art commit `b09951e2b3d2741e4ca08f929eafef849f6fc006` (`tools_python/pr.py`, GPL-3.0).
   - Clean-room implementation: no PrecIR source code was copied or vendored into this repository.
### Physical Validation Limitations

> **PROVISIONAL / INFERRED WARNING:**
> Frame structures, CRC calculations, and symbol timings in default profiles are derived from published prior art and remain **untested against physical Pricer ESL target tags in this setup**. Physical carrier measurements from task T005 have not been performed. No claim of tag or physical carrier compatibility is made.
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

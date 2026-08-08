# Research log

## 2026-08-03 - Initial scaffold evidence

### Cardputer-Adv

Official M5Stack documentation states:

- Stamp-S3A / ESP32-S3FN8 controller;
- built-in IR emitter;
- IR TX mapped to GPIO 44;
- PlatformIO baseline using `espressif32@6.7.0`, `esp32-s3-devkitc-1`, Arduino, and native USB CDC build flags.

Source: https://docs.m5stack.com/en/core/Cardputer-Adv

### ESP32-S3 RMT

Espressif documents RMT as a general-purpose pulse generator capable of carrier modulation. The ESP-IDF 4.4 API used by the pinned Arduino/PlatformIO baseline exposes `carrier_freq_hz`, `carrier_duty_percent`, and timed RMT items.

Source: https://docs.espressif.com/projects/esp-idf/en/v4.4/esp32s3/api-reference/peripherals/rmt.html

### PrecIR

PrecIR is prior art for Pricer ESL transfers and supports serial transmitters and ESL Blaster workflows. Its source is GPL version 3. No source is copied in the initial scaffold.

Source: https://github.com/furrtek/PrecIR

### Open questions

- Exact PP16 carrier, burst, gap, and preamble timings for the target tag.
- Mapping from the printed barcode to the Pricer logical identifier.
- Frame/address/CRC format needed by the target generation.
- Wake-up repeat duration.
- Image dimensions, bit-plane order, compression, and refresh command.
- Whether the Cardputer built-in IR LED can deliver sufficient irradiance at 1.245 MHz.


## 2026-08-04 - Pricer PP16 Protocol & Target Analysis

Full report saved at [`docs/research/2026-08-04-pricer-pp16-protocol-analysis.md`](research/2026-08-04-pricer-pp16-protocol-analysis.md).

### Historical findings (compatibility context)
1. The on-air graphic MCU envelope is `34 00 00 00` after the wire PLID and
   before commands `0x05`, `0x20`, and `0x01`.
2. PrecIR's `00 00 00 40` marker belongs to its legacy dongle transport and is
   not direct AirFrame data. It must not be emitted by direct RMT.
3. Barcode `N4163114582613272` maps to wire PLID
   `[0x02, 0xB3, 0xB7, 0x3F]`.

### T008F software profile
The TagTinker type-1327 profile uses two `208 x 112` MSB-first planes
(`5,824` raw bytes, `5,840` padded), `292` indexed `20`-byte packets, page `0`,
and little-endian CRC16 trailers. Its deterministic metadata is
ping/params/data/refresh repeats `81/16/3/21` with a `500 us` gap. These
vectors remain unverified software artifacts and make no physical compatibility
claim. The T008F image profile does not define PP4 or RLE image encoding; the
bridge's separate PP4 waveform path is documented independently.

## 2026-08-08 - T009B TagTinker settle-gap no-reaction retest

### Source and vector comparison

The local clean-room comparison with TagTinker upstream commit
`81adb463eb9918b72a3acaabd5ef452960ba81ce` matches the generated type-1327
AirFrame bytes and the PP4 raw-symbol mapping. This is evidence that the
software vectors and symbol mapping correspond to that upstream reference; it
does not establish carrier, optical, receiver, or ESL compatibility.

### Transmit-scene repair

The transmit scene now preserves the upstream settle requirements in addition
to the per-repeat metadata (`81/16/3/21`, `500 us` gap):

- `50 ms` after ping;
- `50 ms` after parameters;
- `1 ms` after every 32 data frames;
- `50 ms` before refresh.

### No-reaction result

The repaired scene was exercised on 2026-08-08, and the operator observed no
reaction from the target ESL. This is a known operator observation, not a
measurement of carrier frequency, optical power, receiver threshold, or
physical compatibility. No physical compatibility claim is made.

### No-photodiode test matrix

| Check | Evidence available | Result | What remains unknown |
|---|---|---|---|
| Type-1327 AirFrame bytes | Local comparison with upstream commit | Match | None for this software comparison |
| PP4 raw-symbol mapping | Local comparison with upstream commit | Match | None for this software comparison |
| Scene settle timing | Transmit-sequence definition | Repair recorded | Electrical timing at GPIO 44 |
| ESL display reaction | Operator observation | No reaction observed | Receiver response and protocol acceptance |
| Carrier frequency/duty | No photodiode or equivalent instrument | Not measured | Actual carrier waveform |
| Optical emission/power | No photodiode measurement | Not measured | Optical output and receiver irradiance |
| Physical interoperability | No receiver feedback or qualified optical measurement | Not established | Compatibility with any physical ESL |

Distance, alignment, ambient-light conditions, target identity details, serial
port, artifact hash, and raw instrument captures were not recorded for this
retest. They must not be inferred from the no-reaction result.

## 2026-08-08 - PP4 RMT timing and hardware comparison

The PP4 implementation was corrected against the local TagTinker source:
raw-symbol gaps now use `{61, 242, 121, 181}` microseconds and preserve the
64 MHz source-cycle values as rounded 10 MHz RMT ticks
`{605, 2419, 1210, 1814}`. The terminal burst remains mandatory.

The Cardputer-Adv and Flipper output paths are not electrically equivalent:
the Cardputer schematic shows GPIO44 driving its onboard IR LED through a
22-ohm resistor, while the Flipper firmware uses a complementary STM32 TIM1
PWM output with DMA-fed buffers. Carrier frequency, duty at the LED, optical
power, polarity at the emitter, and long-frame refill behavior remain
unmeasured on the Cardputer. See
`docs/research/2026-08-08-cardputer-vs-flipper-ir-output.md`.
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
vectors remain unverified software artifacts; they make no physical
compatibility claim and do not implement PP4 or RLE.
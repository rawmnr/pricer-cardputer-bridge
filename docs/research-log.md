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

### Key Findings:
1. **MCU Subcommand Envelope Prefix Defect:** Stripping `0x34 0x00 0x00 0x00` in bench retest `T007` caused graphic ESL MCU image frames (`0x05`, `0x20`, `0x01`) to be dropped by the target tag. PrecIR source inspection (`tools_python/pr.py`) confirms `make_mcu_frame` requires `0x85 [PLID] 34 00 00 00 [CMD]`.
2. **Target Model & Barcode PLID:** Marking `#19523-01` is a Pricer SmartTAG HD M+ Red ($208 \times 112$ pixels = 23,296 pixels at 110 DPI). Barcode `N4163114582613272` maps to 32-bit PLID `0x3FB7B302`, placed on the wire as bytes `[0x02, 0xB3, 0xB7, 0x3F]` (little-endian SSSSS followed by little-endian MMYWW).
3. **Tricolor Dual-Bitplane Requirement:** The 3-color label requires two bitplane blocks (2,912-byte Black/White plane + 2,912-byte Red mask plane = 5,824 bytes total uncompressed).
4. **Wake-up Duration:** Wake-up frame (`cmd 0x17`) must be transmitted continuously in a loop for up to 4 seconds before sending image frames.
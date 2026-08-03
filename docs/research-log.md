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

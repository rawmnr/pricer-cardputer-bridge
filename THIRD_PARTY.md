# Third-party software and provenance

## PrecIR

- Project: `furrtek/PrecIR`
- Repository: https://github.com/furrtek/PrecIR
- License: GNU GPL version 3
- Role: prior art for Pricer addressing, framing, PP4/PP16 transmission, and image transfer
- Current repository status: **not vendored and no source copied in the initial scaffold**

Before adapting PrecIR code:

1. pin the exact upstream commit;
2. list every copied or adapted source file;
3. retain original copyright and license notices;
4. add a change note and date;
5. update this document and the relevant source headers;
6. verify that the resulting distribution remains GPL-3.0 compliant.

## M5Cardputer library

- Project: `m5stack/M5Cardputer`
- Pinned commit in `firmware/platformio.ini`: `f1392858b9994c3547120e602a57d3553d16ab01`
- Used as a PlatformIO dependency; not vendored.

## Espressif Arduino / ESP-IDF components

Provided through the PlatformIO `espressif32` platform and used under their upstream licenses. The firmware currently targets the RMT API available in the official M5Stack PlatformIO baseline.

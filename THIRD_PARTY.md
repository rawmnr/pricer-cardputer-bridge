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

### T006 timing-data provenance

- Pinned source commit: `b09951e2b3d2741e4ca08f929eafef849f6fc006`
- Source file inspected: `hardware/esl_blaster/FW02/Src/main.c`
- Related timing revision: `a8b79332bab78e7bd144465052c045807adc1f38`
- Additional source: https://www.furrtek.org/index.php?a=esl
- Adaptation: the project reproduces the published 16-entry PP16 nibble-duration table and 21 us burst width as data in `pc/src/eslbridge/pp16.py` and `firmware/include/pp16_encoder.hpp`; no PrecIR source code was copied.
- Change note: added 2026-08-04; values remain provisional for this Cardputer/target-ESL setup pending T005 and physical PP16 validation.

### T008 PrecIR adapter provenance & license audit

- Pinned source commit: `b09951e2b3d2741e4ca08f929eafef849f6fc006`
- Source file inspected: `tools_python/pr.py` (`terminate_frame` / `crc16`)
- Additional source: https://www.furrtek.org/index.php?a=esl
- Upstream repository: https://github.com/furrtek/PrecIR
- License: GNU General Public License v3.0 (GPL-3.0-only)
- Adaptation: clean-room Python adapter implementation (`pc/src/eslbridge/precir.py`) exposing deterministic CRC16 calculation (polynomial 0x8408, init 0x8408 over raw payload), PP16 header placement (`0x00, 0x00, 0x00, 0x40` prefix), little-endian CRC16 trailer placement, frame finalization (`finalize_precir_frame`), and repeat metadata separation helper (`build_pricer_frame_request`). No PrecIR source code was copied or vendored.
- Change note: added 2026-08-04; framing and CRC implementation remain provisional and UNTESTED against physical Pricer ESL target tags in this setup. No claim of tag or physical carrier compatibility is made.

### T008C image packetization provenance

- Pinned source commit: `b09951e2b3d2741e4ca08f929eafef849f6fc006`
- Source file inspected: `tools_python/img2dm.py` (`bytes_per_frame`, `bits_per_frame`, padding, parameter length, and data-frame loop)
- License: GNU General Public License v3.0 (GPL-3.0-only)
- Adaptation: clean-room Python implementation models 20-byte/160-bit image packets, PrecIR's zero-padding rule, padded group length, and indexed packet construction in `pc/src/eslbridge/precir.py` and `scripts/generate_vectors.py`. No PrecIR source code was copied or vendored.
- Change note: added 2026-08-05 for `T008C-r1`; generated vectors remain UNTESTED against the physical target ESL. No claim of tag compatibility, carrier accuracy, or optical power is made.

## PricehaxBT

- Project: `david4599/PricehaxBT`
- Repository: https://github.com/david4599/PricehaxBT
- License: GNU General Public License v3.0
- Pinned source commit: `3043f964595f90fdb6835640275751277523f809`
- Source files inspected: `app/src/app/src/main/java/org/furrtek/pricehaxbt/MainActivity.java`, `PPM.java`, `CRCCalc.java`, and `dongle/v3.2.0/PricehaxBT_IRDongle_prog/PricehaxBT_IRDongle_prog.ino`
- Adaptation: clean-room profile helpers in `pc/src/eslbridge/pricehax.py` and deterministic vector generation in `scripts/generate_vectors.py` reproduce the published type-1327 dimensions, application frame bodies, binary run-length encoding, 40-byte packetization, PP16 header handling, and repeat metadata. No PricehaxBT source was copied or vendored.
- Change note: added 2026-08-05 for `T008D-r1`; all vectors remain unverified against the physical target ESL, and no compatibility claim is made.

## M5Cardputer library

- Project: `m5stack/M5Cardputer`
- Pinned commit in `firmware/platformio.ini`: `f1392858b9994c3547120e602a57d3553d16ab01`
- Used as a PlatformIO dependency; not vendored.

## Espressif Arduino / ESP-IDF components

Provided through the PlatformIO `espressif32` platform and used under their upstream licenses. The firmware currently targets the RMT API available in the official M5Stack PlatformIO baseline.

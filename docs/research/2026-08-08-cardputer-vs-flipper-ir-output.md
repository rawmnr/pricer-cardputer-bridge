# Cardputer-Adv versus Flipper Zero IR output

## Scope

This note compares the Cardputer-Adv output path used by this bridge with the
Flipper/TagTinker PP4 reference. It does not establish physical ESL
compatibility without an electrical or optical capture.

## Verified differences

| Area | Cardputer-Adv bridge | Flipper/TagTinker reference | Evidence |
|---|---|---|---|
| Controller/output | ESP32-S3 RMT channel 0, GPIO 44, one onboard IR emitter | STM32 TIM1 PWM on the internal `gpio_infrared_tx` path; official firmware maps it to PB9 | M5Stack Cardputer-Adv docs and schematic; Flipper `furi_hal_infrared.c` and `furi_hal_resources.c` |
| Cardputer emitter circuit | Official schematic shows GPIO44 directly through IR1 and R14 22 ohm to ground; no transistor is shown in that branch | Flipper firmware uses a complementary TIM1 output and DMA-fed PWM; the exact LED-current topology was not verified from an official schematic here | Official M5Stack schematic; Flipper firmware source |
| Carrier request | 1,254,902 Hz requested; ESP32-S3 APB/RMT integer period produces 1,250,000 Hz at 50% duty | 64 MHz / 51 = 1,254,902 Hz; CCR/ARR is 25/51, approximately 49.02% duty | `pp4_encoder.hpp`; TagTinker `ir/tagtinker_ir.c`; ESP-IDF RMT API |
| Symbol timing | RMT item clock is 10 MHz; corrected implementation uses rounded 64 MHz reference cycles | Busy-waits 64 MHz DWT cycle counts | `ir_transmitter.cpp`; TagTinker `ir/tagtinker_ir.c` |
| Streaming | Legacy RMT item buffer streamed through the ESP32 RMT ISR | Two 200-entry ping-pong DMA buffers with high-priority DMA ISRs | `ir_transmitter.cpp`; Flipper `furi_hal_infrared.c` |
| Mark polarity | RMT high item plus `RMT_CARRIER_LEVEL_HIGH`, idle low | TagTinker enables PWM2 on complementary CH3N and forces inactive for spaces | `ir_transmitter.cpp`; TagTinker `ir/tagtinker_ir.c`; Flipper HAL |

## Decisive protocol correction

The upstream TagTinker gap table is indexed directly by the raw 2-bit symbol:

```text
symbol 0:  3871 cycles ~= 60.484 us
symbol 1: 15483 cycles ~= 241.922 us
symbol 2:  7741 cycles ~= 120.953 us
symbol 3: 11612 cycles ~= 181.438 us
```

The bridge previously used `{61, 243, 122, 182}`, which reversed the timing of
symbols 1 and 3 relative to the upstream table. The corrected bridge uses
`{61, 242, 121, 181}` as metadata and converts the exact reference cycles to
RMT ticks `{605, 2419, 1210, 1814}`. This is a software-level mismatch that
affected every payload byte containing raw symbol 1 or 3.

## Remaining hypotheses

1. The direct Cardputer GPIO44/22-ohm path may have lower loaded current,
   radiant intensity, or edge quality than the Flipper output. A phone camera
   only proves weak optical activity; it cannot verify the 1.25 MHz waveform.
2. The mark polarity may differ electrically between the direct Cardputer path
   and Flipper's complementary output. Do not invert it blindly; compare GPIO44
   and the LED-side waveform with a scope or fast photodiode first.
3. The 0.39% carrier-frequency difference is probably smaller than the unknown
   electrical/optical differences, but it remains unmeasured.
4. ESP32 RMT streaming and Flipper DMA scheduling are different implementations.
   A capture should verify that long 32-byte frames have no refill gap or jitter.
5. The target's type-1327/SmartTAG identity remains a working hypothesis. A
   software match to TagTinker does not prove that this stock Pricer ESL accepts
   the profile.

## Safe next measurement

Use the existing bounded carrier test for a 5 ms burst, then capture GPIO44 and,
if possible, the LED-side optical signal. Keep the firmware's 5 ms carrier-test
limit and GPIO44 default unchanged. If the measured waveform is correct but the
ESL remains unchanged, obtain a known-good Pricer capture or identify the exact
ESL protocol before changing the frame bytes again.

The firmware now explicitly reapplies the legacy RMT GPIO-matrix route to
GPIO44 after M5Cardputer initialization and before installing the RMT driver.
This removes reliance on implicit routing side effects while preserving the
non-inverted, active-high output assumption.

## Sources

- M5Stack Cardputer-Adv official documentation: https://docs.m5stack.com/en/core/Cardputer-Adv
- M5Stack Cardputer-Adv schematic: https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1178/Sch_M5CardputerAdv_v1.0_2025_06_20_17_19_58.pdf
- ESP-IDF RMT reference: https://docs.espressif.com/projects/esp-idf/en/v4.4/esp32s3/api-reference/peripherals/rmt.html
- Flipper official IR HAL: https://raw.githubusercontent.com/flipperdevices/flipperzero-firmware/dev/targets/f7/furi_hal/furi_hal_infrared.c
- Flipper official GPIO resources: https://raw.githubusercontent.com/flipperdevices/flipperzero-firmware/dev/targets/f7/furi_hal/furi_hal_resources.c
- TagTinker reference commit `81adb463eb9918b72a3acaabd5ef452960ba81ce`: https://raw.githubusercontent.com/i12bp8/TagTinker/81adb463eb9918b72a3acaabd5ef452960ba81ce/ir/tagtinker_ir.c

# Cardputer-Adv IR frequency capability

**Date:** 2026-08-05  
**Question:** Is the Cardputer-Adv built-in IR output limited to a kHz carrier, making a Pricer carrier near 1.245 MHz impossible?

## Conclusion

No primary source identifies a fixed kHz hardware limit for the Cardputer-Adv IR emitter. Values such as 38 kHz are consumer-remote protocol/library choices, not a frequency generated or enforced by the LED itself.

The ESP32-S3 RMT peripheral can generate a carrier near 1.25 MHz. The current firmware asks the 80 MHz APB-clocked carrier generator for a 64-clock period: 32 high clocks plus 32 low clocks. That produces a nominal 1.250 MHz carrier, only about +0.40% above 1.245 MHz.

The remaining uncertainty is electrical/optical, not a documented kHz ceiling: the official Cardputer-Adv schematic shows GPIO 44 driving the IR LED directly through a 22 ohm series resistor, with no transistor driver. M5Stack does not identify the LED part or publish its rise time, junction capacitance, radiant intensity at MHz modulation, or the loaded GPIO waveform. Therefore neither adequate 1.25 MHz modulation depth nor adequate optical power is proven without measurement.

## Evidence

### Official Cardputer-Adv hardware

M5Stack documents:

- Cardputer-Adv uses Stamp-S3A / ESP32-S3FN8;
- the board contains one IR emitter;
- IR TX is connected to GPIO 44.

The official schematic, sheet 1, labels the IR branch as:

```text
GPIO44 -> IR1 -> R14 22R/1% -> GND
```

There is no transistor in that branch. This corrects a common assumption based on other IR transmitter boards.

Sources:

- [M5Stack Cardputer-Adv product page and pin map](https://docs.m5stack.com/en/core/Cardputer-Adv)
- [Official Cardputer-Adv schematic, v1.0, 2025-06-20](https://m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1178/Sch_M5CardputerAdv_v1.0_2025_06_20_17_19_58.pdf)

### ESP32-S3 RMT capability

Espressif documents that:

- RMT can generate a carrier modulated by pulse items;
- the normal RMT source is the 80 MHz APB clock;
- the driver accepts carrier frequency/duty settings and exposes carrier high/low clock counts;
- the RMT clock divider controls pulse-item tick duration.

For the carrier itself:

$$
80{,}000{,}000 / 64 = 1{,}250{,}000\ \text{Hz}
$$

For the desired 1.245 MHz carrier:

$$
(1{,}250{,}000 - 1{,}245{,}000) / 1{,}245{,}000 \approx 0.40\%
$$

Source:

- [Espressif ESP-IDF 4.4.8 ESP32-S3 RMT documentation](https://docs.espressif.com/projects/esp-idf/en/v4.4.8/esp32s3/api-reference/peripherals/rmt.html)

### Current bridge configuration

`firmware/src/ir_transmitter.cpp` uses:

- 80 MHz as the APB carrier source;
- a rounded integer carrier period;
- 50% duty cycle;
- `pp16::kPrecirCarrierHz` for PP16 transmission.

At 1.25 MHz, its computed carrier values are 32 high clocks and 32 low clocks. The successful RMT return status proves local completion only; it does not prove the physical GPIO waveform or optical modulation.

## What “kHz IR” likely means

[INFERENCE] References to a Cardputer IR frequency in kHz most likely describe consumer IR protocols, commonly configured around 38 kHz. The M5Stack documentation specifies an emitter and pin but no fixed carrier frequency. A bare LED has no protocol carrier of its own.

This distinction matters:

- **38 kHz software setting:** plausible and changeable;
- **ESP32-S3 RMT upper limit:** not the blocker for 1.25 MHz;
- **onboard LED plus GPIO44 at 1.25 MHz:** undocumented and still unmeasured.

## What can be concluded without a photodiode

A phone camera showing the LED flash proves some IR energy is emitted during the long PP16 sequence. It cannot resolve a 1.25 MHz carrier, measure duty cycle, or show whether the LED turns sufficiently off between approximately 400 ns half-cycles.

No reliable optical-frequency conclusion can be obtained from an ordinary phone camera or 48/96 kHz audio input because both are far below the required sampling bandwidth.

The cheapest useful next measurement does not require a photodiode:

1. use a logic analyzer rated comfortably above 10 MS/s, preferably 24 MS/s or more, or an oscilloscope;
2. measure GPIO 44 during the bounded carrier test;
3. verify an approximately 800 ns period and 50% duty cycle;
4. if GPIO 44 is correct, optical output remains the unresolved variable and requires a fast optical detector or a known-fast external IR LED stage.

Because the schematic drives the LED directly, probing GPIO 44 measures the loaded electrical node. It can reveal whether the GPIO/LED load preserves the requested waveform, although it still cannot prove optical intensity.

## Decision

Do not replace the 1.25 MHz RMT implementation with a 38 kHz carrier based only on descriptions of ordinary Cardputer remote-control use. The current evidence supports keeping T005 open: digital and optical measurements are still required, but the ESP32-S3 RMT peripheral itself is capable of the requested MHz carrier.

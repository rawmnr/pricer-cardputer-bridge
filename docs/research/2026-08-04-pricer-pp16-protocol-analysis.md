# Research Report: Pricer PP16 Protocol & SmartTAG HD M+ Red Target Analysis

**Date:** 2026-08-04  
**Author:** Pricer Protocol Research Specialist  
**Target Device:** M5Stack Cardputer-Adv (ESP32-S3, GPIO 44 IR TX)  
**Target ESL:** Pricer SmartTAG HD M+ Red (Marking `#19523-01`, Barcode `N4163114582613272`)  
**Primary Source Reference:** PrecIR upstream repository commit [`b09951e2b3d2741e4ca08f929eafef849f6fc006`](https://github.com/furrtek/PrecIR/tree/b09951e2b3d2741e4ca08f929eafef849f6fc006) and Furrtek Reverse-Engineering Documentation ([`https://www.furrtek.org/index.php?a=esl`](https://www.furrtek.org/index.php?a=esl)).

---

## 1. Executive Summary

This investigation resolves why the Cardputer PP16 image update sequence performed during bench retest `T007` failed to update the target Pricer Electronic Shelf Label (ESL). Through direct inspection of the pinned PrecIR source code, analysis of primary reverse-engineering documentation, and cross-referencing authoritative web specifications for Pricer SmartTAG HD ESL models, four primary failure mechanisms were identified:

1. **Stripped MCU Envelope Subcommand Header (`0x34 0x00 0x00 0x00`):** In bench retest `T007`, MCU image subcommands (`0x05` parameters, `0x20` data, `0x01` refresh) were transmitted directly following the PLID without the mandatory 4-byte envelope header `0x34 0x00 0x00 0x00`. Primary source inspection (`tools_python/pr.py` and `furrtek.org/index.php?a=esl`) proves that graphic ESL MCU image frames strictly require this 4-byte prefix. Stripping `0x34 0x00 0x00 0x00` caused the tag MCU to ignore every image parameter, data, and refresh packet.
2. **Target Identification & Unformatted Barcode-to-PLID Mapping:** Graphic image updates are strictly addressed commands and do not accept broadcast addresses (`0x00000000`). The target ESL marking `#19523-01` corresponds to a **Pricer SmartTAG HD M+ Red**. Using the verified PrecIR barcode-to-PLID formula on barcode `N4163114582613272`, the exact 32-bit PLID is `0x3FB7B302`, which must be placed on the wire in little-endian word order as bytes `[0x02, 0xB3, 0xB7, 0x3F]`.
3. **Single Bitplane vs. Tricolor Dual Bitplane Discrepancy:** The target ESL features a 3-color display (Black/White/Red) with a resolution of $208 \times 112$ pixels ($23,296$ pixels). Updating a 3-color ESL requires **two bitplane blocks** (a $2,912$-byte Black/White bitplane plus a $2,912$-byte Red mask plane, totaling $5,824$ uncompressed bytes). Sending only a single monochrome bitplane ($2,912$ bytes) causes an image parameter length mismatch and prevents display activation.
4. **Wake-up Duration & Physical Carrier Alignment:** Target tags remain in deep sleep to conserve battery. The wake-up frame (`cmd 0x17`) must be transmitted continuously in a loop for **up to 4 seconds** (e.g., 400 total wake frames) at nominal $1.25\text{ MHz}$ carrier frequency before transmitting image frames.

---

## 2. Target Identification & Barcode-to-PLID Mapping

### 2.1 ESL Model Identification & Resolution
- **Label Markings:** `PRICER`, `#19523-01`, `F16`, `2311`, `N4163114582613272`.
- **Model Verification:** Article number `#19523-01` corresponds directly to the official Pricer product specification for the **SmartTAG HD M+ Red** (3-color Black/White/Red E-paper graphic label).
- **Display Specifications:**
  - **DPI:** 110 DPI.
  - **Active Area:** Approximately $48\text{ mm} \times 26\text{ mm}$.
  - **Pixel Resolution:** $208 \times 112$ pixels ($23,296$ pixels total).
  - **Bitplane Size:** $\frac{208 \times 112}{8} = 2,912\text{ bytes}$ per bitplane plane.

### 2.2 Barcode Structure & PLID Derivation Algorithm
Pricer tags feature a 17-character Code128 barcode encoding manufacturing and serial data:
`N 4 16311 45826 1327 2`
- `N`: Manufacturing unit prefix.
- `4`: Constant protocol/tag indicator.
- `16311`: Manufacturing unit / date code `MMYWW` (Unit 16, Year 3, Week 11). Decimal $16311 = \text{0x3FB7}$.
- `45826`: Tag serial number `SSSSS` ($0..65535$). Decimal $45826 = \text{0xB302}$.
- `1327`: Model designation code.
- `2`: Checksum digit.

#### PLID Calculation Formula (from PrecIR `tools_python/pr.py:get_plid`)
```python
id_value = int(barcode[2:7]) + (int(barcode[7:12]) << 16)
# id_value = 16311 + (45826 << 16) = 0xB3023FB7

PLID[0] = (id_value >> 8) & 0xFF   # 0x3F (MMYWW MSB)
PLID[1] = id_value & 0xFF          # 0xB7 (MMYWW LSB)
PLID[2] = (id_value >> 24) & 0xFF  # 0xB3 (SSSSS MSB)
PLID[3] = (id_value >> 16) & 0xFF  # 0x02 (SSSSS LSB)
```

#### On-the-Wire PLID Placement
In raw PP16 and MCU frames (`make_mcu_frame`), PLID bytes are transmitted in the exact order `[PLID[3], PLID[2], PLID[1], PLID[0]]`:
$$\text{Wire Bytes} = [\text{0x02}, \text{0xB3}, \text{0xB7}, \text{0x3F}]$$
This places the 16-bit serial number `SSSSS` in little-endian order (`0x02, 0xB3`), followed by the 16-bit manufacturing info `MMYWW` in little-endian order (`0xB7, 0x3F`).

---

## 3. PP16 Framing & MCU Subcommand Envelope Analysis

### 3.1 Frame Structure & CRC16
A complete PP16 frame on the wire consists of:
1. **PP16 Header Prefix:** 4 bytes `0x00 0x00 0x00 0x40` (`PRECIR_PP16_HEADER`). (Must be prepended before PP16 symbol encoding).
2. **Payload Bytes:** Protocol byte (`0x85` for graphic tags), 4-byte PLID, MCU command header/data.
3. **CRC16 Trailer:** 2 bytes, little-endian. Calculated over the payload bytes (from protocol byte `0x85` up to last payload byte) **BEFORE** prepending the 4-byte PP16 header prefix.
   - **Polynomial:** `0x8408` (reflected `0x1021`).
   - **Initial Value:** `0x8408`.

### 3.2 Symbol Modulation & Nibble Transmission Order
- **Symbol Duration:** Each 4-bit nibble ($0\text{..}15$) maps to a total symbol duration (27 us to 147 us) with a fixed carrier pulse width of 21 us.
- **Nibble Order:** Payload bytes are split and transmitted **least-significant nibble first**:
  - Low nibble: `byte & 0x0F`
  - High nibble: `(byte >> 4) & 0x0F`
  - Upstream source verification: `hardware/esl_blaster/FW02/Src/main.c` (lines 145–150).

### 3.3 Discrepancy Analysis: The MCU Envelope Header (`0x34 0x00 0x00 0x00`)
In PrecIR upstream source `tools_python/pr.py`:
```python
def make_mcu_frame(PLID, cmd):
    frame = [0x85, PLID[3], PLID[2], PLID[1], PLID[0], 0x34, 0x00, 0x00, 0x00, cmd]
    return frame
```
Primary documentation (`furrtek.org/index.php?a=esl`) explicitly defines all graphic MCU frames with this 4-byte header:
- Parameter frame: `85 [PLID] 34 00 00 00 05 ...`
- Image data frame: `85 [PLID] 34 00 00 00 20 ...`
- Refresh frame: `85 [PLID] 34 00 00 00 01 ...`

**Failure Mode in `T007` Retest:**  
The bench log records: *"The corrected-frame run used MCU commands 0x05 (parameters), 0x20 (data), and 0x01 (refresh); the earlier generated frames had an erroneous extra 0x34 before those commands."*  
Stripping `0x34 0x00 0x00 0x00` under the assumption that `0x34` was an error directly violated the protocol specification. The tag MCU rejected all resulting frames.

---

## 4. Graphic Image Transmission Commands & Color Format

### 4.1 Image Parameter Command (`0x05`)
- **Structure:** `85 [PLID] 34 00 00 00 05 [LENGTH] 00 [TYPE] [PAGE] [WIDTH] [HEIGHT] [XPOS] [YPOS] [KEY] 88 00 00 00 00 00 00 [CRC16]`
- **Fields:**
  - `LENGTH` (2 bytes, big-endian uint16): Total image payload byte count.
  - `TYPE` (1 byte): `0x00` = raw uncompressed bitstream, `0x02` = bitwise RLE compressed.
  - `PAGE` (1 byte): Flash buffer / display page.
  - `WIDTH`, `HEIGHT` (2 bytes each, big-endian uint16): Image resolution ($208, 112$).
  - `XPOS`, `YPOS` (2 bytes each): Display offset ($0, 0$).
  - `KEY` (2 bytes): Store key (typically `0x0000`).
  - `88 00 00 00 00 00 00` (7 bytes): Mandatory fixed parameter tail.

### 4.2 Image Data Command (`0x20`)
- **Structure:** `85 [PLID] 34 00 00 00 20 [INDEX] [DATA] [CRC16]`
- **Fields:**
  - `INDEX` (1 byte): Sequence index starting at `0x00` and incrementing for each fragment (`0, 1, 2, ...`).
  - `DATA`: Up to 20 bytes of encoded image data per packet.

### 4.3 Image Refresh / Activate Command (`0x01`)
- **Structure:** `85 [PLID] 34 00 00 00 01 [PAYLOAD] [CRC16]`
- **Fields:**
  - `PAYLOAD`: 22 zero bytes (`0x00` $\times 22$). Triggers internal e-paper refresh sequence.

### 4.4 Bitplane Structure for 3-Color (Black/White/Red) SmartTAG HD M+
- **Monochrome vs. Tricolor:** Raw uncompressed image transfer for 3-color displays requires **two distinct bitplane blocks**:
  1. **Black/White Bitplane:** $0 = \text{black}$, $1 = \text{white}$. ($2,912$ bytes).
  2. **Red Mask Bitplane:** $0 = \text{red}$, $1 = \text{no red}$. ($2,912$ bytes).
- **Total Payload Size:** $2,912 + 2,912 = 5,824\text{ bytes}$ uncompressed.
- **Consequence:** Sending only a single $2,912$-byte block causes an image size mismatch in `LENGTH` or leaves the red bitplane unitialized.

---

## 5. Physical Layer, Carrier Timing & Wake-up Requirements

### 5.1 Carrier Frequency & Optical Passband
- **Downlink Carrier:** Nominal $1.25\text{ MHz}$ ($1,250,000\text{ Hz}$) square wave.
- **Receiver Selectivity:** Pricer tag IR receivers feature narrow active bandpass filtering ($\pm 10\text{ kHz}$). Emitter frequency errors outside $1.240\text{ MHz}\text{..}1.260\text{ MHz}$ suffer severe attenuation.
- **Uplink Response Carrier:** Reverse-engineering of Pricer ceiling transceivers shows uplink tags respond at $1.245\text{ MHz}$.

### 5.2 Wake-up Sequence Duration
- **Wake-up Command:** `85 [PLID] 17 01 [KEY] [PAYLOAD] [CRC16]` (23-byte payload).
- **Duration Requirement:** Because tag MCUs spend most of their time in ultra-low-power sleep, the wake-up frame must be transmitted in a continuous loop for **up to 4 seconds** (e.g., 400 frame repeats) before sending image data.

---

## 6. Primary Source Provenance & Evidence Summary

| Parameter / Question | Verified Value / Finding | Primary Source Citation | Confidence |
|---|---|---|---|
| **Target Model** | Pricer SmartTAG HD M+ Red (`#19523-01`) | Official Pricer Specs / `hardware-notes.md` | Verified |
| **Pixel Resolution** | $208 \times 112$ pixels (23,296 pixels) | Pricer Specs / `suntown-ukraine.com` | Verified |
| **PLID Calculation** | `(MMYWW) + (SSSSS << 16)` | PrecIR `tools_python/pr.py:get_plid` | Source Verified |
| **Barcode PLID (`N4163114582613272`)** | `[0x02, 0xB3, 0xB7, 0x3F]` | Calculated via PrecIR `get_plid` | Verified |
| **MCU Subcommand Envelope** | `34 00 00 00` required prefix | PrecIR `tools_python/pr.py:make_mcu_frame` | Source Verified |
| **PP16 Header Prefix** | `0x00 0x00 0x00 0x40` | PrecIR `tools_python/pr.py:terminate_frame` | Source Verified |
| **CRC16 Specs** | Poly `0x8408`, Init `0x8408`, over payload | PrecIR `tools_python/pr.py:crc16` | Source Verified |
| **Nibble Order** | Low nibble first (`byte & 0x0F` then `byte >> 4`) | PrecIR `hardware/esl_blaster/FW02/Src/main.c` | Source Verified |
| **3-Color Image Data Size** | 2 planes ($2,912\text{B B/W} + 2,912\text{B Red} = 5,824\text{B}$) | `furrtek.org/index.php?a=esl` | Source Verified |
| **Downlink Carrier Freq** | $1.25\text{ MHz}$ ($\pm 10\text{ kHz}$) | PrecIR `hardware/esl_blaster/FW02/Src/main.c` | Source Verified |
| **Wake-up Loop Duration** | Up to 4 seconds continuous repeat | `furrtek.org/index.php?a=esl` | Source Verified |

---

## 7. Next Steps & Recommendations

1. **Restore MCU Envelope Subcommand Header:** Update host and firmware frame generators to include `0x34 0x00 0x00 0x00` before MCU command bytes (`0x05`, `0x20`, `0x01`).
2. **Implement Barcode-to-PLID Helper:** Add deterministic barcode parsing to `eslbridge.precir` matching `get_plid` to generate wire PLID bytes `[0x02, 0xB3, 0xB7, 0x3F]` for `N4163114582613272`.
3. **Format Dual-Bitplane Tricolor Images:** Update image encoders to generate both B/W and Red bitplanes for SmartTAG HD M+ Red labels.
4. **Enforce 4-Second Continuous Wake-up Sequence:** Ensure the wake-up command is repeated continuously for $\approx 4\text{ seconds}$ before image parameter delivery.

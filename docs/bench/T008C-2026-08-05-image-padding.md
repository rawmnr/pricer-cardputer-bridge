# Bench record: T008C PrecIR image-data padding

- Date: 2026-08-05
- Operator: repository owner, assisted remotely
- Hardware activity: none; corrected firmware not yet installed or physically tested
- Target marking: `#19523-01`
- Target barcode: `N4163114582613272`
- Source provenance: clean-room implementation of PrecIR commit `b09951e2b3d2741e4ca08f929eafef849f6fc006`, `tools_python/img2dm.py`
- Profile revision: `T008C-r1`

## Correction evidence

Pinned PrecIR models each image-data packet as 20 bytes (160 bits) and pads
encoded image data to a complete packet before calculating the image-group
length. The retained 8 × 8 two-plane raw image contains 128 bits (16 bytes), so
T008C appends 32 zero bits (4 bytes). The parameter group length is therefore
`0x0014`, and the `0x20` body contains its two-byte packet index followed by
exactly 20 image bytes.

| Vector | Command | Length | CRC16 little-endian |
|---|---:|---:|---|
| `wake.bin` | `0x17` raw | 38 bytes | `f1c3` |
| `params-8x8-color.bin` | `0x05` MCU | 38 bytes | `789a` |
| `data-8x8-color.bin` | `0x20` MCU | 38 bytes | `f280` |
| `refresh.bin` | `0x01` MCU | 38 bytes | `8c01` |

Corrected parameter frame:

```text
000000408502b3b73f340000000500140000010008000800000000000088000000000000789a
```

Corrected data frame:

```text
000000408502b3b73f34000000200000f00ff00ff00ff00ff00ff00ff00ff00f00000000f280
```

`scripts/generate_vectors.py` now derives zero padding, parameter length, and
packet contents. Retained binaries, manifest metadata, CRCs, and firmware arrays
are generated from those values and checked against the explicit vectors above.

## Physical retest

Not performed. Install an application-only M5Launcher artifact whose probe and
ready screen report `T008C-r1`, record its Git SHA and SHA-256, then press key
`1` once. Until that test is recorded, no claim is made about ESL compatibility,
carrier accuracy, or optical power. The negative T008B-r1 result cannot isolate
T005 because its image-data packet was incomplete.

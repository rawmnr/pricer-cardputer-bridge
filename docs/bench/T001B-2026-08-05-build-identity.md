# Bench record: T001B exact build identity

- Date/time: 2026-08-05T12:29:02+02:00 (operator-local clock)
- Operator: repository owner, assisted remotely
- Repository commit: `9231bad`
- Firmware version: `0.1.0`
- Cardputer hardware: M5Stack Cardputer-Adv, SKU K132-Adv
- M5Launcher version: `2.6.9`
- Install route: M5Launcher SD application selection
- Candidate artifact: `pricer-cardputer-bridge-cardputer-adv-9231bad.bin`
- Candidate size: `475088` bytes
- Candidate SHA-256: `164AEE98473FBCEF6C789E3E1423FA8489E3E99F9157832894279AAE306046D7`

## Procedure and observations

1. Built the application-only PlatformIO artifact after commit `9231bad`.
2. Copied the candidate to the mounted `CARDPUTER` SD volume.
3. Selected and launched that exact filename through M5Launcher.
4. Cardputer UI showed Git SHA `9231bad` and PP16 profile `T006B-r1`.
5. After USB CDC re-enumeration, `eslbridge probe --port COM3` returned:
   - firmware `0.1.0`;
   - Git SHA `9231bad`;
   - build provenance `clean`;
   - PP16 profile `T006B-r1`;
   - capabilities `0x0000000D`;
   - max payload `4096`;
   - IR GPIO `44`.
6. Reset returned the Cardputer to M5Launcher before the final artifact installation, preserving the normal recovery path.

## Evidence limits

The first probe attempt before USB re-enumeration found no serial port. Reconnecting the USB-C data cable restored COM3. No full-flash operation, partition-table change, OTA metadata change, or NVS erase was performed. This record proves selected-artifact identity and HELLO identity, not physical IR or ESL compatibility.

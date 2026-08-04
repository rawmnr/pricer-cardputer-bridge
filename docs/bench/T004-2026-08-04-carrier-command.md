# Bench record: T004 bounded carrier command

- Date/time: 2026-08-04; exact local time not recorded
- Operator: repository owner, assisted remotely
- Repository commit: `ea1d868` plus uncommitted T004 source changes represented by the candidate artifact hash below
- Firmware version reported by installed application: `0.1.0`
- Host package version: `0.1.0`
- Cardputer hardware: M5Stack Cardputer-Adv, SKU K132-Adv; exact board revision not recorded
- M5Launcher version: `2.6.9`
- ESL markings/identifier: not applicable; no ESL transmission attempted
- Power state/battery notes: USB connected; battery state not recorded

## Objective

Exercise the bounded `CARRIER_TEST` command on the connected Cardputer-Adv and retain the candidate T004 application artifact. This record does not measure the IR waveform and does not claim that the candidate artifact ran on hardware.

## Equipment

- M5Stack Cardputer-Adv, SKU K132-Adv, running the previously installed M5Launcher application artifact
- Windows 11 host
- USB-C data cable
- No oscilloscope, logic analyzer, or photodiode was used

## Setup

- Installed application port: `COM3`
- Installed application artifact: `pricer-cardputer-bridge-cardputer-adv-hwcdc.bin`
- Installed artifact SHA-256: `71127BC866F235F7D4B432336E8847F6053548BF52BEE71EB2268DF55FAE3D91`
- Candidate T004 artifact: `pricer-cardputer-bridge-cardputer-adv-t004-60ad2eea.bin`
- Candidate artifact size: 473,696 bytes
- Candidate artifact SHA-256: `60AD2EEAFD5FF9C08C0518A508338B4348A5C9997A13E8EF8346D2A92DF354BB`
- Candidate artifact location: `C:\Users\rom1m\Downloads\pricer-cardputer-bridge-cardputer-adv-t004-60ad2eea.bin`
- Candidate artifact installation state: not installed or launched
- Distance, alignment, ambient light: not applicable; optical output was not observed

## Command/input

```text
uv run --frozen --project pc eslbridge carrier-test --port COM3 --duration-us 2000
uv run --frozen --project pc eslbridge carrier-test --port COM3 --duration-us 5000
```

Both requests used the provisional defaults of 1,245,000 Hz and 50% duty.

## Expected result

- The installed application accepts a 2,000 us request and a maximum-boundary 5,000 us request.
- Each command returns a local structured success or a precise failure.
- No continuous-carrier command or ESL frame transmission occurs.
- The candidate T004 artifact remains an application-only M5Launcher binary.

## Observed result

- The 2,000 us command returned local success.
- An immediate attempt to reopen `COM3` for the 5,000 us command raced a transient COM-port disappearance and failed with `FileNotFoundError`.
- After `COM3` reappeared, the 5,000 us command returned local success.
- No optical emission, carrier frequency, duty cycle, exact burst duration, GPIO voltage, or ESL response was measured.
- The commands ran against the previously installed artifact, not the candidate T004 artifact containing exact envelope accounting and a bounded RMT completion wait.
- No direct PlatformIO upload, full-flash erase, PP16 command, or ESL transmission was performed.

## Measurements

| Quantity | Requested | Observed | Evidence limit |
|---|---:|---:|---|
| Carrier command duration | 2,000 us | local `OK` | installed firmware status only; waveform not measured |
| Carrier command duration | 5,000 us | local `OK` after port reappeared | installed firmware status only; waveform not measured |
| Candidate application size | non-empty | 473,696 bytes | exact file length |
| Candidate SHA-256 | recorded | `60AD2EEA...354BB` | exact file hash |

## Artifacts

- Candidate application binary: `C:\Users\rom1m\Downloads\pricer-cardputer-bridge-cardputer-adv-t004-60ad2eea.bin`
- Raw waveform capture: none
- Photo/video: none retained
- Host log: interactive command output summarized above

## Conclusion

The connected, previously installed bridge accepted bounded 2,000 us and 5,000 us carrier-test commands and returned local success. The candidate T004 application binary was built and retained, but it was not installed; therefore this record does not validate its corrected exact-duration plan or bounded RMT wait on hardware. Frequency, duty cycle, timing, idle level, and optical output remain unmeasured. M5Launcher installation of the candidate artifact and physical waveform measurement remain required before promoting those properties from software invariants to hardware facts.

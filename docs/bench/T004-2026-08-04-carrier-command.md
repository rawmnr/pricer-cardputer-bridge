# Bench record: T004 bounded carrier command

- Date/time: 2026-08-04; exact local time not recorded
- Operator: repository owner, assisted remotely
- Repository commit: `058df82549dd91f24018e654500c68434dd855c9`
- Firmware version reported by installed application: `0.1.0`
- Host package version: `0.1.0`
- Cardputer hardware: M5Stack Cardputer-Adv, SKU K132-Adv; exact board revision not recorded
- M5Launcher version: `2.6.9`
- ESL markings/identifier: not applicable; no ESL transmission attempted
- Power state/battery notes: USB connected; battery state not recorded

## Objective

Exercise the bounded `CARRIER_TEST` command on the connected Cardputer-Adv after installing the T004 application artifact through M5Launcher. This record does not measure the IR waveform.

## Equipment

- M5Stack Cardputer-Adv, SKU K132-Adv, running the T004 M5Launcher application artifact
- Windows 11 host
- USB-C data cable
- No oscilloscope, logic analyzer, or photodiode was used

## Setup

- Installed application port: `COM3`
- Installed application artifact: `pricer-cardputer-bridge-cardputer-adv-t004-60ad2eea.bin`
- Installed artifact size: 473,696 bytes
- Installed artifact SHA-256: `60AD2EEAFD5FF9C08C0518A508338B4348A5C9997A13E8EF8346D2A92DF354BB`
- Source artifact location: `C:\Users\rom1m\Downloads\pricer-cardputer-bridge-cardputer-adv-t004-60ad2eea.bin`
- M5Launcher source location: `E:\pricer-cardputer-bridge-cardputer-adv-t004-60ad2eea.bin`
- Installation state: operator reported installation and launch through the M5Launcher SD browser
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

- An automatic `HELLO` probe succeeded on `COM3` after the operator installed and launched the T004 artifact.
- The probe reported protocol 1, firmware 0.1.0, capabilities `0x00000009`, maximum payload 4096, and IR GPIO 44.
- The 2,000 us and maximum-boundary 5,000 us commands both returned local success without a port-open retry.
- No optical emission, carrier frequency, duty cycle, exact burst duration, GPIO voltage, or ESL response was measured.
- No direct PlatformIO upload, full-flash erase, PP16 command, or ESL transmission was performed.

## Measurements

| Quantity | Requested | Observed | Evidence limit |
|---|---:|---:|---|
| Carrier command duration | 2,000 us | local `OK` | installed T004 firmware status only; waveform not measured |
| Carrier command duration | 5,000 us | local `OK` | installed T004 firmware status only; waveform not measured |
| Installed application size | non-empty | 473,696 bytes | exact source file length |
| Installed artifact SHA-256 | recorded | `60AD2EEA...354BB` | exact source and SD-copy hash; installation reported by operator |

## Artifacts

- Installed application binary source: `C:\Users\rom1m\Downloads\pricer-cardputer-bridge-cardputer-adv-t004-60ad2eea.bin`
- Raw waveform capture: none
- Photo/video: none retained
- Host log: interactive command output summarized above

## Conclusion

The operator installed and launched the T004 application through M5Launcher. The application answered `HELLO` and completed bounded 2,000 us and 5,000 us carrier-test commands locally. This validates the installation and command-execution path for the recorded artifact, including the maximum accepted duration. Frequency, duty cycle, exact timing, idle level, and optical output remain unmeasured and are deferred to T005; local `OK` responses do not prove the physical waveform.

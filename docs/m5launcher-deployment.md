# M5Launcher deployment

## Decision

M5Launcher remains installed on the Cardputer-Adv and is the primary installer and application launcher for this project.

The bridge is distributed as a normal ESP32-S3 **application-only binary** produced by PlatformIO:

```text
firmware/.pio/build/m5stack-cardputer-adv/firmware.bin
```

M5Launcher supports installing normal application binaries produced by Arduino, PlatformIO, or ESP-IDF from its SD browser or WebUI OTA interface. It manages application partitions and can keep Launcher available for later app selection and maintenance.

Primary upstream references:

- https://github.com/bmorcelli/Launcher
- https://github.com/bmorcelli/Launcher/wiki/Explaining-the-project
- https://docs.m5stack.com/en/guide/restore_factory/cardputer_adv

## Supported project workflow

### 1. Build

```powershell
pio run -d .\firmware
```

Expected output:

```text
firmware\.pio\build\m5stack-cardputer-adv\firmware.bin
```

### 2. Sanity-check the artifact

The file must:

- exist and be non-empty;
- be produced by the `m5stack-cardputer-adv` PlatformIO environment;
- begin with the normal ESP image magic byte `0xE9`;
- be identified as an application binary, not a full-flash dump.

Optional PowerShell check:

```powershell
$path = '.\firmware\.pio\build\m5stack-cardputer-adv\firmware.bin'
$bytes = [System.IO.File]::ReadAllBytes($path)
if ($bytes.Length -eq 0 -or $bytes[0] -ne 0xE9) {
    throw 'Not a valid non-empty ESP application image'
}
Get-FileHash $path -Algorithm SHA256
```

### 3A. Install through microSD

1. Copy the `.bin` to the Cardputer microSD card.
2. Boot into M5Launcher.
3. Open `SD`.
4. Select the binary.
5. Choose the install action.
6. Launch the installed bridge application.

M5Launcher recommends an SDHC card up to 32 GB, FAT32, with an MBR partition layout.

### 3B. Install through WebUI

1. Boot into M5Launcher.
2. Start `WUI`.
3. Connect the Windows machine to the indicated network/interface.
4. Open the Launcher WebUI.
5. Upload the application binary.
6. Install it using the OTA option.
7. Launch the bridge application.

Do not expose the Launcher WebUI to an untrusted network. Change default Launcher credentials if the device is used beyond an isolated bench network.

## Boot and USB behavior

Launcher and the bridge application are distinct USB runtimes. Starting the application may cause Windows to remove one COM device and enumerate another. The host tooling must not assume that the Launcher COM number remains valid.

Automatic discovery workflow:

```powershell
# Run after the bridge application has booted (auto-discovers sole Cardputer bridge)
uv run --project .\pc eslbridge probe

# Or pass explicit port if multiple serial devices exist
uv run --project .\pc eslbridge probe --port COM7
```

Host tooling supports bounded auto-discovery and retry after application boot via `discover_bridge` and `eslbridge probe`. When `--port` is omitted, discovery polls candidate serial ports, validates HELLO protocol identity, and retries up to `--timeout` seconds (default 3.0s) for single candidate or transient timeout cases. If zero ports are found within the timeout window, discovery fails with `MissingPortError`. If multiple candidate serial ports are detected, discovery immediately rejects the ambiguity with `MultiplePortsError`, reporting candidate port names and advising the user to pass `--port <PORT>`. Direct `--port` targeting remains supported and validates HELLO identity on the specified port.

## Returning to Launcher

During development, configure Launcher to make the Launcher menu easy to reach on reboot. A deployment test is incomplete until the bridge application has booted and a subsequent restart proves that Launcher is still accessible.

The bridge application must not:

- rewrite the partition table;
- modify Launcher application metadata;
- erase OTA metadata;
- erase all NVS;
- assume ownership of the entire flash;
- initiate a full-chip erase.

## CI artifact convention

CI stages the normal PlatformIO application binary as:

```text
pricer-cardputer-bridge-cardputer-adv-<short-sha>.bin
```

The GitHub Actions artifact name includes the full commit SHA. The artifact description and README must consistently state that this is an M5Launcher-installable application binary, not a full-flash image.

Automatic tagged releases are deferred until:

- version injection is deterministic;
- T001A proves install, boot, USB enumeration, and return to Launcher;
- the binary naming/version policy is accepted.

## Direct flashing policy

The following is not part of the normal workflow:

```powershell
pio run -d .\firmware -t upload
```

Direct bootloader upload may be used only by an explicit low-level debugging or recovery task that explains the consequences. Never run `erase_flash` as a routine step.

## Recovery

If Launcher or the flash layout is damaged:

1. power the Cardputer-Adv off;
2. hold `G0` while powering it on to enter download mode;
3. connect it to Windows over USB;
4. use M5Burner and the official Cardputer-Adv restore procedure;
5. reinstall M5Launcher if it was the desired previous environment.

Recovery is a fallback. It is not evidence that the application deployment path works correctly.

## Dependency pins and update policy

### Python host environment (`pc/`)
- Dependencies are declared in `pc/pyproject.toml` targeting Python 3.12+.
- Committed lockfile `pc/uv.lock` is generated via `uv lock --project pc` and verified in CI using `uv sync --project pc --all-groups --frozen`.
- **Update Policy:** Changes to host dependencies must be declared in `pc/pyproject.toml` and locked into `pc/uv.lock`. Pull requests and CI runs must use `--frozen` sync to prevent unexpected dependency drift.

### PlatformIO firmware environment (`firmware/`)
- Built using PlatformIO environment `m5stack-cardputer-adv`.
- Core toolchain platform is pinned in `firmware/platformio.ini`: `espressif32@6.7.0`.
- External libraries are pinned to explicit git commit hashes (e.g. `M5Cardputer=https://github.com/m5stack/M5Cardputer.git#f1392858b9994c3547120e602a57d3553d16ab01`).
- **Update Policy:** Firmware dependencies must be pinned to explicit tags or git commit SHAs in `platformio.ini`. Unpinned library versions or unpinned platforms are prohibited.

# T001A - M5Launcher deployment validation

## Objective

Prove that the project can be installed and run as a normal application through M5Launcher on the Cardputer-Adv without replacing Launcher or reflashing the complete device.

## Depends on

T001.

## Work

- record the exact Cardputer-Adv and M5Launcher versions;
- download the CI artifact or build the application locally;
- record binary filename, size, SHA-256, and first-byte sanity check;
- install through the M5Launcher SD browser or WebUI OTA path;
- boot the bridge application;
- observe the display and USB CDC enumeration;
- reboot and verify that Launcher remains available;
- document any partition prompt or automatic partition-manager action;
- verify that firmware source contains no partition-table writes, full NVS erase, or full-flash assumptions;
- document the M5Burner recovery procedure as a fallback only.

## Bench record

Use `docs/bench-template.md` and include:

- Launcher version;
- install route: SD or WebUI;
- microSD format/details if used;
- binary SHA-256 and size;
- COM port before launching the app;
- COM port after launching the app;
- boot and return-to-Launcher result;
- photos or video references where useful.

## Acceptance

See `docs/backlog.md#t001a---m5launcher-deployment-validation`.

## Non-goals

- no Pricer IR transmission;
- no PP16 implementation;
- no automatic tagged release;
- no requirement to test every M5Launcher partition layout.

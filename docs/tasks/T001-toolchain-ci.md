# T001 - Reproducible toolchain, CI, and application artifact

## Objective

Make a fresh Windows checkout and GitHub Actions run the same static checks, tests, and firmware build, then expose the resulting application-only binary as a clearly named CI artifact for M5Launcher.

## Work

- verify Python 3.12 dependency resolution with uv;
- create and commit `uv.lock`;
- pin or document all PlatformIO dependencies;
- make `scripts/bootstrap.ps1` idempotent;
- validate CI cache keys;
- build `firmware/.pio/build/m5stack-cardputer-adv/firmware.bin`;
- verify the output is non-empty and starts with the ESP application image magic byte;
- stage it as `pricer-cardputer-bridge-cardputer-adv-<short-sha>.bin`;
- upload the staged `.bin` using GitHub Actions artifacts;
- document that direct PlatformIO upload is not the primary deployment path.

## Non-goals

- no PP16 implementation;
- no image pipeline;
- no GUI;
- no automatic tagged GitHub Release yet;
- no full-flash or merged image generation;
- no claim that M5Launcher installation is validated until T001A is complete.

## Acceptance

See `docs/backlog.md#t001---reproducible-toolchain-ci-and-application-artifact`.

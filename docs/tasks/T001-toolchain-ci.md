# T001 - Reproducible toolchain and CI

## Objective

Make a fresh Windows checkout and GitHub Actions run the same static checks, tests, and firmware build.

## Work

- verify Python 3.12 dependency resolution with uv;
- create and commit `uv.lock`;
- pin or document all PlatformIO dependencies;
- make `scripts/bootstrap.ps1` idempotent;
- validate CI cache keys;
- document any Windows driver/manual upload prerequisite.

## Non-goals

- no PP16 implementation;
- no image pipeline;
- no GUI.

## Acceptance

See `docs/backlog.md#t001---reproducible-toolchain-and-ci`.

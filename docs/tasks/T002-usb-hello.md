# T002 - USB HELLO/probe round trip

## Objective

Prove the Windows host can identify the Cardputer bridge over USB after M5Launcher installs and starts the application, using the versioned binary protocol.

## Depends on

T001 and T001A.

## Work

- complete firmware stream parser and HELLO response;
- report firmware version, protocol version, max payload, GPIO, and capabilities;
- handle USB CDC disconnection and re-enumeration when Launcher starts the bridge application;
- add bounded port discovery/retry behavior with explicit timeouts;
- distinguish port missing, multiple candidates, access denied, timeout, wrong protocol, and CRC failure;
- add fake-serial host tests for round trip, retry, and failure behavior;
- add a bench record from the real Cardputer with Launcher/app COM-port observations.

## Acceptance

See `docs/backlog.md#t002---usb-helloprobe-round-trip`.

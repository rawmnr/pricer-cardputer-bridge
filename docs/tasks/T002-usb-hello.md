# T002 - USB HELLO/probe round trip

## Objective

Prove the Windows host can identify the Cardputer bridge over a selected COM port using the versioned binary protocol.

## Work

- complete firmware stream parser and HELLO response;
- add fake-serial host tests;
- report firmware version, protocol version, max payload, GPIO, and capabilities;
- distinguish port missing, access denied, timeout, wrong protocol, and CRC failure;
- add a bench record from the real Cardputer.

## Acceptance

See `docs/backlog.md#t002---usb-helloprobe-round-trip`.

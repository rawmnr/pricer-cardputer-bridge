# T004 - Bounded carrier test

## Objective

Generate a short, safe, measurable carrier burst on GPIO 44 through RMT.

## Work

- implement `IrTransmitter::carrier_test` using the RMT API available in the pinned platform;
- validate frequency, duty, and duration ranges;
- split durations into legal RMT item sizes if required;
- return hardware-specific errors;
- display TX state without blocking the timing path;
- create a real bench record.

## Guardrails

- maximum 5,000 us per command;
- no loop/continuous mode;
- idle output low;
- default 1,245,000 Hz, 50%, 2,000 us is provisional.

## Acceptance

See `docs/backlog.md#t004---bounded-carrier-test`.

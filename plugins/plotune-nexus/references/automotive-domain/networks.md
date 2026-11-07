# Automotive Network Artifacts

Use this reference for offline CAN, DBC, LIN, and trace analysis. For live capture or transmit, use Nexus CAN workflows.

## DBC Review Points

- Frame ID width: distinguish 11-bit and 29-bit IDs.
- DLC and CAN FD: check data length assumptions before using classic CAN tooling.
- Signals: verify start bit, length, byte order, signedness, factor, offset, minimum, maximum, and unit.
- Multiplexing: identify multiplexer signals and conditional payload layouts before decoding.
- Naming: flag duplicated frame IDs, duplicated signal names, vague units, and missing receivers.
- Cycle time: compare declared cycle times with trace timing when traces are available.

## Trace Review Points

- Confirm timestamp origin and units before calculating periods.
- Preserve malformed or unsupported lines as evidence; do not silently treat them as absent traffic.
- Report unknown IDs separately from decoded signals.
- Treat remote frames, error frames, CAN FD frames, and channel labels as context that may affect interpretation.
- Use payload changes and timing jitter as clues, not root-cause proof.

## Script Helpers

Run from the plugin package root when script execution is allowed:

- `python3 scripts/automotive/dbc_sanity.py --dbc network.dbc --format json`
- `python3 scripts/automotive/can_trace_summarize.py --trace trace.log --dbc network.dbc --format json`

If command execution is restricted, do not bypass it. Review snippets manually and state that deterministic script checks were not run.

## Nexus Handoff

Use `plotune-can-workflows` when the user wants live observation, waits, periodic frames, DBC message sends, captures, or recordings. Active transmit requires exact payloads, DBC-backed commands, or an approved runbook.

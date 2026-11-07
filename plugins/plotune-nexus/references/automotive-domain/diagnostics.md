# Automotive Diagnostics Planning

Use this reference for offline diagnostic design, payload review, DTC/DID reasoning, and report planning. For live UDS or DoIP, use Nexus diagnostics workflows.

## Offline Inputs

- UDS request and response hex
- DTC reports and status bytes
- DID and RoutineControl lists
- ODX/PDX excerpts or exported diagnostic metadata
- DoIP addressing notes and tester/ECU logical addresses
- flash or programming sequence drafts

## Review Points

- Distinguish request SID, positive response SID, and negative response `0x7F`.
- Preserve NRCs exactly. `0x78` response-pending extends waiting and is not a success by itself.
- Check subfunction suppress-positive-response bit before treating missing responses as failures.
- Keep DID, RID, address, and length fields in big-endian order unless the diagnostic database says otherwise.
- Separate payload construction from transport. A valid UDS payload can still be unsafe for a target ECU.
- For DoIP, keep path-stable source/interface context when multiple NICs are present.

## Script Helpers

Run from the plugin package root when script execution is allowed:

- `python3 scripts/automotive/uds_payload.py decode HEX --format json`
- `python3 scripts/automotive/uds_payload.py rdbi F190 F187 --format json`
- `python3 scripts/automotive/uds_payload.py dtc-status 9B --format json`
- `python3 scripts/automotive/odx_inspect.py --odx database.odx --format json`
- `python3 scripts/automotive/uds_sequence_lint.py --sequence sequence.csv --format json`

If command execution is restricted, do not bypass it. Review snippets manually and state that deterministic script checks were not run.

## Nexus Handoff

Use `plotune-uds-doip-diagnostics` for live sends, DoIP discovery, DoIP leases, response-pending handling, and raw evidence capture. Use one target per request and pass any acquired DoIP lease session into sends.

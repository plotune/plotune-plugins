---
name: automotive-diagnostics-planning
description: Use when planning or reviewing automotive diagnostics without live ECU access, including UDS payloads, DoIP addressing, DTCs, DIDs, routines, ODX or PDX assumptions, diagnostic reports, NRCs, or flash sequence drafts.
---

# Automotive Diagnostics Planning

Use this skill for offline diagnostic reasoning. It does not send requests or open transport connections.

Read:

- `../../references/automotive-domain/diagnostics.md`
- `../../references/automotive-domain/nexus-adoption-map.md`
- `../../references/automotive-domain/script-catalog.md`

Run script examples from the plugin package root, the directory containing `skills/`, `references/`, and `scripts/`. If script execution is restricted, do a manual best-effort review and state which script checks were not run.

## Workflow

1. Identify whether the user has payload bytes, diagnostic database metadata, DTCs, a sequence draft, or a report.
2. Decode or build UDS bytes with `uds_payload.py` when exact payload reasoning is useful:

   ```bash
   python3 scripts/automotive/uds_payload.py decode 7F2278 --format json
   python3 scripts/automotive/uds_payload.py rdbi F190 F187 --format json
   ```

3. Inspect ODX/PDX metadata before making DID, DTC, service, or routine claims:

   ```bash
   python3 scripts/automotive/odx_inspect.py --odx path/to/database.odx --format json
   ```

4. Lint diagnostic sequence drafts before proposing a live run:

   ```bash
   python3 scripts/automotive/uds_sequence_lint.py --sequence path/to/uds_sequence.csv --format json
   ```

5. Preserve NRCs, timeouts, response-pending behavior, malformed bytes, and risky-service preconditions as evidence.
6. Separate payload validity from target safety and transport readiness.
7. For active diagnostics, switch to `plotune-uds-doip-diagnostics` and require target, transport, lease, and stop-condition context.

## Output

Hex IS the natural language for diagnostics — DID F190, service 0x22, NRC 0x22 are how engineers communicate. Use hex freely, but always decode alongside:
- NRCs by name: "NRC 0x22 (conditionsNotCorrect)" not just "0x22"
- Service names: "ReadDataByIdentifier (0x22)" not just "0x22"
- DTC status bits by name: "testFailed, confirmedDTC" not just "0x0F"

Sequence review: state each step by service name and purpose, flag preconditions (session state, security level), and call out steps that change ECU state with "requires confirmation before live execution."

ODX findings: name the specific service, DID, or routine that has an issue — don't dump raw ODX element trees.

Mark any proposed live ECU action explicitly as proposed, not as a conclusion.

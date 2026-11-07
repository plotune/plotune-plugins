---
name: automotive-can-dbc-analysis
description: Use when analyzing automotive CAN, DBC, CAN FD assumptions, DBC signal definitions, CAN trace logs, candump or ASC-like logs, bus timing, payload changes, unknown arbitration IDs, or offline bus reports.
---

# Automotive CAN And DBC Analysis

Use this skill for offline bus artifact analysis. It does not open CAN sockets or send frames.

Run script examples from the plugin package root, the directory containing `skills/`, `references/`, and `scripts/`. If script execution is restricted, do a manual best-effort review and state which script checks were not run.

## Workflow

1. Confirm what artifacts are available: DBC, trace log, decoded CSV, or expected signal list.
2. **Before asking the user for a DBC**, check whether one exists in the same directory as the trace file with the same base name (e.g., `network.dbc` alongside `network.asc`). Only ask if no DBC is found.
3. When a DBC is available, run the sanity checker first:

   ```bash
   python3 scripts/automotive/dbc_sanity.py --dbc path/to/network.dbc --format json
   ```

4. Run the trace summarizer with the DBC so signals are decoded by name:

   ```bash
   python3 scripts/automotive/can_trace_summarize.py --trace path/to/trace.log --dbc path/to/network.dbc --bitrate 500000 --format json
   ```

   The script supports candump format, standard ASC format, and Vector CAN FD ASC format (with the `CANFD` keyword).

5. For mixed artifact sets, run triage first:

   ```bash
   python3 scripts/automotive/automotive_triage.py --inputs path/to/network.dbc path/to/trace.log --format json
   ```

6. For live capture, waits, DBC sends, or periodic frames, switch to `plotune-can-workflows`.

## Output Format

**Report at message and signal level, not byte level.** Engineers care about what the data means, not which byte offset contains which hex value.

Good output:
- "2 messages decoded: `ReplayCanFdPayload` (0x456, 1 frame) and `ReplayCanFdExtended` (0x18FF50E5, 1 frame). Both use CAN FD BRS. Frame 2 has ESI=1 (transmitter error-passive at send time — benign in a replay simulation, flag on real hardware)."

Bad output:
- A table of Byte0=0x01, Byte1=0x02... for each byte in the payload.

**When signals have names from the DBC, use them.** Only fall back to raw bytes for IDs with no DBC coverage.

**Summary structure:**
- Messages decoded vs. unknown IDs (DBC coverage)
- Signal values by name for known messages (not byte-by-byte)
- Anomalies: CAN FD flags, ESI=1, cycle-time violations, duplicate IDs, unknown IDs
- What the trace represents: simulation, bench, vehicle, etc.
- Script limitations if any (e.g., unsupported format variant)

## Notes

- Separate observed trace facts from decoded signal interpretations.
- Call out 11-bit vs. 29-bit ID ambiguity, CAN FD assumptions, byte order, signedness, and multiplexing.
- Do not invent transmit frames from a DBC review.
- If the script reports malformed lines, check whether the format is an unsupported variant (e.g., DLC-only ASC without data bytes). Report the limitation explicitly and do the analysis manually.

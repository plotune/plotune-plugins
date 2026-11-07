---
name: automotive-calibration-a2l-xcp
description: Use when reviewing automotive calibration artifacts without live ECU access, including A2L or ASAP2 files, LAB measurement lists, XCP planning, calibration deltas, measurement plans, or parameter-change reports.
---

# Automotive Calibration A2L And XCP

Use this skill for offline calibration planning and artifact review. It does not read or write ECU memory.

Read:

- `../../references/automotive-domain/calibration.md`
- `../../references/automotive-domain/nexus-adoption-map.md`
- `../../references/automotive-domain/script-catalog.md`

Run script examples from the plugin package root, the directory containing `skills/`, `references/`, and `scripts/`. If script execution is restricted, do a manual best-effort review and state which script checks were not run.

## Workflow

1. Inventory A2L measurements, characteristics, transport hints, and LAB symbols.
2. Run the A2L/LAB checker when files are available:

   ```bash
   python3 scripts/automotive/a2l_lab_check.py --a2l path/to/file.a2l --lab path/to/list.lab --format json
   ```

3. Draft an offline DAQ plan from valid measurement symbols before live XCP planning:

   ```bash
   python3 scripts/automotive/xcp_daq_plan.py --a2l path/to/file.a2l --lab path/to/list.lab --max-signals-per-list 8 --format json
   ```

4. Compare calibration snapshots with the diff helper when baseline and candidate files exist:

   ```bash
   python3 scripts/automotive/calibration_diff.py --base path/to/base.json --candidate path/to/candidate.json --format json
   ```

5. Flag duplicates, missing units, missing addresses, LAB symbols absent from A2L, IF_DATA/XCP hints, address ranges, DAQ-list assumptions, and changed parameters.
6. Treat calibration changes as review items until target, security, rollback, and evidence plans are explicit.
7. For live measurement or calibration, switch to `plotune-xcp-workflows`.
8. For **symbol-level lookup** (finding which FUNCTION blocks contain a signal, resolving ECU addresses, or preparing a backtrace), use `inspect_a2l.py` directly — it is purpose-built for targeted symbol queries rather than inventory audits:

   ```bash
   python3 scripts/automotive/inspect_a2l.py --a2l path/to/file.a2l --symbol MySignal_Name
   ```

   For the full signal tracing workflow, use `automotive-signal-backtrace`.

## Output

**Report by parameter name and finding, not by raw symbol address or A2L offset.**

A2L/LAB summary: "N measurements, N characteristics — N LAB gaps, N missing units." Then:
- Name the specific parameters with issues: "BrakeTorque_Cmd is in the LAB but not in the A2L" is useful. A raw list of addresses is not.
- Calibration diff: "5 parameters changed — IdleSpeed: 800 → 850, CoolantThreshold: 90 → 95, ..." List by name with old and new values.
- DAQ plan: "N DAQ lists, N measurements total — list names, event channels, and any unsupported byte-order issues by parameter name."
- Keep measurement plans and calibration deltas in separate sections.
- Mention where XCP transport metadata appears (CAN vs. Ethernet hints from IF_DATA), but do not infer live connectivity without runtime context.
- Ask for A2L/LAB snippets rather than guessing symbol definitions.

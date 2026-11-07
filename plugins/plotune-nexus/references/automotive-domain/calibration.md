# Calibration And XCP Artifacts

Use this reference for offline A2L, LAB, XCP, and calibration artifact review. For live measurement or calibration, use Nexus XCP workflows.

## Offline Inputs

- A2L/ASAP2 files
- LAB or measurement list files
- calibration change logs
- HEX/S-record metadata or linker map summaries
- XCP transport notes from A2L `IF_DATA`

## Review Points

- Inventory measurements and characteristics separately.
- Check duplicate symbol names before building measurement plans.
- Compare LAB entries against A2L symbols.
- Flag missing units, conversions, or addresses for engineer review.
- Inspect byte order, `COMPU_METHOD`, `RECORD_LAYOUT`, and `IF_DATA` manually when exact scaling or memory layout matters.
- Treat calibration deltas as change requests until target, session, security, and rollback are explicit.

## Script Helpers

Run from the plugin package root when script execution is allowed:

- `python3 scripts/automotive/a2l_lab_check.py --a2l ECU.a2l --lab plan.lab --format json`
- `python3 scripts/automotive/xcp_daq_plan.py --a2l ECU.a2l --lab plan.lab --format json`
- `python3 scripts/automotive/calibration_diff.py --base base.json --candidate candidate.json --format json`

If command execution is restricted, do not bypass it. Review snippets manually and state that deterministic script checks were not run.

## Nexus Handoff

Use `plotune-xcp-workflows` for live XCP recording, calibration reads/writes, STIM planning, seed/key unlock flows, and artifact-based measurement outputs.

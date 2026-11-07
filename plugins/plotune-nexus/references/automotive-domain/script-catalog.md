# Offline Automotive Script Catalog

Run scripts from the plugin package root:

```bash
python3 scripts/automotive/<script>.py ...
```

Do not depend on parent-relative paths from individual skill folders. In copied or marketplace-installed packages, first locate the plugin package root that contains `.codex-plugin/plugin.json`, `skills/`, `references/`, and `scripts/`.

All scripts are Python stdlib only, read local files, print to stdout by default, and write only when `--output` is provided. Prefer `--format json` for agent workflows and summarize the parsed JSON instead of guessing from raw text.

If a user or client restricts shell/script execution, do not try to bypass the restriction. Read the relevant artifact snippets and this catalog, perform a manual best-effort review, and clearly state which deterministic script checks were not run. When possible, provide the exact `python3 scripts/automotive/... --format json` command so the user can run it in their allowed environment.

## Artifact Triage And Evidence

| Script | Use | Required Inputs | Typical Skill |
| --- | --- | --- | --- |
| `automotive_triage.py` | Detect mixed artifacts and run matching analyzers | `--inputs ...` | `automotive-adoption-gateway` |
| `evidence_pack.py` | Build SHA-256 evidence manifest | `--inputs ...` | requirements/test reporting |
| `tool_inventory.py` | Read-only local tool presence check | none | adoption/cybersecurity |
| `tool_compare.py` | Static tool comparison and Nexus handoff matrix | optional `--category` | adoption |

`tool_inventory.py` omits full executable paths by default. If `--include-paths` is used, redact paths before sharing reports.

## Networks And Diagnostics

| Script | Use | Required Inputs | Typical Skill |
| --- | --- | --- | --- |
| `dbc_sanity.py` | DBC structure, overlap, units, DLC, cycle checks | `--dbc` | CAN/DBC |
| `can_trace_summarize.py` | Trace timing, unknown IDs, DBC decoding, bus estimate | `--trace`, optional `--dbc` | CAN/DBC, Nexus CAN |
| `uds_payload.py` | Decode UDS payloads, build RDBI, decode DTC status byte | subcommand | diagnostics |
| `uds_sequence_lint.py` | Lint UDS sequence drafts and risky preconditions | `--sequence` | diagnostics, Nexus UDS |
| `odx_inspect.py` | ODX/PDX metadata inventory | `--odx` | diagnostics |

Common JSON fields:

- `dbc_sanity.py`: `summary`, `issues`, `messages`
- `can_trace_summarize.py`: `summary`, `dbc_coverage`, `messages.*.decoded_samples`
- `uds_payload.py`: `kind`, `service`, request or response fields
- `uds_sequence_lint.py`: `summary`, `issues`, `decoded_steps`
- `odx_inspect.py`: `summary`, `documents.*.inventory`, `documents.*.issues`

## Calibration And Architecture

| Script | Use | Required Inputs | Typical Skill |
| --- | --- | --- | --- |
| `a2l_lab_check.py` | A2L/LAB inventory, units, addresses, IF_DATA/XCP hints | `--a2l`, optional `--lab` | calibration |
| `xcp_daq_plan.py` | Draft XCP DAQ measurement lists | `--a2l`, optional `--lab` | calibration, Nexus XCP |
| `calibration_diff.py` | Compare calibration snapshots | `--base`, `--candidate` | calibration |
| `autosar_manifest_inspect.py` | Quick ARXML and manifest sanity checks | `--arxml`, optional `--manifest` | AUTOSAR |
| `autosar_architecture_report.py` | Component, port, runnable, event, service inventory | `--arxml`, optional `--manifest` | AUTOSAR |

Common JSON fields:

- `a2l_lab_check.py`: `summary`, `issues`, `xcp_hints`, `memory_ranges`, `inventory`
- `xcp_daq_plan.py`: `summary`, `xcp_hints`, `plan`
- `calibration_diff.py`: `summary`, `changes`
- `autosar_manifest_inspect.py`: `summary`, `issues`, `inventory`
- `autosar_architecture_report.py`: `summary`, `issues`, `inventory`

## Workproducts

| Script | Use | Required Inputs | Typical Skill |
| --- | --- | --- | --- |
| `requirements_trace_lint.py` | Requirement quality and test traceability lint | `--requirements`, optional `--tests` | requirements, safety |
| `safety_workproduct.py` | Generate/lint HARA, FMEA, FTA, safety goals/cases | `template` or `lint` | functional safety |
| `tara_workproduct.py` | Generate/lint TARA assets, attack surfaces, threats, treatments | `template` or `lint` | cybersecurity |

Common JSON fields:

- `requirements_trace_lint.py`: `summary`, `issues`, `rows`
- `safety_workproduct.py`: `status`, `summary` or `columns`, `issues` or `rows`
- `tara_workproduct.py`: `status`, `summary` or `columns`, `issues` or `rows`

## Safety Boundary

The scripts do not open CAN, serial, DoIP, XCP, cloud, or ECU connections. They do not authorize live actions. Live hardware work must go through the bounded `plotune-*` skills with explicit target, lease, payload, timeout, stop condition, artifact, and cleanup context.

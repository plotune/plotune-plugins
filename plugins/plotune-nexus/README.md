# Plotune Nexus Agent Plugin

## Install

```
/plugin install plotune-nexus --marketplace plotune/plotune-plugins
```

Or see the [marketplace README](../../README.md) for Claude Code, Copilot CLI and Codex.

This plugin provides agent skills for offline automotive engineering work and Plotune Nexus MCP servers.

It is intentionally script-backed and hardware-safe:

- offline automotive skills work from local files, payloads, requirements, and plans without a Nexus device
- bundled scripts provide deterministic first-pass reports before narrative review
- no device URL is embedded
- no bearer token is embedded
- no `.mcp.json` is generated
- all hardware actions are guided toward resource-first inspection, bounded operations, explicit confirmation, and cleanup
- notes workflows are documented for preserving operator and agent context around tests, artifacts, recordings, and failures

Use the `automotive-*` skills for offline analysis and planning. Use the `plotune-*` skills when operating connected Nexus devices.

Install or copy this package as a whole. The skill folders share references from `references/`, so copying a single skill folder without those references is incomplete.

## Skills

Offline automotive skills:

- `automotive-adoption-gateway`
- `automotive-diagnostics-planning`
- `automotive-calibration-a2l-xcp`
- `automotive-can-dbc-analysis`
- `automotive-autosar-architecture-review`
- `automotive-functional-safety-workproducts`
- `automotive-cybersecurity-tara`
- `automotive-requirements-vmodel-test-planning`
- `automotive-ehb-reader`
- `automotive-signal-backtrace`
- `automotive-signal-trace-report`

Plotune Nexus MCP skills:

- `plotune-mcp-setup`
- `plotune-agent-orientation`
- `plotune-safety-and-errors`
- `plotune-can-workflows`
- `plotune-dds-workflows`
- `plotune-xcp-workflows`
- `plotune-uds-doip-diagnostics`
- `plotune-uart-workflows`
- `plotune-artifacts-drives`
- `plotune-gateways-containers`
- `plotune-controller-simulations`
- `plotune-test-sequences-reporting`
- `plotune-n8n-mcp-workflow-json`

## Offline Scripts

Portable helper scripts live in `scripts/automotive/` inside this plugin package:

- `automotive_triage.py`
- `evidence_pack.py`
- `tool_inventory.py`
- `tool_compare.py`
- `dbc_sanity.py`
- `can_trace_summarize.py`
- `uds_payload.py`
- `uds_sequence_lint.py`
- `odx_inspect.py`
- `a2l_lab_check.py`
- `xcp_daq_plan.py`
- `calibration_diff.py`
- `autosar_manifest_inspect.py`
- `autosar_architecture_report.py`
- `requirements_trace_lint.py`
- `safety_workproduct.py`
- `tara_workproduct.py`

They are read-only by default and print reports to stdout. They write files only when `--output` is provided. Use `--format json` for agent workflows.

Run script examples from this plugin package root, not from individual skill folders. If a client or user policy blocks shell/script execution, agents should do a manual best-effort review, state which deterministic checks were not run, and provide the exact command for an allowed environment.

See `references/automotive-domain/script-catalog.md` for inputs, outputs, and skill mapping.

## Standards Boundary

Automotive standards guidance in this plugin is an engineering aid. It is not certification evidence, legal advice, or a substitute for licensed standards and qualified safety or cybersecurity review.

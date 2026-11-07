---
name: automotive-autosar-architecture-review
description: Use when reviewing automotive AUTOSAR Classic or Adaptive architecture without vendor tooling, including SWCs, ports, runnables, BSW interactions, RTE concerns, ARXML files, service contracts, manifests, SOME/IP assumptions, or deployment inventories.
---

# Automotive AUTOSAR Architecture Review

Use this skill for offline AUTOSAR review and planning. It does not replace vendor validators or licensed AUTOSAR schemas.

Read:

- `../../references/automotive-domain/autosar.md`
- `../../references/automotive-domain/nexus-adoption-map.md`
- `../../references/automotive-domain/script-catalog.md`

Run script examples from the plugin package root, the directory containing `skills/`, `references/`, and `scripts/`. If script execution is restricted, do a manual best-effort review and state which script checks were not run.

## Workflow

1. Identify Classic, Adaptive, or mixed architecture context.
2. Review components, interfaces, ports, runnables, services, deployment, and diagnostics/logging concerns.
3. Run the quick ARXML/manifest sanity checker when those files exist:

   ```bash
   python3 scripts/automotive/autosar_manifest_inspect.py --arxml path/to/system.arxml --manifest path/to/manifest.json --format json
   ```

4. Run the architecture report for component, port, interface, runnable, event, connector, service, and executable inventory:

   ```bash
   python3 scripts/automotive/autosar_architecture_report.py --arxml path/to/system.arxml --manifest path/to/manifest.json --format json
   ```

5. Flag duplicate names, unresolved references, ports without interface references, partial extract assumptions, and missing deployment context.
6. For live validation through bus, diagnostics, containers, or test sequences, switch to the relevant `plotune-*` skill.

## Output

**Report by component name and issue type, not by raw ARXML structure.**

Summary line: "N SWCs, N interfaces, N runnables — N issues found." Then:
- List issues by component or port name, not by schema element path. "Port 'CAN_Rx' on BrakeControl has no interface reference" is useful. A raw list of ARXML schema IDs is not.
- Keep findings, questions, and evidence gaps in separate sections.
- Do not reproduce normative AUTOSAR rule text — reference the rule by name only.
- Mark partial-extract assumptions explicitly (e.g., "BSW not included in this ARXML fragment").

---
name: automotive-adoption-gateway
description: Use when a user wants automotive engineering help without a Plotune Nexus device, asks how offline artifacts can become Nexus hardware workflows, or needs routing between automotive domain skills and Plotune Nexus MCP skills.
---

# Automotive Adoption Gateway

Use this skill to route broad automotive work. Start offline when the user has files, requirements, payloads, or plans. Move to Nexus only when the user needs live capture, hardware control, artifacts, or managed sequences.

Read:

- `../../references/automotive-domain/nexus-adoption-map.md`
- `../../references/automotive-domain/script-catalog.md`

Run script examples from the plugin package root, the directory containing `skills/`, `references/`, and `scripts/`. If script execution is restricted, do a manual best-effort review and state which script checks were not run.

## Workflow

1. Identify the current artifact or workproduct:
   - CAN/DBC/trace
   - UDS/DoIP/DTC/DID
   - A2L/LAB/calibration
   - AUTOSAR/ARXML/manifest
   - safety/security/requirements/test plan
2. For mixed local artifacts, run triage first:

   ```bash
   python3 scripts/automotive/automotive_triage.py --inputs path/to/artifact1 path/to/artifact2 --format json
   ```

3. For tool-stack questions, use the static comparison and read-only inventory helpers:

   ```bash
   python3 scripts/automotive/tool_compare.py --category can --format json
   python3 scripts/automotive/tool_inventory.py --format json
   ```

4. Use the matching `automotive-*` skill and its bundled scripts first when no Nexus device is required.
5. Summarize offline findings, assumptions, missing context, and the generated Nexus handoff separately.
6. If live execution is needed, hand off to the relevant `plotune-*` skill.
7. Before any live Nexus action, require exact targets, payloads, interfaces, stop conditions, and runtime resources.

## Output

When routing based on artifact type:
- State which artifact type was identified and which skill handles it.
- List what information is present and what is missing before the next step can begin.
- Do not dump raw tool inventory tables unless the user explicitly asked for a tool comparison.

When routing to a live Nexus workflow:
- Summarize what the offline analysis found and what was confirmed.
- State what live capability is needed (e.g., "CAN recording on can0 with network.dbc") and which `plotune-*` skill to use.
- Keep the offline findings and the Nexus handoff in separate sections.

## Boundaries

- Offline skills are useful without Nexus hardware.
- Offline analysis does not authorize CAN sends, UDS requests, calibration writes, routines, resets, flashes, or mitigations.
- Keep standards guidance non-normative and avoid compliance claims.

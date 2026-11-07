---
name: plotune-n8n-mcp-workflow-json
description: Use when turning a Plotune Nexus test case, manual validation procedure, or test sequence idea into JSON payloads for n8n MCP Client nodes, including run_test_sequence definitions, status polling, artifact export, and webhook-triggered Nexus automation.
---

# Plotune Nexus n8n MCP Workflow JSON

Use this skill to turn a Nexus test case into n8n-ready MCP Client JSON. The output should help an operator build an n8n workflow that calls existing Plotune Nexus MCP tools. Do not invent a separate Nexus HTTP API or webhook contract.

## Step 1 - Load The Local Contract

Read these references before producing JSON:

- `references/mcp-connection.md`
- `references/tool-contracts.md`
- `references/test-sequences.md`
- `references/n8n-mcp-workflows.md`

If a live Nexus MCP server is available, prefer live tool schemas and resources over static examples:

```
read resource: plotune://device/context
read resource: plotune://device/interfaces
read resource: plotune://artifacts/recent
```

## Step 2 - Normalize The Test Case

Extract or ask briefly for missing essentials:

- trigger source: manual, schedule, webhook, or another n8n node
- target action: read-only status, capture, diagnostic, calibration, gateway, container, or managed test sequence
- hardware targets: CAN channel, interface, UART device, DoIP target, A2L/LAB/DBC paths, artifact IDs
- time bounds: recording durations, wait timeouts, polling interval
- evidence: artifact, status result, decoded value, diagnostic response, external ticket/comment/callback
- safety posture: read-only, transmit allowed, calibration write allowed, flash/programming allowed

If the request is a multi-step validation procedure, model it as `run_test_sequence` unless the user explicitly needs separate n8n nodes for each hardware action.

## Step 3 - Produce n8n MCP Client Payloads

Default output format:

1. A short node sequence, for example `Webhook Trigger -> MCP Client: run_test_sequence -> MCP Client: wait_for_test_sequence -> MCP Client: list_artifacts_tool`.
2. One fenced `json` block per Nexus MCP tool call.
3. A mapping table that shows which test-case fields map to which JSON fields.
4. Safety and credential notes only when they affect execution.

For n8n, generate tool argument JSON for the MCP Client node's JSON input mode. Do not output raw MCP `tools/call` JSON-RPC unless the user explicitly asks for protocol-level MCP traffic.

## JSON Rules

- Emit valid JSON only inside `json` fences: no comments, trailing commas, or unquoted placeholders.
- Use placeholders such as `"<device-uuid>"`, `"<job-id-from-run_test_sequence>"`, and `"<artifact-id>"`; never embed real tokens, real device UUIDs, OAuth secrets, or customer data.
- Put test names, requirement IDs, and scenario labels under `definition.metadata` in `run_test_sequence`.
- Declare sequence-owned recordings in `definition.recordings`, then reference them from `start_recording` and `stop_recording` steps.
- Use Nexus-device paths for `a2l_file_path`, `lab_file_path`, `dbc_file_path`, and artifact-backed file paths.
- Keep numeric MCP parameters numeric. If an n8n expression supplies a numeric field, tell the user to map it in n8n so the final value is a number.
- Use `MCP Client` for normal workflows. Use `MCP Client Tool` only for n8n AI Agent flows. Do not use `MCP Server Trigger` to call Nexus.

## Safety Rules

- Start with read-only tools such as `get_device_context_tool` or `list_can_interfaces_tool` when the endpoint or credentials are new.
- For hardware mutation tools, include explicit bounds and cleanup/status steps.
- For leased CAN or DoIP targets, preserve the lease `session_id` and pass it as `lease_session_id` where required.
- For long work, return or wait on job IDs with `wait_for_job`, `get_job_status_tool`, `wait_for_test_sequence`, or `get_test_sequence`.
- For artifacts, prefer status tools first, then `list_artifacts_tool(job_id=...)`, `get_artifact_metadata_tool`, `get_artifact`, or `upload_to_artifact_drive`.

## Importable n8n Workflow JSON

Only produce a full importable n8n workflow JSON when the user asks for it. n8n workflow exports are version-sensitive and can include credential names or IDs, so keep credentials as placeholders and tell the user to validate the imported workflow in their n8n version.

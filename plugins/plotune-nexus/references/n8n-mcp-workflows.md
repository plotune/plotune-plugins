# n8n MCP Workflow JSON Reference

This reference supports the `plotune-n8n-mcp-workflow-json` skill. It focuses on JSON payloads for n8n MCP Client nodes that call Plotune Nexus tools.

## n8n MCP Client Shape

Use the n8n `MCP Client` node for deterministic workflow steps. It can call tools from an external MCP server and has a JSON input mode for nested tool parameters.

Use these nodes by direction:

| n8n node | Direction |
|---|---|
| MCP Client | n8n calls Plotune Nexus MCP tools as normal workflow steps. |
| MCP Client Tool | n8n exposes external MCP tools to an n8n AI Agent. |
| MCP Server Trigger | n8n acts as an MCP server for external MCP clients. |

Useful official references:

- `https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcpClient/`
- `https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.toolmcp/`
- `https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcptrigger/`
- `https://docs.n8n.io/workflows/export-import/`

## Endpoint And Auth Fields

Common Nexus MCP endpoints:

```text
http://<device-ip>/mcp
https://<device-uuid>.plotune.net/mcp
```

Auth headers:

```text
Authorization: Bearer <token>
X-Plotune-MCP-Bearer-Token: <token>
```

Use n8n credentials for tokens. Do not place bearer tokens in workflow JSON or skill output.

## Output Contract For A Test Case

When asked to convert a test case, return:

| Section | Content |
|---|---|
| n8n node sequence | Trigger and MCP Client node order. |
| MCP Client setup | Endpoint placeholder, auth mode, selected tools, timeout notes. |
| Tool payloads | One JSON object per MCP Client node. |
| Field mapping | Test-case field to Nexus JSON field. |
| Result handling | Which job status and artifact tools to call next. |

Do not output raw MCP protocol JSON by default. The n8n MCP Client node abstracts `tools/list` and `tools/call`; users need the tool arguments JSON.

## Pattern: Multi-Step Test Sequence

Use this when the test case has ordered actions, waits, recordings, and evidence that should be owned by Nexus.

Node sequence:

```text
Webhook Trigger or Manual Trigger
  -> MCP Client: run_test_sequence
  -> MCP Client: wait_for_test_sequence
  -> MCP Client: list_artifacts_tool
  -> notification, ticket update, or callback node
```

`run_test_sequence` JSON:

```json
{
  "definition": {
    "recordings": [
      {
        "id": "can-window",
        "protocol": "can",
        "channel": "can0",
        "interface": "socketcan",
        "duration_seconds": 10
      }
    ],
    "steps": [
      {
        "id": "start-can",
        "type": "start_recording",
        "target": {
          "kind": "recording",
          "recording_id": "can-window"
        }
      },
      {
        "id": "hold-window",
        "type": "wait_duration",
        "target": {
          "kind": "duration"
        },
        "duration_seconds": 10
      },
      {
        "id": "stop-can",
        "type": "stop_recording",
        "target": {
          "kind": "recording",
          "recording_id": "can-window"
        }
      }
    ],
    "metadata": {
      "scenario": "n8n-can-smoke",
      "source": "n8n",
      "test_case_id": "TC-CAN-001"
    }
  }
}
```

`wait_for_test_sequence` JSON:

```json
{
  "job_id": "<job-id-from-run_test_sequence>",
  "timeout_seconds": 120,
  "poll_interval_seconds": 1
}
```

`list_artifacts_tool` JSON:

```json
{
  "job_id": "<test-sequence-job-id>",
  "only_complete": true
}
```

## Pattern: Direct Recording

Use this when the workflow only needs a single capture and does not need sequence-managed steps.

Node sequence:

```text
Webhook Trigger, Schedule Trigger, or Manual Trigger
  -> MCP Client: record_can
  -> MCP Client: wait_for_job
  -> MCP Client: get_record_can
  -> MCP Client: get_artifact or upload_to_artifact_drive
```

`record_can` JSON:

```json
{
  "channel": "can0",
  "duration_seconds": 60,
  "interface": "socketcan"
}
```

`wait_for_job` JSON:

```json
{
  "job_id": "<job-id-from-record_can>",
  "timeout_seconds": 90,
  "poll_interval_seconds": 1
}
```

## Pattern: Webhook Fields To Nexus Fields

When n8n receives an external webhook, validate the body before calling Nexus.

Example normalized webhook body:

```json
{
  "test_case_id": "TC-CAN-001",
  "channel": "can0",
  "duration_seconds": 10,
  "callback_url": "https://example.invalid/callback"
}
```

Map values into MCP Client JSON using n8n expressions. Preserve expected types after expression evaluation, especially numbers such as `duration_seconds`, `timeout_seconds`, and `poll_interval_seconds`.

## Pattern: Artifact And Result Handoff

After a job finishes, choose one handoff path:

| Goal | Tool |
|---|---|
| Get local metadata | `get_artifact_metadata_tool` |
| Get a download URL (direct from the device) | `get_artifact` |
| Upload to configured artifact drive | `upload_to_artifact_drive` |
| Find sequence artifacts | `list_artifacts_tool(job_id="<sequence-job-id>")` |

For callbacks to external systems, send a compact payload from n8n containing the Nexus job ID, terminal status, selected step evidence, and artifact link or drive path.

## Full n8n Workflow JSON

n8n workflow exports are full workflow definitions, not just MCP tool arguments. They include `nodes`, `connections`, and `settings`, and exported files can include credential names and IDs. Generate a full importable workflow only when requested, keep credentials as placeholders, and validate the import in the target n8n version.

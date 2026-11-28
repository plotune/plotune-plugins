# Plotune

Connects your agent to Plotune through **one** MCP server, the Plotune gateway (`https://mcp.plotune.net/mcp`, registered by this plugin as `plotune`): requirements (RMS), event history and analytics (Stream) and cloud sessions on Nexus Edges with their test devices (Nexus). One sign-in; you choose **Read only** or **Full access** on the consent page, and your role in each workspace still limits what a call can do.

## Install

```
/plugin install plotune@plotune-plugins
```

Or see the [marketplace README](../../README.md) for Claude Code, Copilot CLI, Codex, Cursor and OpenCode. The MCP server is registered by the plugin's `.mcp.json` (`mcp.json` for Cursor); sign in through the OAuth prompt on first use. The URL is the same for everyone, unlike `plotune-nexus`, which connects to your own device.

## What the connector's tools can do

The plugin's skills call the Plotune server's tools. With **Full access** (and the right role in the workspace), those tools can do the following. With **Read only**, only the reading tools, the Stream analysis tools and Nexus workspace file links are offered; none of the tools below that send, delete or change access are. Claude asks before each tool that is not read-only, and the tools that delete, revoke access, run shell commands or send to hardware are also marked destructive.

- **Send to hardware and other systems.** Send CAN frames, CAN messages from a DBC file and periodic CAN traffic; send bytes on UART and serial ports; send UDS diagnostic requests to a vehicle or ECU; write XCP calibration values and stimulate XCP signals; publish DDS messages; ramp XCP calibrations, DBC signals and DDS topics, and inject faults on DDS topics (`ramp_value`, `dds_ramp`, `dds_fault_inject`); run test sequences. On a Nexus Edge or machine, `nexus_exec` runs shell commands (as an unprivileged user, or as root for Owners and Admins), and `nexus_start_container` starts containers in a session.
- **Send data to outside URLs.** `webhooks_create` and `webhooks_update` forward the project's captured events to an HTTPS URL that an Owner or Admin chooses; `webhook_test` sends one sample event to it now.
- **Publish and share.** Create and change Stream dashboards, insights and actions, and RMS records (requirements, test cases, test runs, traceability), visible to the project's members. Approvers can freeze baselines.
- **Delete.** Delete dashboards (one or many), dashboard tiles, insights, actions and webhooks; remove traceability links; delete files in the Nexus session workspace; remove container images; delete virtual CAN interfaces.
- **Change access.** `members_set_role` changes a project member's RMS role (reader, editor, approver); `connections_revoke` revokes an agent connection; `processes_set` and `settings_set` change the approval lifecycle and governance settings (Admin only); `nexus_connect_device_to_pc` makes a bench USB device available on the user's own PC.
- **Pay.** No tool makes payments or moves money. Some tools use the workspace's plan allowance: Stream analysis jobs and webhook deliveries count against its event allowance, and Nexus sessions count session time.

## Skills

| Skill | What it does |
|---|---|
| `plotune-orientation` | Start here: connecting, Read only versus Full access, `plotune_projects_list` first, the `project_id` rules, and what to do when a product is unavailable or the sign-in expires. |
| `stream-orientation` | Safe, bounded querying of Stream event history through the gateway, analysis jobs, and which tools need your confirmation. |
| `nexus-cloud-orientation` | Cloud Nexus sessions: find an Edge, start and poll a session, device tools, long work as jobs, and stopping the session. Hardware-actuating tools are confirmed every time. |
| 13 requirements skills | `agent-execution`, `automotive-profiles`, `change-impact`, `existing-requirements-review`, `idea-to-requirements`, `lead-task-tracking`, `requirement-decomposition`, `requirements-cycle`, `requirements-governance`, `traceable-delivery`, `verification-coverage`, `work-orchestration`, `workspace-management`. |

## What is bundled, and from where

The requirements skills and what they depend on (`scripts/`, `schema/`, `templates/`, `migrations/`, `docs/`, `examples/` and the AI-pool `hooks/`) are **copies of [`plotune-requirements`](../plotune-requirements)**, which stays the only place to edit them. `tools/bundles.json` declares the copied paths and `python tools/sync_bundles.py` refreshes them (`--check` fails when a copy differs). Do not edit those paths here.

Not bundled: the appliance skills of `plotune-nexus` (they target a per-device URL and the old, unprefixed tool names), and the requirements plugin's own `tests/` and `evals/`.

The bundled hook only records subagent calls when you have an `ai-pool.json`, as in `plotune-requirements`. Do not install `plotune` and `plotune-requirements` together: the same skills and the same hook would be present twice.

## Tool names

`references/gateway-tools.json` lists every tool name the gateway offers (plus `plotune_projects_list`), generated from the monorepo catalog by `tools/generate_gateway_tools.py`, with the monorepo commit it was generated from. `python tools/check_gateway_tools.py` fails when a skill names an old (renamed) or unavailable tool, for example `list_jobs_tool` instead of `nexus_list_jobs`.

## OpenAI plugin directory

`.openai-plugin/plugin.json` is the manifest for OpenAI's plugin submission (Agent Plugins schema; listing fields, starter prompts, onboarding skill and the review test cases live under `extensions.com.openai`). It sits in a hidden folder because a root `plugin.json` would shadow the Claude manifest in tools that read a root manifest first. Build and validate the upload with:

```
python tools/package_openai.py plotune      # writes dist/plotune-<version>-openai.zip (gitignored)
```

The script puts `plugin.json` (with `version` from the Claude manifest) and a portable `mcp.json` (`$schema`, `"type": "streamable-http"`, generated from `.mcp.json`) at the ZIP root next to `skills/`, `assets/` and the files the skills use. It leaves out `hooks/` (OpenAI cannot accept lifecycle hooks), evals, other tools' manifests and anything that looks like a secret, then validates the result. Warnings list what the owner must still enter: `termsOfServiceURL` and `demo_recording_url` (both required for MCP review). Reviewer credentials go in the submission dashboard, never in the ZIP. Test cases and starter prompts: [`docs/plotune-review-test-cases.md`](../../docs/plotune-review-test-cases.md).

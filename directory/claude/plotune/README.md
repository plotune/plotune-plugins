# Plotune

Version 0.1.1. Connects Claude to Plotune through **one** remote MCP server, the Plotune gateway at `https://mcp.plotune.net/mcp` (registered by this plugin's `.mcp.json` as `plotune`): requirements (RMS), event history and analytics (Stream), and cloud sessions on Nexus Edges with their test devices (Nexus). It is the same server as the Plotune connector in the Claude directory.

## What it does, sends and fetches

- **One network destination.** Tool calls go to `https://mcp.plotune.net/mcp`, which Plotune operates. Nothing else is contacted by the plugin.
- **No local code.** The plugin contains only skills (Markdown), the MCP configuration, reference JSON the skills cite, and images. It runs no hooks, scripts or programs, installs nothing and does not change Claude's permissions.
- **Sign-in.** On first use, Claude opens Plotune's OAuth sign-in. You choose **Read only** or **Full access** on the consent page; your role in each workspace still limits what a call can do. You can change or revoke the connection at any time under Connected apps on plotune.net.
- **Data.** What Plotune stores for a connection, and for how long, is in the privacy policy: https://www.plotune.net/privacy#ai-apps.

## What the connector's tools can do

The plugin's skills call the Plotune server's tools. With **Full access** (and the right role in the workspace), those tools can do the following. With **Read only**, only the reading tools and the Stream analysis tools are offered; none of the tools below that send, delete or change access are. Claude asks before each tool that is not read-only, and the tools that delete, revoke access, run shell commands or send to hardware are also marked destructive.

- **Send to hardware and other systems.** Send CAN frames, CAN messages from a DBC file and periodic CAN traffic; send bytes on UART and serial ports; send UDS diagnostic requests to a vehicle or ECU; write XCP calibration values and stimulate XCP signals; publish DDS messages; run test sequences. On a Nexus Edge or machine, `nexus_exec` runs shell commands (as an unprivileged user, or as root for Owners and Admins), and `nexus_start_container` starts containers in a session.
- **Send data to outside URLs.** `webhooks_create` and `webhooks_update` forward the project's captured events to an HTTPS URL that an Owner or Admin chooses; `webhook_test` sends one sample event to it now.
- **Publish and share.** Create and change Stream dashboards, insights and actions, and RMS records (requirements, test cases, test runs, traceability), visible to the project's members. Approvers can freeze baselines.
- **Delete.** Delete dashboards (one or many), dashboard tiles, insights, actions and webhooks; remove traceability links; delete files in the Nexus session workspace; remove container images; delete virtual CAN interfaces.
- **Change access.** `members_set_role` changes a project member's RMS role (reader, editor, approver); `connections_revoke` revokes an agent connection; `processes_set` and `settings_set` change the approval lifecycle and governance settings (Admin only); `nexus_connect_device_to_pc` makes a bench USB device available on the user's own PC.
- **Pay.** No tool makes payments or moves money. Some tools use the workspace's plan allowance: Stream analysis jobs and webhook deliveries count against its event allowance, and Nexus sessions count session time.

## Skills

| Skill | What it does |
|---|---|
| `plotune-orientation` | Start here: connecting, Read only versus Full access, `plotune_projects_list` first, the `project_id` rules, and what to do when a product is unavailable or the sign-in expires. |
| `stream-orientation` | Safe, bounded querying of Stream event history, analysis jobs, and which tools need your confirmation. |
| `nexus-cloud-orientation` | Cloud Nexus sessions: find an Edge, start and poll a session, device tools, long work as jobs, and stopping the session. Tools that actuate hardware are confirmed every time. |
| 13 requirements skills | `agent-execution`, `automotive-profiles`, `change-impact`, `existing-requirements-review`, `idea-to-requirements`, `lead-task-tracking`, `requirement-decomposition`, `requirements-cycle`, `requirements-governance`, `traceable-delivery`, `verification-coverage`, `work-orchestration`, `workspace-management`: discovery, review, governance, change impact and verification of requirements, with Plotune RMS as the store. |

## Directory edition

This folder is generated from `plugins/plotune` by `tools/build_claude_directory.py` and is never edited by hand. It leaves out what the full plugin adds for local use: the scripts, schema templates and migrations for a local SQLite, CSV or Google Sheets requirements workspace, and the hook that meters subagent calls for the optional AI pool of `requirements-cycle`. The skills mention those steps as optional; with this edition, use Plotune RMS through the connector. The full plugin is in the Plotune marketplace: https://github.com/plotune/plotune-plugins.

Documentation: https://www.plotune.net/docs/mcp. Support: contact@plotune.net. License: Apache-2.0.

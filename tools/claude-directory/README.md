# Plotune

Version {version}. Connects Claude to Plotune through **one** remote MCP server, the Plotune gateway at `https://mcp.plotune.net/mcp` (registered by this plugin's `.mcp.json` as `plotune`): requirements (RMS), event history and analytics (Stream), and cloud sessions on Nexus Edges with their test devices (Nexus). It is the same server as the Plotune connector in the Claude directory.

## What it does, sends and fetches

- **One network destination.** Tool calls go to `https://mcp.plotune.net/mcp`, which Plotune operates. Nothing else is contacted by the plugin.
- **No local code.** The plugin contains only skills (Markdown), the MCP configuration, reference JSON the skills cite, and images. It runs no hooks, scripts or programs, installs nothing and does not change Claude's permissions.
- **Sign-in.** On first use, Claude opens Plotune's OAuth sign-in. You choose **Read only** or **Full access** on the consent page; your role in each workspace still limits what a call can do. You can change or revoke the connection at any time under Connected apps on plotune.net.
- **Data.** What Plotune stores for a connection, and for how long, is in the privacy policy: https://www.plotune.net/privacy#ai-apps.

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

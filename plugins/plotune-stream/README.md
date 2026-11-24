# Plotune Stream

Connects your agent to the Plotune Stream MCP server (`https://stream.plotune.net/mcp`) and ships one orientation skill, `stream-orientation`, for querying engineering event history safely and frugally.

## Install

```
/plugin install plotune-stream --marketplace plotune/plotune-plugins
```

Or see the [marketplace README](../../README.md) for Claude Code, Copilot CLI and Codex. The MCP server is registered by the plugin's `.mcp.json`; sign in through the OAuth prompt on first use.

## Notes

- Using the Plotune gateway (`mcp.plotune.net`)? The [`plotune`](../plotune) plugin replaces this one for gateway users: one sign-in for RMS, Stream and Nexus, with a `stream-orientation` skill written for the gateway's tool names and project handling. This plugin keeps connecting to `stream.plotune.net` directly.

- MCP tool calls are not charged credits; they are rate limited per workspace (a refused call answers 429 with `Retry-After`).
- The skill is read-first: writes (webhooks, catalog, dashboards, project settings) are confirmed with you before they run.

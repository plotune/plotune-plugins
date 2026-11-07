# Plotune Stream

Connects your agent to the Plotune Stream MCP server (`https://stream.plotune.net/mcp`) and ships one orientation skill, `stream-orientation`, for querying engineering event history safely and frugally.

## Install

```
/plugin install plotune-stream --marketplace plotune/plotune-plugins
```

Or see the [marketplace README](../../README.md) for Claude Code, Copilot CLI and Codex. The MCP server is registered by the plugin's `.mcp.json`; sign in through the OAuth prompt on first use.

## Notes

- Each project tool call costs one credit from the project owner's account.
- The skill is read-first: writes (webhooks, catalog, dashboards, project settings) are confirmed with you before they run.

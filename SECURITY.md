# Security policy

## What these plugins can do

Plotune plugins are not just documentation. Installing one can give your coding agent:

- **Skills and scripts** that the agent may run on your machine (for example the Python helpers under `plugins/plotune-nexus/scripts/` and `plugins/plotune-requirements/scripts/`).
- **MCP servers** that reach external services (`plotune-stream` connects to `https://stream.plotune.net/mcp`; `plotune-nexus` connects to a device you point it at and can control hardware such as CAN interfaces).

Install only plugins you trust, read what a plugin ships before enabling it, and prefer pinned release tags (`<plugin>--v<version>`) over a moving branch. Skills that change state say so and ask first: `stream-orientation` confirms before webhook, catalog and dashboard writes, and the Nexus skills have a safety-and-errors reference for hardware actions.

## Reporting a vulnerability

Please **do not open a public issue** for a security problem.

Once this repository is public, use GitHub's private reporting: open **Security → Report a vulnerability**. While it is private (private reporting is not available yet), contact the maintainers directly through GitHub (members of the `plotune` organization). Include the plugin and version, what you found, and how to reproduce it. We aim to acknowledge a report within a few working days and will tell you what we decide.

In scope: anything in this repository that could make a plugin run unintended code, leak credentials or data, or cause an unsafe hardware action; the release workflow; the checked-in tooling.
Out of scope: vulnerabilities in the Plotune Stream or Nexus services themselves (report those through the product's own channels), and in Claude Code, Codex, Copilot, Cursor or OpenCode.

## Supported versions

Only the latest released version of each plugin receives fixes.

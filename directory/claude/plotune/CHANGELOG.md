# Changelog

## 0.1.0 — initial release: one MCP server (mcp.plotune.net) with plotune-orientation, stream-orientation, nexus-cloud-orientation and the 13 requirements skills bundled from plotune-requirements

## 0.1.1 — plotune-orientation: RMS is the requirements store; local workspaces and the AI pool need the full plugin (the Claude directory edition has no scripts/).

## 0.1.2 — follow the gateway after the OpenAI review of 2026-11-28: test sequences stay, and every step type has a tool of its own (`ramp_value`, `wait_measurement`, `wait_duration`, `dds_ramp`, `dds_assert`, `dds_causal_wait`, `dds_fault_inject`, `dds_record_and_assert`), described in nexus-cloud-orientation; stopping work, containers and watch restarts are destructive; `insights_run` replaces a shared result, so it is not a read; `nexus_exec` described as it runs; this connection offers no firmware flashing. The OpenAI package leaves out `scripts/pool_hook.py` (hooks only), and the bundled `pool.md` says the hook ships only with the full plugin; its negative case 1 no longer depends on the connection mode. gateway-tools.json from the monorepo catalog at 82bd4a5 (main, #316).

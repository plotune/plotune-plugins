# Plotune Plugins

Plugin marketplace for [Plotune](https://www.plotune.net). It packages each plugin for **Claude Code**, **Codex**, **OpenCode**, **GitHub Copilot CLI** and **Cursor**; every tool except Cursor has been verified (see below). One repository, one shared body per plugin, thin per-tool manifests.

> **Trust notice.** Plugins can ship scripts your agent may run and MCP servers that reach external services or hardware. Install only what you trust, read what a plugin contains first, and see [SECURITY.md](SECURITY.md).

## Plugins

| Plugin | Version | What it does |
|---|---|---|
| [`plotune-requirements`](plugins/plotune-requirements) | 0.10.0 | Portable continuous requirements engineering: Draft decomposition, independent approval governance, review, change impact and multi-agent delivery. |
| [`plotune-nexus`](plugins/plotune-nexus) | 0.3.1 | Automotive engineering skills (CAN/DBC, A2L/XCP, UDS, AUTOSAR, safety and security work products) plus Plotune Nexus MCP workflows for hardware execution, artifacts and diagnostics. You enter your own Nexus device's MCP URL when enabling it. |
| [`plotune-stream`](plugins/plotune-stream) | 0.2.1 | Connects to the Plotune Stream MCP (`stream.plotune.net`) and teaches safe, credit-aware querying of engineering event history. |

## Install and update

Users add the marketplace once per tool, then install the plugins they want. While this repository is private, every command below needs Git access to it (for example `gh auth login`). A new release reaches you when you update (see each tool below); releases are announced as [GitHub Releases](../../releases) tagged `<plugin>--v<version>`.

| Tool | Status |
|---|---|
| Claude Code | verified: install and update |
| Codex | verified: install and update |
| OpenCode | verified: skills load, install and update by pinned tag |
| GitHub Copilot CLI | verified: install and marketplace update (Copilot CLI 1.0.107) |
| Cursor | **not verified** (manifests follow Cursor's documented format) |

### Claude Code

```
/plugin marketplace add plotune/plotune-plugins
/plugin install plotune-requirements@plotune-plugins
/plugin install plotune-nexus@plotune-plugins
/plugin install plotune-stream@plotune-plugins
```

Update: `/plugin marketplace update plotune-plugins`, then `claude plugin update <plugin>@plotune-plugins`, then restart. Background auto-update is off by default; turn it on under **Marketplaces** in `/plugin`.

`plotune-nexus` asks for **Your Nexus MCP URL** when you enable it (`http://<device-ip>/mcp` on your LAN, or `https://<device-uuid>.plotune.net/mcp`) and connects to *your* device. Change it later in `/config`.

### Codex

```
codex plugin marketplace add plotune/plotune-plugins
```

Then install the plugins you want from the *Plotune Plugins* marketplace in Codex. Update: `codex plugin marketplace upgrade plotune-plugins` (installed plugins are refreshed too).

Codex plugin manifests have no per-user settings, so connect Nexus yourself: `codex mcp add plotune-nexus --url <your Nexus MCP URL>` (the `plotune-mcp-setup` skill walks through it).

### GitHub Copilot CLI

```
copilot plugin marketplace add plotune/plotune-plugins
copilot plugin install plotune-requirements@plotune-plugins
```

Update: `copilot plugin marketplace update plotune-plugins`. Tested with Copilot CLI 1.0.107: all three plugins install (12 + 24 + 1 skills), `plotune-stream` registers its MCP server, and `plotune-nexus` correctly registers none (its per-user URL is Claude-only). Copilot reads the Claude manifests, so a Copilot user sees the same plugins and versions as a Claude Code user.

### Cursor

Per Cursor's documentation, import this repository as a team marketplace (**Dashboard → Plugins & MCPs → Add Marketplace → Import from Repo**). `plotune-stream` ships an `mcp.json`; add your own Nexus server in Cursor's MCP settings. *(Not verified, see the table above: this follows Cursor's docs and has not been run.)*

### OpenCode

OpenCode installs Git packages, so pin each plugin to its release tag. This registers the plugin's skills (release tags such as `plotune-stream--v0.2.0` are created by the release workflow when a version is merged, so they exist from that point on):

```bash
opencode plugin add "git+https://github.com/plotune/plotune-plugins.git#plotune-stream--v0.2.0::path:plugins/plotune-stream"
```

Update to a new release by adding the new tag and removing the old one:

```bash
opencode plugin add    "git+https://github.com/plotune/plotune-plugins.git#plotune-stream--v0.3.0::path:plugins/plotune-stream"
opencode plugin remove "git+https://github.com/plotune/plotune-plugins.git#plotune-stream--v0.2.0::path:plugins/plotune-stream"
```

Notes: OpenCode's `plugin check` / `plugin update` did not recognise these Git entries in testing, and re-adding a moving branch stays on the cached version, so use tags. The adapter registers skills only; add MCP servers yourself in `opencode.json`. Tested with OpenCode 2.2.5: installing all three plugins from their GitHub release tags registered all 37 skills, and the tag-to-tag update flow was tested against a local clone. While the repository is private, OpenCode needs your Git credentials.

## How releases work

1. Change a plugin; bump it with `python tools/bump_version.py <plugin> <version> --note "…"` (updates every manifest, this table and the changelog).
2. CI on the pull request checks everything agrees and that every changed plugin has a higher version. (Branch protection is not available on this plan, so nothing *blocks* a direct push to `main`. Instead the same version check runs on every push to `main`, flagging an un-bumped change, and the release workflow re-runs it, plus the consistency checks, before it tags anything, so an un-bumped push is never released.)
3. Merge to `main`. The `release` workflow tags `<plugin>--v<version>` and publishes a GitHub Release from the changelog.

Claude Code only delivers an update when `version` changes, which is why step 2 exists. See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/adding-a-plugin.md](docs/adding-a-plugin.md).

## Repository layout

```
.claude-plugin/marketplace.json     Claude Code + Copilot CLI catalog
.agents/plugins/marketplace.json    Codex catalog
.cursor-plugin/marketplace.json     Cursor catalog
plugins/<name>/
  .claude-plugin/plugin.json        Claude/Copilot manifest (source of truth for name + version)
  .codex-plugin/plugin.json         Codex manifest
  .cursor-plugin/plugin.json        Cursor manifest
  package.json, index.js            OpenCode entry point (index.js is generated)
  skills/ …                         the shared body
  evals/                            behaviour tests for `claude plugin eval`
tools/                              checks, bump/release/sync scripts and their tests
```

## License

Apache-2.0, see [LICENSE](LICENSE).

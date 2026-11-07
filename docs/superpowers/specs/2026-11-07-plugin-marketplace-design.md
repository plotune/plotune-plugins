# Plotune Plugin Marketplace — Design

Date: 2026-11-07
Status: Draft for review

## Goal

`plotune/plotune-plugins` is a single public monorepo that acts as a plugin marketplace for **Claude Code**, **GitHub Copilot CLI** and **OpenAI Codex**. Users add it once per platform and receive plugin updates through each platform's native update mechanism. The first plugin is `plotune-requirements` (from `rms.zip`). The plotune nexus and stream plugins will be added later as siblings.

The repo was renamed from `plt-plugins` to `plotune-plugins` (2026-11-07) so the repo, marketplace and install commands share one name. Until it is ready the repo stays private; it becomes public when the first release is done.

## Constraints and findings

- One repo for all plugins; no per-plugin repositories.
- Plugins are versioned independently (semver per plugin).
- Claude Code and Copilot CLI both read `.claude-plugin/marketplace.json` and `.claude-plugin/plugin.json`, so they share one manifest set.
- Codex uses `.agents/plugins/marketplace.json` and `.codex-plugin/plugin.json`. Catalog entries require `category` and `policy`; local sources use `{"source":"local","path":"./plugins/<name>"}`.
- Claude detects updates by the computed `version`. It must be set only in `plugin.json`; setting it in both the plugin manifest and the marketplace entry makes `plugin.json` win silently. If `version` is not bumped, users keep their cached copy.
- Claude auto-update is off by default; each user enables it in `/plugin` → Marketplaces. Without it users run `/plugin marketplace update plotune-plugins`.
- Codex update detection is not documented as version-based; users run `codex plugin marketplace upgrade`. We keep versions in sync regardless.
- Skill content is platform-neutral Markdown and is shared; only manifests differ.

## Layout

```
.claude-plugin/marketplace.json     # Claude + Copilot catalog, name "plotune-plugins"
.agents/plugins/marketplace.json    # Codex catalog
plugins/
  plotune-requirements/
    .claude-plugin/plugin.json      # source of truth for name + version
    .codex-plugin/plugin.json       # same name/version + Codex "interface" block
    skills/ docs/ schema/ scripts/ templates/ tests/ examples/ migrations/
    README.md
    CHANGELOG.md
  (later) plotune-nexus/, plotune-stream/
tools/check_manifests.py
.github/workflows/validate.yml
docs/adding-a-plugin.md
README.md
.gitignore                          # ignores rms.zip
```

## Plugin import (`plotune-requirements`)

- Unpack `rms.zip` into `plugins/plotune-requirements/`.
- The export's root `plugin.json` (agent-plugins schema with `extensions.com.openai`) is split into:
  - `.claude-plugin/plugin.json`: `name`, `version`, `description`, `author`, `keywords`, `skills`.
  - `.codex-plugin/plugin.json`: the existing file, kept as is (it already carries the `interface` block).
- The root `plugin.json` is removed after the split.
- Version stays `0.8.2`; the first marketplace release is not a version bump.
- `rms.zip` is not committed.

## Catalogs

Marketplace name: `plotune-plugins`, owner `plotune`.

- `.claude-plugin/marketplace.json`: entry `{ name, source: "./plugins/plotune-requirements", description }`. No `version` in entries.
- `.agents/plugins/marketplace.json`: entry with `source.source = "local"`, `path`, `policy { installation: AVAILABLE, authentication: ON_INSTALL }`, `category: Productivity`; `interface.displayName` = "Plotune Plugins".

## User commands (documented in root README)

```
Claude Code:  /plugin marketplace add plotune/plotune-plugins
              /plugin install plotune-requirements@plotune-plugins
              (optional) enable auto-update in /plugin → Marketplaces
Copilot CLI:  copilot plugin marketplace add plotune/plotune-plugins
              copilot plugin install plotune-requirements@plotune-plugins
Codex:        codex plugin marketplace add plotune/plotune-plugins
              codex plugin marketplace upgrade plotune-plugins   # to update
```

Exact Copilot/Codex command forms are verified when writing the README, against the installed CLIs where available.

## Release flow

1. Change plugin files.
2. Bump `version` in both of the plugin's manifests and add a `CHANGELOG.md` entry.
3. Merge to `main` (merging is the release; there is no deploy step).
4. Optionally tag `plotune-requirements--v<version>`.

## Drift check (`tools/check_manifests.py`)

Plain Python, no dependencies. Exit non-zero if:

- a plugin's `name` or `version` differs between its two manifests;
- a directory under `plugins/` is missing from either catalog, or a catalog entry has no directory;
- a catalog entry's name differs from its plugin manifest name;
- a Claude catalog entry sets `version`;
- a Codex catalog entry lacks `category` or `policy`;
- any JSON file fails to parse.

## CI (`.github/workflows/validate.yml`)

On pull requests and pushes to `main`: run `tools/check_manifests.py`, `claude plugin validate .` (if the CLI can be installed in CI; otherwise skipped with a note), and each plugin's tests (`python -m unittest discover -s tests` inside `plugins/plotune-requirements`).

## Adding nexus and stream later

Each gets `plugins/<name>/` with both manifests plus catalog entries in both files. They are expected to be MCP-based, so they may include `.mcp.json` and skills. `docs/adding-a-plugin.md` records the steps and the drift-check rules. No scaffolding generator until the first addition proves one is needed.

## Out of scope

- Making the repo public, org-level distribution, or marketplace submissions.
- Plugin dependencies between plugins.
- A manifest generator; manifests are hand-written and checked.

## Testing

- `check_manifests.py` is run against the real tree and against deliberately broken copies (version mismatch, missing catalog entry, `version` in an entry) to confirm each rule fails.
- The imported plugin's existing test suite must still pass from its new location.
- `claude plugin validate .` passes locally; the marketplace can be added from the local path in Claude Code and `plotune-requirements` installs.

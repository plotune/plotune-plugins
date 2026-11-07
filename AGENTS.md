# Working in plotune-plugins

A monorepo marketplace for Plotune plugins, packaged for Claude Code, Codex, OpenCode, GitHub Copilot CLI and Cursor (see "Verified vs not" below). Each plugin under `plugins/<name>/` has one shared body (`skills/`, `scripts/`, `references/`, …) and thin per-tool manifests.

## The rule that matters most

**If you change anything functional in `plugins/<name>/`, bump that plugin's version** — otherwise Claude Code users who already installed it never receive the change.

```bash
python tools/bump_version.py <plugin> <new-version> --note "what changed"
```

That one command updates `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `package.json`, the version table in `README.md` and `CHANGELOG.md`. Do not edit versions by hand. Changes to a plugin's `CHANGELOG.md`, `README.md`, `tests/` and `evals/` alone do not need a bump. Merging to `main` is the release: `.github/workflows/release.yml` tags `<plugin>--v<version>` and publishes a GitHub Release.

## Before you finish, run

```bash
python tools/check_manifests.py      # manifests, catalogs, README table, metadata, asset paths
python tools/check_skills.py         # SKILL.md frontmatter
python tools/check_evals.py          # eval suites are well-formed
python tools/check_mcp_urls.py --offline
python tools/sync_opencode.py --check
python -I -m unittest discover -s tools/tests
node --test tools/tests/opencode-adapter.test.mjs
python tools/check_version_bumps.py --base origin/main   # in a branch with plugin changes
claude plugin validate .
```

## Layout and ownership

| Path | What | Edit by hand? |
|---|---|---|
| `plugins/<n>/.claude-plugin/plugin.json` | Claude + Copilot manifest, the source of truth for name and version | yes (not `version`) |
| `plugins/<n>/.codex-plugin/plugin.json` | Codex manifest (+ `interface` block) | yes (not `version`) |
| `plugins/<n>/.cursor-plugin/plugin.json`, `package.json` | Cursor / OpenCode | yes (not `version`) |
| `plugins/<n>/index.js` | OpenCode adapter | **no**: generated from `tools/opencode-adapter.js` by `tools/sync_opencode.py` |
| `.claude-plugin/`, `.agents/plugins/`, `.cursor-plugin/` `marketplace.json` | catalogs (Claude+Copilot / Codex / Cursor) | yes; Claude entries never carry `version` |
| `tools/` | repo tooling and its tests | yes, test-first |

## Conventions

- Plugin `name` equals its directory name, kebab-case. Display names ("Plotune Nexus") go in `displayName` / `interface.displayName`; changing `name` breaks installs.
- A skill's frontmatter `name` equals its directory; `description` is at most 1024 characters and says *when to use it*.
- **Per-user MCP URLs** (Nexus) must never be a fixed URL and never live in a root `.mcp.json` (Codex/Copilot would load an unresolved placeholder). Claude's `userConfig` + `mcp/claude-nexus.mcp.json` is the pattern; other tools use their own `mcp add`.
- Codex `defaultPrompt`: at most 3 entries, each at most 128 characters (it truncates longer ones).
- Never commit secrets, tokens, device UUIDs, `.env` files, or `plugins/*/evals/results/`.
- Tooling is Python standard library only (plus Node for the adapter test). New behaviour in `tools/` gets a test that fails first.
- `claude plugin eval` calls a model and costs money. Run it deliberately (see `CONTRIBUTING.md`), not in loops.

## Verified vs not

Verified end to end: Claude Code, Codex and GitHub Copilot CLI (1.0.107) install and update; OpenCode loads the adapter and registers every skill (tested against OpenCode 2.2.5), installs from the GitHub release tags, and updates by pinned tag (the update flow was tested against a local clone). Not verified: Cursor (a desktop app, not available where this was built). Its manifests follow Cursor's documentation — say so rather than claiming it works.

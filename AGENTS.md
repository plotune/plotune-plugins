# Working in plotune-plugins

A monorepo marketplace for Plotune plugins, packaged for Claude Code, Codex, OpenCode, GitHub Copilot CLI and Cursor (see "Verified vs not" below). Each plugin under `plugins/<name>/` has one shared body (`skills/`, `scripts/`, `references/`, …) and thin per-tool manifests.

## The rule that matters most

**If you change anything functional in `plugins/<name>/`, bump that plugin's version** — otherwise Claude Code users who already installed it never receive the change.

```bash
python tools/bump_version.py <plugin> <new-version> --note "what changed"
```

That one command updates `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `package.json`, the version table in `README.md` and `CHANGELOG.md`. Do not edit versions by hand. Changes to a plugin's `CHANGELOG.md`, `README.md`, `tests/` and `evals/` alone do not need a bump. There is no CI/CD in this repo: merging to `main` with a higher version is the release for Claude Code, and nobody tags or publishes GitHub Releases automatically. Run the checks above by hand.

## Before you finish, run

```bash
python tools/check_manifests.py      # manifests, catalogs, README table, metadata, asset paths
python tools/check_skills.py         # SKILL.md frontmatter
python tools/check_evals.py          # eval suites are well-formed
python tools/check_mcp_urls.py --offline
python tools/sync_opencode.py --check
python tools/sync_bundles.py --check      # bundled copies in plugins/plotune match their source
python tools/check_gateway_tools.py       # skills in plugins/plotune name only gateway tools
python tools/build_claude_directory.py --check   # directory/claude/plotune matches plugins/plotune
python -I -m unittest discover -s tools/tests
node --test tools/tests/opencode-adapter.test.mjs
python tools/package_openai.py plotune    # builds dist/ (gitignored) and validates the OpenAI ZIP
python tools/check_version_bumps.py --base origin/main   # in a branch with plugin changes
claude plugin validate .
```

## Layout and ownership

| Path | What | Edit by hand? |
|---|---|---|
| `plugins/<n>/.claude-plugin/plugin.json` | Claude + Copilot manifest, the source of truth for name and version | yes (not `version`) |
| `plugins/<n>/.codex-plugin/plugin.json` | Codex manifest (+ `interface` block) | yes (not `version`) |
| `plugins/<n>/.cursor-plugin/plugin.json`, `package.json` | Cursor / OpenCode | yes (not `version`) |
| `plugins/<n>/.openai-plugin/plugin.json` | OpenAI plugin manifest (Agent Plugins schema, listing fields under `extensions.com.openai`); `tools/package_openai.py` copies it to the ZIP root and fills in `version` | yes (no `version` key) |
| `plugins/<n>/index.js` | OpenCode adapter | **no**: generated from `tools/opencode-adapter.js` by `tools/sync_opencode.py` |
| `.claude-plugin/`, `.agents/plugins/`, `.cursor-plugin/` `marketplace.json` | catalogs (Claude+Copilot / Codex / Cursor) | yes; Claude entries never carry `version` |
| `plugins/plotune/{skills/<13 requirements skills>,scripts,schema,templates,migrations,docs,examples,hooks}` | copies of `plugins/plotune-requirements`, declared in `tools/bundles.json` | **no**: edit the source, then `python tools/sync_bundles.py` |
| `directory/claude/plotune/` | the Claude directory edition of `plotune` (what the directory submission points at): only Markdown, JSON and PNG, no hooks, scripts or package files | **no**: `python tools/build_claude_directory.py` (also after every `plotune` change or version bump) |
| `plugins/plotune/references/gateway-tools.json` | gateway tool names, generated from the monorepo catalog | **no**: `python tools/generate_gateway_tools.py <monorepo>/packages/contracts/mcp-catalog` |
| `tools/` | repo tooling and its tests | yes, test-first |

## Conventions

- **`plotune` bundles `plotune-requirements`.** A change to a bundled path of the source plugin changes the `plotune` copy too: run `python tools/sync_bundles.py` and bump both plugins (`plotune-requirements` for the source change, `plotune` for the copy). `plotune`'s own skills (`plotune-orientation`, `stream-orientation`, `nexus-cloud-orientation`) use gateway tool names only; `tools/check_gateway_tools.py` enforces it. After a catalog change in the monorepo, regenerate `gateway-tools.json` and review the diff.
- Plugin `name` equals its directory name, kebab-case. Display names ("Plotune Nexus") go in `displayName` / `interface.displayName`; changing `name` breaks installs.
- A skill's frontmatter `name` equals its directory; `description` is at most 1024 characters and says *when to use it*.
- **Per-user MCP URLs** (Nexus) must never be a fixed URL and never live in a root `.mcp.json` (Codex/Copilot would load an unresolved placeholder). Claude's `userConfig` + `mcp/claude-nexus.mcp.json` is the pattern; other tools use their own `mcp add`.
- Codex `defaultPrompt`: at most 3 entries, each at most 128 characters (it truncates longer ones).
- Never commit secrets, tokens, device UUIDs, `.env` files, or `plugins/*/evals/results/`.
- Tooling is Python standard library only (plus Node for the adapter test). New behaviour in `tools/` gets a test that fails first.
- `claude plugin eval` calls a model and costs money. Run it deliberately (see `CONTRIBUTING.md`), not in loops.

## Verified vs not

Verified end to end: Claude Code, Codex and GitHub Copilot CLI (1.0.107) install and update; OpenCode loads the adapter and registers every skill (tested against OpenCode 2.2.5), installs from the GitHub release tags, and updates by pinned tag (the update flow was tested against a local clone). Not verified: Cursor (a desktop app, not available where this was built). Its manifests follow Cursor's documentation — say so rather than claiming it works.

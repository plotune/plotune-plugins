# Adding a plugin

1. Create `plugins/<name>/` (kebab-case `<name>`; it must equal the manifest `name`).
2. Add `plugins/<name>/.claude-plugin/plugin.json` with `name`, `version`, `description`, `author`, `license` (`Apache-2.0`), `homepage`, `repository`, `keywords`, and `skills: "./skills/"` if it ships skills. Add `displayName` for the human-readable name.
3. Add `plugins/<name>/.codex-plugin/plugin.json` with the **same `name` and `version`** plus the same `license`/`homepage`/`repository` and an `interface` block (`displayName`, `shortDescription`, `longDescription`, `developerName`, `category`, `websiteURL`, `privacyPolicyURL`, `brandColor`, `composerIcon`, `logo`, and up to 3 `defaultPrompt` entries of at most 128 characters).
4. Add `plugins/<name>/.cursor-plugin/plugin.json` (`name`, `version`, `description`, `author`, `license`, `homepage`, `repository`).
5. Copy `assets/logo.png` and `assets/icon.png` from another plugin (or provide your own) and point `interface.logo` / `composerIcon` at them.
6. Write skills as `skills/<skill>/SKILL.md` (frontmatter `name` = folder name, `description` ≤ 1024 characters saying when to use it).
7. Add one entry to each catalog:
   - `.claude-plugin/marketplace.json`: `{ "name", "source": "./plugins/<name>", "description", "category" }`. **No `version`.**
   - `.agents/plugins/marketplace.json`: `source` `{"source":"local","path":"./plugins/<name>"}`, `policy` `{"installation":"AVAILABLE","authentication":"ON_INSTALL"}`, `category`.
   - `.cursor-plugin/marketplace.json`: `{ "name", "source": "./plugins/<name>", "description", "license" }`.
8. Add a row to the plugin table in the root `README.md` (`| [`<name>`](plugins/<name>) | <version> | … |`).
9. Generate the OpenCode entry point: `python tools/sync_opencode.py` (creates `index.js` and `package.json`).
10. Add `README.md` (with an install line), `CHANGELOG.md` (`## <version> — <note>`) and at least two eval cases under `evals/` (see CONTRIBUTING.md).

## MCP servers

- **Fixed endpoint** (like Stream): add a root `.mcp.json` with `{"type":"http","url":"https://…"}` and `"mcpServers": "./.mcp.json"` in both manifests; add `mcp.json` (same content) for Cursor. `python tools/check_mcp_urls.py` checks the URL is alive.
- **Per-user endpoint** (like Nexus): do **not** put a placeholder in a root `.mcp.json`. For Claude Code, declare `userConfig` in `plugin.json` and reference it as `${user_config.<key>}` from a non-default file such as `mcp/claude-<name>.mcp.json` (set `mcpServers` in the Claude manifest only). Document `codex mcp add` / `opencode mcp add` for the other tools.

## Before opening the PR

Run the checks in [AGENTS.md](../AGENTS.md). CI runs the same ones.

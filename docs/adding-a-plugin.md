# Adding a plugin

1. Create `plugins/<name>/` (kebab-case `<name>`).
2. Add `plugins/<name>/.claude-plugin/plugin.json` with `name`, `version`, `description`, `author` (and `skills: "./skills"` if it ships skills).
3. Add `plugins/<name>/.codex-plugin/plugin.json` with the **same `name` and `version`** plus an `interface` block (`displayName`, `shortDescription`, `longDescription`, `developerName`, `category`).
4. MCP-based plugins may add a `.mcp.json` at the plugin root.
5. Add an entry to `.claude-plugin/marketplace.json`: `{ "name", "source": "./plugins/<name>", "description" }`. **No `version`.**
6. Add an entry to `.agents/plugins/marketplace.json`: `source` `{"source":"local","path":"./plugins/<name>"}`, `policy` `{"installation":"AVAILABLE","authentication":"ON_INSTALL"}`, and `category`.
7. Add `CHANGELOG.md` and a README with an install line (`/plugin install <name> --marketplace plotune/plotune-plugins`).
8. Run `python tools/check_manifests.py` and `claude plugin validate .`, add the plugin to the table in the root README, and open a PR. CI runs the same checks.

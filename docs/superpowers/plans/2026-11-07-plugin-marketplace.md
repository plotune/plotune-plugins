# Plotune Plugin Marketplace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `plotune/plotune-plugins` into a monorepo marketplace serving `plotune-requirements` to Claude Code, Copilot CLI and Codex, with a drift check and CI.

**Architecture:** One shared plugin body under `plugins/<name>/` with two hand-written manifests (`.claude-plugin/plugin.json` read by Claude and Copilot; `.codex-plugin/plugin.json` for Codex) and two catalogs (`.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`). A dependency-free Python script verifies the manifests and catalogs agree; CI runs it plus the plugin's own tests.

**Tech Stack:** JSON manifests, Python 3 stdlib (`unittest`, `json`, `pathlib`), GitHub Actions, `claude plugin validate`.

**Spec:** `docs/superpowers/specs/2026-11-07-plugin-marketplace-design.md`

## Global Constraints

- Marketplace name `plotune-plugins`, owner `plotune`; repo `plotune/plotune-plugins`.
- Plugin `plotune-requirements` stays at version `0.8.2` (import is not a version bump).
- `version` is set only in plugin manifests, never in a Claude catalog entry.
- Claude/Copilot catalog entry source: `"./plugins/plotune-requirements"`.
- Codex entry: `source` = `{"source":"local","path":"./plugins/plotune-requirements"}`, `policy` = `{"installation":"AVAILABLE","authentication":"ON_INSTALL"}`, `category` = `"Productivity"`; `interface.displayName` = `"Plotune Plugins"`.
- `rms.zip` is never committed.
- `tools/check_manifests.py` uses the Python standard library only.
- Every commit message ends with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- All JSON read and written as UTF-8 (author name is `Veysel Kantarcılar`).

## Review Focus

- Non-ASCII author name: Codex manifest stores `ı` escapes, Claude manifest stores the literal character; the checker must compare parsed values, not text (Task 3).
- A directory in `plugins/` with no manifest, or only one of the two manifests: reported as an error naming the missing path, not a crash (Task 3).
- Malformed JSON in any manifest or catalog: reported as an error naming the file, not a traceback (Task 3).
- Stray non-directory files in `plugins/` (e.g. `.DS_Store`, `.gitkeep`): ignored (Task 3).
- Duplicate plugin names in a catalog: reported (Task 3).
- Imported plugin's existing tests depend on its own relative paths: must pass from the new location (Task 1).

---

### Task 1: Import `plotune-requirements`

**Files:**
- Create: `plugins/plotune-requirements/` (contents of `rms.zip`), `plugins/plotune-requirements/.claude-plugin/plugin.json`, `plugins/plotune-requirements/CHANGELOG.md`
- Delete (from the extracted tree): `plugins/plotune-requirements/plugin.json`
- Modify: `.gitignore` (create)

**Interfaces:**
- Produces: plugin dir `plugins/plotune-requirements/` with `.claude-plugin/plugin.json` (`name`, `version` `0.8.2`) and unchanged `.codex-plugin/plugin.json`; consumed by Tasks 2–6.

- [ ] **Step 1: Extract into a fresh directory**

Run: `mkdir -p plugins/plotune-requirements && unzip -q rms.zip -d plugins/plotune-requirements`
Expected: tree contains `skills/`, `.codex-plugin/plugin.json`, `tests/`, root `plugin.json`.

- [ ] **Step 2: Run the plugin's tests from the new location (baseline)**

Run: `cd plugins/plotune-requirements && python3 -I -m unittest discover -s tests -v`
Expected: all pass. If any fail because of path assumptions, fix only the path assumption in the test and note it in the commit message.

- [ ] **Step 3: Create `.claude-plugin/plugin.json`**

Fields copied verbatim from the old root `plugin.json`: `name`, `version`, `description`, `author`, `keywords`; plus `"skills": "./skills"`. Omit `$schema` and `extensions`. UTF-8, literal `ı` (no escapes).

- [ ] **Step 4: Remove root `plugin.json`; write `CHANGELOG.md`**

Changelog has one entry `## 0.8.2 — initial marketplace import` .

- [ ] **Step 5: Add `.gitignore` with `rms.zip`; verify tests again**

Run: `cd plugins/plotune-requirements && python3 -I -m unittest discover -s tests` then `git status --short`
Expected: tests pass; `rms.zip` not listed.

- [ ] **Step 6: Commit**

```bash
git add .gitignore plugins/plotune-requirements
git commit -m "feat: import plotune-requirements 0.8.2 as marketplace plugin

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Task 2: Marketplace catalogs

**Files:**
- Create: `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`

**Interfaces:**
- Consumes: plugin `plotune-requirements` from Task 1.
- Produces: the two catalogs, each with one entry named `plotune-requirements`; `checker` (Task 3) reads both.

- [ ] **Step 1: Write `.claude-plugin/marketplace.json`**

`{ "name": "plotune-plugins", "description": ..., "owner": {"name": "plotune"}, "plugins": [{ "name": "plotune-requirements", "source": "./plugins/plotune-requirements", "description": <plugin description> }] }`. No `version` anywhere.

- [ ] **Step 2: Write `.agents/plugins/marketplace.json`**

`name` `plotune-plugins`, `interface.displayName` `Plotune Plugins`, one entry with the Codex `source`, `policy`, `category` from Global Constraints.

- [ ] **Step 3: Validate with Claude**

Run: `claude plugin validate .`
Expected: last line `✔ Validation passed`. If the CLI is unavailable, record that and rely on Task 6.

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin .agents
git commit -m "feat: add Claude/Copilot and Codex marketplace catalogs

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Task 3: Drift check (`tools/check_manifests.py`)

**Files:**
- Create: `tools/check_manifests.py`, `tools/tests/test_check_manifests.py`

**Interfaces:**
- Consumes: catalogs and manifests from Tasks 1–2.
- Produces: `check(root: pathlib.Path) -> list[str]` (empty list = OK; each string is one human-readable error) and `main(argv: list[str] | None = None) -> int` (prints errors, returns `1` if any, else `0`; optional `argv[0]` is the repo root, default = parent of `tools/`). Used by Task 4 CI.

Test helper in the test file: `make_tree(tmp: Path, **overrides) -> Path` builds a minimal valid tree (one plugin `demo`, version `1.0.0`, both manifests, both catalogs) and lets a test mutate it.

- [ ] **Step 1: Write failing tests** (one test per rule, each asserting on a substring of the error and that unrelated rules stay quiet)

`test_valid_tree_has_no_errors`; `test_version_mismatch_between_manifests` (`"1.0.0"` vs `"1.0.1"` → error contains `version`); `test_name_mismatch_between_manifests`; `test_plugin_missing_from_claude_catalog`; `test_plugin_missing_from_codex_catalog`; `test_catalog_entry_without_directory`; `test_catalog_entry_name_differs_from_manifest_name`; `test_claude_catalog_entry_sets_version`; `test_codex_entry_missing_category`; `test_codex_entry_missing_policy`; `test_duplicate_catalog_names`; `test_missing_codex_manifest_names_the_path`; `test_malformed_json_names_the_file` (no exception raised); `test_stray_files_in_plugins_dir_ignored`; `test_non_ascii_author_does_not_matter` (escaped vs literal `ı` in the two manifests, otherwise equal → no errors); `test_main_returns_1_on_error_and_0_on_ok`; `test_real_repo_tree_passes` (runs `check` on the actual repo root).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -I -m unittest discover -s tools/tests -v`
Expected: FAIL / ImportError (`check_manifests` not defined).

- [ ] **Step 3: Implement `check` and `main` in `tools/check_manifests.py`**

Load JSON with `encoding="utf-8"`, catching `OSError`/`json.JSONDecodeError` into error strings that include the file path. Iterate `sorted(p for p in (root/"plugins").iterdir() if p.is_dir())`. Rules exactly as listed in the spec's "Drift check" section; compare only `name` and `version` across manifests. `if __name__ == "__main__": raise SystemExit(main())`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -I -m unittest discover -s tools/tests -v` and `python3 tools/check_manifests.py`
Expected: all tests pass; script exits 0 with no output (or `OK`).

- [ ] **Step 5: Commit**

```bash
git add tools
git commit -m "feat: add manifest/catalog drift check with tests

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Task 4: CI workflow

**Files:**
- Create: `.github/workflows/validate.yml`

**Interfaces:**
- Consumes: `tools/check_manifests.py` (Task 3), plugin tests (Task 1).

- [ ] **Step 1: Write the workflow**

Triggers: `pull_request`, `push` to `main`. One job on `ubuntu-latest`, `actions/checkout@v4`, `actions/setup-python@v5` (3.12). Steps: (1) `python tools/check_manifests.py`; (2) `python -I -m unittest discover -s tools/tests`; (3) `cd plugins/plotune-requirements && python -I -m unittest discover -s tests`; (4) `claude plugin validate .` via `npm i -g @anthropic-ai/claude-code`, marked `continue-on-error: true` with a comment that it is advisory until the install step is confirmed in CI.

- [ ] **Step 2: Lint the YAML**

Run: `python3 -c "import yaml,sys;yaml.safe_load(open('.github/workflows/validate.yml'))"`
Expected: no error. (If PyYAML is absent, use `gh workflow` after push in Task 6 instead.)

- [ ] **Step 3: Commit**

```bash
git add .github
git commit -m "ci: validate manifests and plugin tests

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Task 5: Documentation

**Files:**
- Create: `README.md`, `docs/adding-a-plugin.md`

**Interfaces:**
- Consumes: layout and commands from the spec.

- [ ] **Step 1: Verify the CLI command forms**

Run: `claude plugin marketplace --help`; `copilot plugin marketplace --help`; `codex plugin marketplace --help` (whichever are installed).
Expected: the `add`/`update`/`upgrade` forms used in the README match; correct the README wherever the help disagrees with the spec.

- [ ] **Step 2: Write `README.md`**

Sections: what this is; per-platform install and update commands (Claude, Copilot, Codex, with the note that Claude auto-update is off by default and enabled in `/plugin` → Marketplaces); plugin list table (`plotune-requirements` 0.8.2); release flow (bump both manifests + changelog, merge, optional tag `plotune-requirements--v<version>`); link to `docs/adding-a-plugin.md`; Apache-2.0 note.

- [ ] **Step 3: Write `docs/adding-a-plugin.md`**

Checklist: create `plugins/<name>/` with both manifests (same `name`/`version`); add one entry to each catalog (Claude entry without `version`; Codex entry with `policy` and `category`); optional `.mcp.json` for MCP-based plugins; run `python tools/check_manifests.py` and `claude plugin validate .`.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/adding-a-plugin.md
git commit -m "docs: add README and adding-a-plugin guide

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

### Task 6: End-to-end verification and push

**Files:** none modified unless a check fails.

- [ ] **Step 1: Full local check**

Run: `python3 tools/check_manifests.py && python3 -I -m unittest discover -s tools/tests && (cd plugins/plotune-requirements && python3 -I -m unittest discover -s tests) && claude plugin validate .`
Expected: all succeed.

- [ ] **Step 2: Install from the local marketplace in Claude Code**

Run: `claude plugin marketplace add . && claude plugin install plotune-requirements@plotune-plugins && claude plugin list`
Expected: `plotune-requirements@plotune-plugins` shown `✔ enabled`. Afterwards `claude plugin marketplace remove plotune-plugins` to clean up.

- [ ] **Step 3: Confirm break detection**

Temporarily change the Codex manifest version, run `python3 tools/check_manifests.py` (expect exit 1 with a `version` error), then `git checkout` the file.

- [ ] **Step 4: Push and confirm CI**

Run: `git push -u origin main` then `gh run watch`
Expected: workflow succeeds. Pushing is outward-facing: ask the user before running this step.

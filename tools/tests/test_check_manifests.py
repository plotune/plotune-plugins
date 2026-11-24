import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import check_manifests  # noqa: E402

REPO_ROOT = TOOLS.parent


def dump(path: Path, obj, ensure_ascii=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=ensure_ascii, indent=2) + "\n", encoding="utf-8")


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


META = {"license": "Apache-2.0", "homepage": "https://example.com/demo",
        "repository": "https://github.com/example/demo"}


def make_tree(root: Path) -> Path:
    """Minimal valid tree: one plugin 'demo' 1.0.0, both manifests, both catalogs, README."""
    author = {"name": "Veysel Kantarcılar"}
    dump(root / "plugins/demo/.claude-plugin/plugin.json",
         {"name": "demo", "version": "1.0.0", "author": author, **META})
    dump(root / "plugins/demo/.codex-plugin/plugin.json",
         {"name": "demo", "version": "1.0.0", "author": author, **META}, ensure_ascii=True)
    dump(root / ".claude-plugin/marketplace.json", {
        "name": "plotune-plugins", "owner": {"name": "plotune"},
        "plugins": [{"name": "demo", "source": "./plugins/demo", "category": "productivity"}]})
    dump(root / ".agents/plugins/marketplace.json", {
        "name": "plotune-plugins",
        "plugins": [{"name": "demo",
                     "source": {"source": "local", "path": "./plugins/demo"},
                     "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                     "category": "Productivity"}]})
    (root / "README.md").write_text(
        "| Plugin | Version |\n|---|---|\n| [`demo`](plugins/demo) | 1.0.0 | Demo. |\n", encoding="utf-8")
    return root


class CheckManifestsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = make_tree(Path(self._tmp.name))

    def errors(self):
        return check_manifests.check(self.root)

    def assertOneError(self, needle):
        errs = self.errors()
        self.assertTrue(any(needle in e for e in errs), f"{needle!r} not in {errs}")

    def edit(self, rel, fn):
        p = self.root / rel
        data = load(p)
        fn(data)
        dump(p, data)

    def test_valid_tree_has_no_errors(self):
        self.assertEqual(self.errors(), [])

    def test_non_ascii_author_does_not_matter(self):
        # codex manifest is written with \u escapes, claude one with the literal character
        raw = (self.root / "plugins/demo/.codex-plugin/plugin.json").read_text(encoding="utf-8")
        self.assertIn("\\u0131", raw)
        self.assertEqual(self.errors(), [])

    def test_version_mismatch_between_manifests(self):
        self.edit("plugins/demo/.codex-plugin/plugin.json", lambda d: d.update(version="1.0.1"))
        self.assertOneError("version")

    def test_name_mismatch_between_manifests(self):
        self.edit("plugins/demo/.codex-plugin/plugin.json", lambda d: d.update(name="other"))
        self.assertOneError("name")

    def test_plugin_missing_from_claude_catalog(self):
        self.edit(".claude-plugin/marketplace.json", lambda d: d["plugins"].clear())
        self.assertOneError("demo")

    def test_plugin_missing_from_codex_catalog(self):
        self.edit(".agents/plugins/marketplace.json", lambda d: d["plugins"].clear())
        self.assertOneError("demo")

    def test_catalog_entry_without_directory(self):
        self.edit(".claude-plugin/marketplace.json",
                  lambda d: d["plugins"].append({"name": "ghost", "source": "./plugins/ghost"}))
        self.assertOneError("ghost")

    def test_catalog_entry_name_differs_from_manifest_name(self):
        self.edit(".claude-plugin/marketplace.json",
                  lambda d: d["plugins"][0].update(name="renamed"))
        self.assertOneError("renamed")

    def test_claude_catalog_entry_sets_version(self):
        self.edit(".claude-plugin/marketplace.json",
                  lambda d: d["plugins"][0].update(version="1.0.0"))
        self.assertOneError("version")

    def test_codex_entry_missing_category(self):
        self.edit(".agents/plugins/marketplace.json", lambda d: d["plugins"][0].pop("category"))
        self.assertOneError("category")

    def test_codex_entry_missing_policy(self):
        self.edit(".agents/plugins/marketplace.json", lambda d: d["plugins"][0].pop("policy"))
        self.assertOneError("policy")

    def test_duplicate_catalog_names(self):
        self.edit(".claude-plugin/marketplace.json",
                  lambda d: d["plugins"].append(dict(d["plugins"][0])))
        self.assertOneError("duplicate")

    def test_missing_codex_manifest_names_the_path(self):
        (self.root / "plugins/demo/.codex-plugin/plugin.json").unlink()
        self.assertOneError(".codex-plugin/plugin.json")

    def test_malformed_json_names_the_file(self):
        (self.root / ".agents/plugins/marketplace.json").write_text("{not json", encoding="utf-8")
        self.assertOneError(".agents/plugins/marketplace.json")

    def test_stray_files_in_plugins_dir_ignored(self):
        (self.root / "plugins/.DS_Store").write_text("x")
        (self.root / "plugins/.gitkeep").write_text("")
        self.assertEqual(self.errors(), [])

    def test_main_returns_1_on_error_and_0_on_ok(self):
        self.assertEqual(check_manifests.main([str(self.root)]), 0)
        self.edit("plugins/demo/.codex-plugin/plugin.json", lambda d: d.update(version="9.9.9"))
        self.assertEqual(check_manifests.main([str(self.root)]), 1)

    # --- final-review fixes: never crash, never pass silently on broken shapes ---

    def test_invalid_utf8_names_the_file_without_crashing(self):
        (self.root / "plugins/demo/.claude-plugin/plugin.json").write_bytes(b'{"name": "\xff"}')
        self.assertOneError("plugins/demo/.claude-plugin/plugin.json")

    def test_catalog_entry_name_is_a_list(self):
        self.edit(".claude-plugin/marketplace.json",
                  lambda d: d["plugins"].append({"name": ["x"], "source": "./plugins/x"}))
        self.assertOneError("name must be a string")

    def test_catalog_mixed_type_names_do_not_crash(self):
        self.edit(".agents/plugins/marketplace.json",
                  lambda d: d["plugins"].append({"name": 5}))
        self.assertOneError("name must be a string")

    def test_manifest_name_is_a_dict(self):
        self.edit("plugins/demo/.claude-plugin/plugin.json", lambda d: d.update(name={"a": 1}))
        self.assertOneError("name must be a string")

    def test_manifest_root_is_a_list(self):
        (self.root / "plugins/demo/.codex-plugin/plugin.json").write_text("[1]", encoding="utf-8")
        self.assertOneError("must be a JSON object")

    def test_catalog_entry_not_an_object(self):
        self.edit(".claude-plugin/marketplace.json", lambda d: d["plugins"].append("demo"))
        self.assertOneError("must be an object")

    def test_catalog_entry_without_name(self):
        self.edit(".agents/plugins/marketplace.json",
                  lambda d: d["plugins"].append({"source": {"source": "local", "path": "./plugins/x"}}))
        self.assertOneError("name must be a string")

    def test_claude_source_must_point_at_plugin_directory(self):
        self.edit(".claude-plugin/marketplace.json",
                  lambda d: d["plugins"][0].update(source="./plugins/nope"))
        self.assertOneError("./plugins/demo")

    def test_codex_source_path_must_point_at_plugin_directory(self):
        self.edit(".agents/plugins/marketplace.json",
                  lambda d: d["plugins"][0]["source"].update(path="./plugins/nope"))
        self.assertOneError("./plugins/demo")

    def test_manifest_name_must_equal_directory_name(self):
        for rel in ("plugins/demo/.claude-plugin/plugin.json", "plugins/demo/.codex-plugin/plugin.json"):
            self.edit(rel, lambda d: d.update(name="other"))
        for rel in (".claude-plugin/marketplace.json", ".agents/plugins/marketplace.json"):
            self.edit(rel, lambda d: d["plugins"][0].update(name="other"))
        self.assertOneError("directory")

    # --- metadata, extra manifests, README drift, asset paths ---

    def test_missing_metadata_in_either_manifest(self):
        for rel in ("plugins/demo/.claude-plugin/plugin.json", "plugins/demo/.codex-plugin/plugin.json"):
            for field in ("license", "homepage", "repository"):
                with self.subTest(rel=rel, field=field):
                    data = load(self.root / rel)
                    saved = data.pop(field)
                    dump(self.root / rel, data)
                    self.assertOneError(field)
                    data[field] = saved
                    dump(self.root / rel, data)

    def test_claude_catalog_entry_missing_category(self):
        self.edit(".claude-plugin/marketplace.json", lambda d: d["plugins"][0].pop("category"))
        self.assertOneError("category")

    def test_cursor_manifest_matching_is_ok_and_mismatch_fails(self):
        dump(self.root / "plugins/demo/.cursor-plugin/plugin.json", {"name": "demo", "version": "1.0.0", **META})
        self.assertEqual(self.errors(), [])
        self.edit("plugins/demo/.cursor-plugin/plugin.json", lambda d: d.update(version="2.0.0"))
        self.assertOneError("version")

    def test_package_json_version_must_match(self):
        dump(self.root / "plugins/demo/package.json", {"name": "x", "version": "1.0.0"})
        self.assertEqual(self.errors(), [])
        self.edit("plugins/demo/package.json", lambda d: d.update(version="1.0.1"))
        self.assertOneError("package.json")

    def test_cursor_catalog_must_list_every_plugin(self):
        dump(self.root / ".cursor-plugin/marketplace.json",
             {"name": "plotune-plugins", "plugins": [{"name": "demo", "source": "./plugins/demo"}]})
        self.assertEqual(self.errors(), [])
        self.edit(".cursor-plugin/marketplace.json", lambda d: d["plugins"].clear())
        self.assertOneError("cursor-plugin/marketplace.json")

    def test_readme_version_must_match_manifest(self):
        (self.root / "README.md").write_text("| [`demo`](plugins/demo) | 0.9.0 | Demo. |\n", encoding="utf-8")
        self.assertOneError("README")

    def test_readme_must_list_every_plugin_when_it_has_a_table(self):
        (self.root / "README.md").write_text("| [`other`](plugins/other) | 1.0.0 | x |\n", encoding="utf-8")
        self.assertOneError("README")

    def test_missing_readme_is_skipped(self):
        (self.root / "README.md").unlink()
        self.assertEqual(self.errors(), [])

    def test_declared_component_paths_must_exist(self):
        self.edit("plugins/demo/.codex-plugin/plugin.json", lambda d: d.update(skills="./skills/"))
        self.assertOneError("skills")
        (self.root / "plugins/demo/skills").mkdir()
        self.assertEqual(self.errors(), [])
        self.edit("plugins/demo/.codex-plugin/plugin.json",
                  lambda d: d.update(interface={"logo": "./assets/logo.png"}))
        self.assertOneError("logo")
        (self.root / "plugins/demo/assets").mkdir()
        (self.root / "plugins/demo/assets/logo.png").write_bytes(b"x")
        self.assertEqual(self.errors(), [])

    def test_mcp_servers_path_must_exist(self):
        self.edit("plugins/demo/.claude-plugin/plugin.json", lambda d: d.update(mcpServers="./mcp/x.json"))
        self.assertOneError("mcpServers")

    def test_default_prompt_limits(self):
        self.edit("plugins/demo/.codex-plugin/plugin.json",
                  lambda d: d.update(interface={"defaultPrompt": ["a", "b", "c", "d"]}))
        self.assertOneError("defaultPrompt")
        self.edit("plugins/demo/.codex-plugin/plugin.json",
                  lambda d: d.update(interface={"defaultPrompt": ["x" * 129]}))
        self.assertOneError("defaultPrompt")

    # --- review fixes: every declared path, Cursor content, README table, mcp.json copy ---

    def test_claude_icon_path_must_exist(self):
        self.edit("plugins/demo/.claude-plugin/plugin.json", lambda d: d.update(icon="./assets/nope.png"))
        self.assertOneError("icon")
        (self.root / "plugins/demo/assets").mkdir()
        (self.root / "plugins/demo/assets/nope.png").write_bytes(b"x")
        self.assertEqual(self.errors(), [])

    def test_cursor_logo_path_must_exist_with_or_without_dot_slash(self):
        dump(self.root / "plugins/demo/.cursor-plugin/plugin.json",
             {"name": "demo", "version": "1.0.0", **META, "logo": "assets/logo.png"})
        self.assertOneError("logo")
        (self.root / "plugins/demo/assets").mkdir()
        (self.root / "plugins/demo/assets/logo.png").write_bytes(b"x")
        self.assertEqual(self.errors(), [])

    def test_cursor_manifest_needs_the_same_metadata(self):
        dump(self.root / "plugins/demo/.cursor-plugin/plugin.json", {"name": "demo", "version": "1.0.0"})
        self.assertOneError("license")

    def test_readme_without_a_plugin_table_is_an_error(self):
        (self.root / "README.md").write_text("# Plugins\n\nNo table here.\n", encoding="utf-8")
        self.assertOneError("README")

    def test_cursor_mcp_json_must_match_root_mcp_json(self):
        servers = {"mcpServers": {"s": {"type": "http", "url": "https://a.example/mcp"}}}
        dump(self.root / "plugins/demo/.mcp.json", servers)
        dump(self.root / "plugins/demo/mcp.json", servers)
        self.assertEqual(self.errors(), [])
        servers["mcpServers"]["s"]["url"] = "https://b.example/mcp"
        dump(self.root / "plugins/demo/mcp.json", servers)
        self.assertOneError("mcp.json")

    # --- OpenAI (Agent Plugins) manifest: plugins/<n>/.openai-plugin/plugin.json ---

    def make_openai(self):
        pdir = self.root / "plugins/demo"
        (pdir / "assets").mkdir(exist_ok=True)
        (pdir / "assets/icon.png").write_bytes(b"x")
        (pdir / "assets/logo.png").write_bytes(b"x")
        (pdir / "skills/get-started").mkdir(parents=True, exist_ok=True)
        (pdir / "skills/get-started/SKILL.md").write_text("---\nname: get-started\ndescription: d\n---\n")
        (pdir / "references").mkdir(exist_ok=True)
        dump(pdir / "references/gateway-tools.json", {"tools": ["plotune_projects_list", "events_query"]})
        servers = {"mcpServers": {"demo": {"type": "http", "url": "https://a.example/mcp"}}}
        dump(pdir / ".mcp.json", servers)
        dump(pdir / "mcp.json", servers)
        for rel in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
            self.edit(f"plugins/demo/{rel}", lambda d: d.update(mcpServers="./.mcp.json"))
        pos = {"description": "d", "prompt": "p", "tools_triggered": "plotune_projects_list, events_query",
               "expected_behavior": "e"}
        dump(pdir / ".openai-plugin/plugin.json", {
            "$schema": check_manifests.OPENAI_SCHEMA, "name": "demo", "description": "Demo.",
            "author": {"name": "Demo"}, "homepage": "https://example.com/docs", "license": "Apache-2.0",
            "extensions": {"com.openai": {
                "interface": {
                    "displayName": "Demo", "shortDescription": "Short", "longDescription": "Long text.",
                    "developerName": "Demo", "category": "Developer Tools",
                    "websiteURL": "https://example.com", "supportURL": "https://example.com/contact",
                    "privacyPolicyURL": "https://example.com/privacy",
                    "defaultPrompt": ["One", "Two"],
                    "composerIcon": "./assets/icon.png", "logo": "./assets/logo.png"},
                "onboardingSkill": "./skills/get-started/SKILL.md",
                "review": {"test_cases": {"positive": [pos],
                                          "negative": [{"description": "n", "prompt": "q"}]}}}}})

    def edit_openai(self, fn):
        self.edit("plugins/demo/.openai-plugin/plugin.json", fn)

    def oai(self, d):
        return d["extensions"]["com.openai"]

    def test_valid_openai_manifest_passes(self):
        self.make_openai()
        self.assertEqual(self.errors(), [])

    def test_openai_schema_must_be_the_agent_plugins_one(self):
        self.make_openai()
        self.edit_openai(lambda d: d.update({"$schema": "https://example.com/x.json"}))
        self.assertOneError("$schema")

    def test_openai_name_must_equal_directory(self):
        self.make_openai()
        self.edit_openai(lambda d: d.update(name="other"))
        self.assertOneError("name")

    def test_openai_unknown_top_level_key_is_rejected(self):
        self.make_openai()
        self.edit_openai(lambda d: d.update(skills="./skills/"))
        self.assertOneError("skills")

    def test_openai_version_when_present_must_match(self):
        self.make_openai()
        self.edit_openai(lambda d: d.update(version="2.0.0"))
        self.assertOneError("version")

    def test_openai_missing_listing_field(self):
        self.make_openai()
        for field in ("displayName", "shortDescription", "longDescription", "developerName", "category",
                      "websiteURL", "supportURL", "privacyPolicyURL"):
            with self.subTest(field=field):
                self.make_openai()
                self.edit_openai(lambda d: self.oai(d)["interface"].pop(field))
                self.assertOneError(field)

    def test_openai_length_limits(self):
        for field, limit in (("displayName", 30), ("shortDescription", 30), ("longDescription", 4000),
                             ("developerName", 80)):
            with self.subTest(field=field):
                self.make_openai()
                self.edit_openai(lambda d: self.oai(d)["interface"].update({field: "x" * (limit + 1)}))
                self.assertOneError(field)

    def test_openai_display_name_never_says_mcp_or_plugin(self):
        for bad in ("Demo MCP", "Demo Plugin", "Demo MCP Server"):
            with self.subTest(bad=bad):
                self.make_openai()
                self.edit_openai(lambda d: self.oai(d)["interface"].update(displayName=bad))
                self.assertOneError("displayName")

    def test_openai_urls_must_be_https(self):
        self.make_openai()
        self.edit_openai(lambda d: self.oai(d)["interface"].update(privacyPolicyURL="http://example.com/p"))
        self.assertOneError("privacyPolicyURL")

    def test_openai_default_prompts(self):
        self.make_openai()
        self.edit_openai(lambda d: self.oai(d)["interface"].update(defaultPrompt=["a", "b", "c", "d"]))
        self.assertOneError("defaultPrompt")
        self.edit_openai(lambda d: self.oai(d)["interface"].update(defaultPrompt=["x" * 129]))
        self.assertOneError("defaultPrompt")
        self.edit_openai(lambda d: self.oai(d)["interface"].update(defaultPrompt=["same", "same"]))
        self.assertOneError("unique")

    def test_openai_asset_and_onboarding_paths_must_exist(self):
        self.make_openai()
        self.edit_openai(lambda d: self.oai(d)["interface"].update(logo="./assets/missing.png"))
        self.assertOneError("logo")
        self.make_openai()
        self.edit_openai(lambda d: self.oai(d).update(onboardingSkill="./skills/none/SKILL.md"))
        self.assertOneError("onboardingSkill")

    def test_openai_review_test_case_fields(self):
        self.make_openai()
        self.edit_openai(lambda d: self.oai(d)["review"]["test_cases"]["positive"][0].pop("expected_behavior"))
        self.assertOneError("expected_behavior")
        self.make_openai()
        self.edit_openai(lambda d: self.oai(d)["review"]["test_cases"]["negative"][0].pop("prompt"))
        self.assertOneError("prompt")

    def test_openai_test_case_tools_must_exist_in_the_gateway_catalog(self):
        self.make_openai()
        self.edit_openai(lambda d: self.oai(d)["review"]["test_cases"]["positive"][0].update(
            tools_triggered="plotune_projects_list, made_up_tool"))
        self.assertOneError("made_up_tool")

    def test_openai_review_secrets_are_rejected(self):
        self.make_openai()
        self.edit_openai(lambda d: self.oai(d)["review"].update(test_credentials={"user": "x"}))
        self.assertOneError("test_credentials")

    def test_openai_needs_exactly_one_mcp_server(self):
        self.make_openai()
        servers = {"mcpServers": {"a": {"type": "http", "url": "https://a.example/mcp"},
                                  "b": {"type": "http", "url": "https://b.example/mcp"}}}
        dump(self.root / "plugins/demo/.mcp.json", servers)
        dump(self.root / "plugins/demo/mcp.json", servers)
        self.assertOneError("exactly one")

    def test_openai_mcp_url_must_be_https(self):
        self.make_openai()
        servers = {"mcpServers": {"demo": {"type": "http", "url": "http://a.example/mcp"}}}
        dump(self.root / "plugins/demo/.mcp.json", servers)
        dump(self.root / "plugins/demo/mcp.json", servers)
        self.assertOneError("https")

    def test_openai_mcp_url_must_equal_claude_and_codex(self):
        self.make_openai()
        dump(self.root / "plugins/demo/mcp.json",
             {"mcpServers": {"demo": {"type": "http", "url": "https://b.example/mcp"}}})
        self.assertOneError("mcp.json")
        # the Claude and Codex manifests must both read that same .mcp.json
        self.make_openai()
        self.edit("plugins/demo/.codex-plugin/plugin.json", lambda d: d.update(mcpServers="./other.mcp.json"))
        self.assertOneError("mcpServers")

    def test_openai_hooks_are_not_allowed_in_the_manifest(self):
        self.make_openai()
        self.edit_openai(lambda d: self.oai(d).update(hooks="./hooks/hooks.json"))
        self.assertOneError("hooks")

    def test_real_repo_tree_passes(self):
        self.assertEqual(check_manifests.check(REPO_ROOT), [])


if __name__ == "__main__":
    unittest.main()

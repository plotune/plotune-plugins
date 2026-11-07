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


def make_tree(root: Path) -> Path:
    """Minimal valid tree: one plugin 'demo' 1.0.0, both manifests, both catalogs."""
    author = {"name": "Veysel Kantarcılar"}
    dump(root / "plugins/demo/.claude-plugin/plugin.json",
         {"name": "demo", "version": "1.0.0", "author": author})
    dump(root / "plugins/demo/.codex-plugin/plugin.json",
         {"name": "demo", "version": "1.0.0", "author": author}, ensure_ascii=True)
    dump(root / ".claude-plugin/marketplace.json", {
        "name": "plotune-plugins", "owner": {"name": "plotune"},
        "plugins": [{"name": "demo", "source": "./plugins/demo"}]})
    dump(root / ".agents/plugins/marketplace.json", {
        "name": "plotune-plugins",
        "plugins": [{"name": "demo",
                     "source": {"source": "local", "path": "./plugins/demo"},
                     "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                     "category": "Productivity"}]})
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

    def test_real_repo_tree_passes(self):
        self.assertEqual(check_manifests.check(REPO_ROOT), [])


if __name__ == "__main__":
    unittest.main()

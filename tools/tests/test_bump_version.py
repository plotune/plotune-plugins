import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import bump_version  # noqa: E402

README = """# Plugins

| Plugin | Version | What it does |
|---|---|---|
| [`demo`](plugins/demo) | 1.0.0 | Demo. |
| [`other`](plugins/other) | 2.0.0 | Other. |
"""


def make_tree(root: Path, cursor=False, package=False) -> Path:
    manifest = '{\n  "name": "demo",\n  "version": "1.0.0",\n  "keywords": ["a", "b"]\n}\n'
    for rel in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        p = root / "plugins/demo" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(manifest, encoding="utf-8")
    if cursor:
        p = root / "plugins/demo/.cursor-plugin/plugin.json"
        p.parent.mkdir(parents=True)
        p.write_text(manifest, encoding="utf-8")
    if package:
        (root / "plugins/demo/package.json").write_text(manifest, encoding="utf-8")
    (root / "plugins/demo/CHANGELOG.md").write_text("# Changelog\n\n## 1.0.0 — first\n", encoding="utf-8")
    (root / "README.md").write_text(README, encoding="utf-8")
    return root


class BumpVersionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = make_tree(Path(self._tmp.name))

    def version(self, rel):
        return json.loads((self.root / "plugins/demo" / rel).read_text(encoding="utf-8"))["version"]

    def test_bumps_both_manifests_and_readme_row(self):
        bump_version.bump(self.root, "demo", "1.1.0")
        self.assertEqual(self.version(".claude-plugin/plugin.json"), "1.1.0")
        self.assertEqual(self.version(".codex-plugin/plugin.json"), "1.1.0")
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertIn("| [`demo`](plugins/demo) | 1.1.0 |", readme)
        self.assertIn("| [`other`](plugins/other) | 2.0.0 |", readme)

    def test_preserves_formatting_of_the_rest_of_the_file(self):
        bump_version.bump(self.root, "demo", "1.1.0")
        text = (self.root / "plugins/demo/.claude-plugin/plugin.json").read_text(encoding="utf-8")
        self.assertEqual(text, '{\n  "name": "demo",\n  "version": "1.1.0",\n  "keywords": ["a", "b"]\n}\n')

    def test_returns_changed_paths(self):
        changed = bump_version.bump(self.root, "demo", "1.1.0")
        self.assertIn("plugins/demo/.claude-plugin/plugin.json", changed)
        self.assertIn("README.md", changed)

    def test_changelog_note_adds_heading(self):
        bump_version.bump(self.root, "demo", "1.1.0", note="adds a thing")
        text = (self.root / "plugins/demo/CHANGELOG.md").read_text(encoding="utf-8")
        self.assertTrue(text.rstrip().endswith("## 1.1.0 — adds a thing"))

    def test_no_note_leaves_changelog_alone(self):
        bump_version.bump(self.root, "demo", "1.1.0")
        text = (self.root / "plugins/demo/CHANGELOG.md").read_text(encoding="utf-8")
        self.assertNotIn("1.1.0", text)

    def test_rejects_same_or_lower_version_and_changes_nothing(self):
        for bad in ("1.0.0", "0.9.9"):
            with self.assertRaises(ValueError):
                bump_version.bump(self.root, "demo", bad)
        self.assertEqual(self.version(".claude-plugin/plugin.json"), "1.0.0")

    def test_rejects_version_with_trailing_newline_and_changes_nothing(self):
        with self.assertRaises(ValueError):
            bump_version.bump(self.root, "demo", "1.1.0\n")
        self.assertEqual(self.version(".claude-plugin/plugin.json"), "1.0.0")

    def test_rejects_non_semver(self):
        with self.assertRaises(ValueError):
            bump_version.bump(self.root, "demo", "v2")

    def test_unknown_plugin(self):
        with self.assertRaises(ValueError):
            bump_version.bump(self.root, "nope", "1.1.0")

    def test_refuses_when_manifests_disagree_and_changes_nothing(self):
        p = self.root / "plugins/demo/.codex-plugin/plugin.json"
        p.write_text(p.read_text(encoding="utf-8").replace("1.0.0", "0.9.0"), encoding="utf-8")
        with self.assertRaises(ValueError):
            bump_version.bump(self.root, "demo", "1.1.0")
        self.assertEqual(self.version(".claude-plugin/plugin.json"), "1.0.0")

    def test_also_bumps_cursor_manifest_and_package_json_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_tree(Path(tmp), cursor=True, package=True)
            bump_version.bump(root, "demo", "1.1.0")
            for rel in (".cursor-plugin/plugin.json", "package.json"):
                data = json.loads((root / "plugins/demo" / rel).read_text(encoding="utf-8"))
                self.assertEqual(data["version"], "1.1.0")

    def test_main_returns_nonzero_on_error(self):
        self.assertEqual(bump_version.main(["demo", "1.0.0", "--root", str(self.root)]), 1)
        self.assertEqual(bump_version.main(["demo", "1.2.0", "--root", str(self.root)]), 0)


if __name__ == "__main__":
    unittest.main()

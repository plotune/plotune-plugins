import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import check_version_bumps as cvb  # noqa: E402


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=root, check=True, capture_output=True, text=True).stdout.strip()


def write_manifest(root: Path, name: str, version: str):
    p = root / "plugins" / name / ".claude-plugin" / "plugin.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"name": name, "version": version}) + "\n", encoding="utf-8")


class VersionBumpTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        git(self.root, "init", "-q", "-b", "main")
        write_manifest(self.root, "demo", "1.0.0")
        write_manifest(self.root, "other", "2.0.0")
        (self.root / "plugins/demo/skills").mkdir()
        (self.root / "plugins/demo/skills/a.md").write_text("a")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "base")
        git(self.root, "checkout", "-q", "-b", "feature")

    def commit(self, msg="change"):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", msg)

    def errors(self):
        return cvb.check(self.root, "main")

    def test_parse_version_orders_numerically(self):
        self.assertGreater(cvb.parse_version("0.10.0"), cvb.parse_version("0.9.9"))
        self.assertGreater(cvb.parse_version("1.0.1"), cvb.parse_version("1.0.0"))

    def test_parse_version_rejects_garbage(self):
        with self.assertRaises(ValueError):
            cvb.parse_version("not-a-version")

    def test_no_changes_no_errors(self):
        self.assertEqual(self.errors(), [])

    def test_changed_plugin_without_bump_fails(self):
        (self.root / "plugins/demo/skills/a.md").write_text("changed")
        self.commit()
        errs = self.errors()
        self.assertEqual(len(errs), 1)
        self.assertIn("demo", errs[0])
        self.assertIn("1.0.0", errs[0])

    def test_changed_plugin_with_bump_passes(self):
        (self.root / "plugins/demo/skills/a.md").write_text("changed")
        write_manifest(self.root, "demo", "1.0.1")
        self.commit()
        self.assertEqual(self.errors(), [])

    def test_version_going_down_fails(self):
        (self.root / "plugins/demo/skills/a.md").write_text("changed")
        write_manifest(self.root, "demo", "0.9.0")
        self.commit()
        self.assertTrue(any("demo" in e for e in self.errors()))

    def test_only_changed_plugin_is_checked(self):
        (self.root / "plugins/demo/skills/a.md").write_text("changed")
        write_manifest(self.root, "demo", "1.0.1")
        self.commit()
        self.assertFalse(any("other" in e for e in self.errors()))

    def test_changelog_readme_tests_and_evals_do_not_require_bump(self):
        for rel in ("CHANGELOG.md", "README.md", "tests/test_x.py", "evals/case/prompt.md"):
            p = self.root / "plugins/demo" / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x")
        self.commit()
        self.assertEqual(self.errors(), [])

    def test_new_plugin_needs_no_bump(self):
        write_manifest(self.root, "fresh", "0.1.0")
        self.commit()
        self.assertEqual(self.errors(), [])

    def test_changes_outside_plugins_are_ignored(self):
        (self.root / "README.md").write_text("root readme")
        (self.root / "tools").mkdir()
        (self.root / "tools/x.py").write_text("x")
        self.commit()
        self.assertEqual(self.errors(), [])

    def test_unknown_base_ref_is_reported_not_raised(self):
        errs = cvb.check(self.root, "no-such-ref")
        self.assertTrue(any("no-such-ref" in e for e in errs))

    def test_main_returns_1_on_error_and_0_on_ok(self):
        self.assertEqual(cvb.main(["--base", "main", "--root", str(self.root)]), 0)
        (self.root / "plugins/demo/skills/a.md").write_text("changed")
        self.commit()
        self.assertEqual(cvb.main(["--base", "main", "--root", str(self.root)]), 1)


if __name__ == "__main__":
    unittest.main()

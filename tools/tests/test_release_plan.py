import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import release_plan  # noqa: E402

CHANGELOG = """# Changelog

## 1.1.0 — adds a thing
Longer note for 1.1.0.

- bullet

## 1.0.0 — first release
"""


def write_plugin(root: Path, name: str, version: str, changelog=None):
    p = root / "plugins" / name / ".claude-plugin" / "plugin.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"name": name, "version": version}), encoding="utf-8")
    if changelog is not None:
        (root / "plugins" / name / "CHANGELOG.md").write_text(changelog, encoding="utf-8")


class ReleasePlanTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        write_plugin(self.root, "demo", "1.1.0", CHANGELOG)

    def test_tag_name_format(self):
        self.assertEqual(release_plan.tag_name("demo", "1.1.0"), "demo--v1.1.0")

    def test_plans_a_release_when_the_tag_is_missing(self):
        plan = release_plan.plan(self.root, existing_tags=set())
        self.assertEqual([(r.plugin, r.version, r.tag) for r in plan], [("demo", "1.1.0", "demo--v1.1.0")])

    def test_skips_versions_that_are_already_tagged(self):
        self.assertEqual(release_plan.plan(self.root, existing_tags={"demo--v1.1.0"}), [])

    def test_older_tag_does_not_block_a_new_version(self):
        plan = release_plan.plan(self.root, existing_tags={"demo--v1.0.0"})
        self.assertEqual(len(plan), 1)

    def test_notes_come_from_the_matching_changelog_section_only(self):
        notes = release_plan.plan(self.root, set())[0].notes
        self.assertIn("adds a thing", notes)
        self.assertIn("Longer note for 1.1.0.", notes)
        self.assertIn("- bullet", notes)
        self.assertNotIn("first release", notes)

    def test_notes_fall_back_when_changelog_has_no_section(self):
        write_plugin(self.root, "demo", "2.0.0", CHANGELOG)
        notes = release_plan.plan(self.root, set())[0].notes
        self.assertIn("demo", notes)
        self.assertIn("2.0.0", notes)

    def test_notes_fall_back_when_there_is_no_changelog(self):
        write_plugin(self.root, "bare", "0.1.0")
        notes = {r.plugin: r.notes for r in release_plan.plan(self.root, set())}["bare"]
        self.assertIn("0.1.0", notes)

    def test_version_prefix_is_not_confused_with_a_longer_version(self):
        write_plugin(self.root, "demo", "1.1", "## 1.10.0 — other\nwrong\n\n## 1.1 — right\nright\n")
        notes = release_plan.plan(self.root, set())[0].notes
        self.assertIn("right", notes)
        self.assertNotIn("wrong", notes)

    def test_multiple_plugins_are_sorted_and_independent(self):
        write_plugin(self.root, "alpha", "0.2.0", "## 0.2.0 — a\n")
        plan = release_plan.plan(self.root, {"alpha--v0.2.0"})
        self.assertEqual([r.plugin for r in plan], ["demo"])

    def test_plugin_without_a_version_is_skipped_not_crashed(self):
        p = self.root / "plugins/broken/.claude-plugin/plugin.json"
        p.parent.mkdir(parents=True)
        p.write_text("{not json", encoding="utf-8")
        self.assertEqual([r.plugin for r in release_plan.plan(self.root, set())], ["demo"])

    def test_main_prints_json_lines_for_the_workflow(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = release_plan.main(["--root", str(self.root), "--tags", ""])
        self.assertEqual(code, 0)
        rows = [json.loads(line) for line in buf.getvalue().splitlines()]
        self.assertEqual(rows[0]["tag"], "demo--v1.1.0")
        self.assertEqual(rows[0]["title"], "demo 1.1.0")
        self.assertIn("adds a thing", rows[0]["notes"])

    def test_main_prints_nothing_when_everything_is_tagged(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            release_plan.main(["--root", str(self.root), "--tags", "demo--v1.1.0"])
        self.assertEqual(buf.getvalue(), "")


if __name__ == "__main__":
    unittest.main()

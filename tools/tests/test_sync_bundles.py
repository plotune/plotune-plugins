import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import sync_bundles  # noqa: E402

CONFIG = {"bundles": [{
    "source": "plugins/src",
    "target": "plugins/dst",
    "paths": ["skills/one", "skills/two", "scripts", "hooks/hooks.json"],
}]}


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_tree(root: Path) -> Path:
    write(root / "tools/bundles.json", json.dumps(CONFIG))
    src = root / "plugins/src"
    write(src / "skills/one/SKILL.md", "one\n")
    write(src / "skills/two/SKILL.md", "two\n")
    write(src / "skills/two/roles/a.md", "role a\n")
    write(src / "skills/three/SKILL.md", "not declared\n")
    write(src / "scripts/tool.py", "print(1)\n")
    write(src / "hooks/hooks.json", "{}\n")
    write(src / "hooks/other.json", "{}\n")
    (root / "plugins/dst").mkdir(parents=True)
    return root


class SyncBundlesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = make_tree(Path(self._tmp.name))
        self.dst = self.root / "plugins/dst"

    def test_copies_only_declared_paths(self):
        changed = sync_bundles.sync(self.root)
        self.assertEqual((self.dst / "skills/one/SKILL.md").read_text(encoding="utf-8"), "one\n")
        self.assertEqual((self.dst / "skills/two/roles/a.md").read_text(encoding="utf-8"), "role a\n")
        self.assertEqual((self.dst / "scripts/tool.py").read_text(encoding="utf-8"), "print(1)\n")
        self.assertTrue((self.dst / "hooks/hooks.json").is_file())
        self.assertFalse((self.dst / "skills/three").exists())
        self.assertFalse((self.dst / "hooks/other.json").exists())
        self.assertIn("plugins/dst/skills/one/SKILL.md", changed)

    def test_is_idempotent(self):
        sync_bundles.sync(self.root)
        self.assertEqual(sync_bundles.sync(self.root), [])

    def test_check_reports_missing_and_does_not_write(self):
        changed = sync_bundles.sync(self.root, write=False)
        self.assertIn("plugins/dst/scripts/tool.py", changed)
        self.assertFalse((self.dst / "scripts").exists())

    def test_check_reports_a_differing_copy(self):
        sync_bundles.sync(self.root)
        (self.dst / "skills/one/SKILL.md").write_text("edited here\n", encoding="utf-8")
        self.assertEqual(sync_bundles.sync(self.root, write=False), ["plugins/dst/skills/one/SKILL.md"])

    def test_source_change_is_picked_up(self):
        sync_bundles.sync(self.root)
        (self.root / "plugins/src/scripts/tool.py").write_text("print(2)\n", encoding="utf-8")
        self.assertEqual(sync_bundles.sync(self.root), ["plugins/dst/scripts/tool.py"])
        self.assertEqual((self.dst / "scripts/tool.py").read_text(encoding="utf-8"), "print(2)\n")

    def test_extra_file_inside_a_bundled_directory_is_removed(self):
        sync_bundles.sync(self.root)
        write(self.dst / "skills/two/stale.md", "left over\n")
        self.assertEqual(sync_bundles.sync(self.root, write=False), ["plugins/dst/skills/two/stale.md"])
        sync_bundles.sync(self.root)
        self.assertFalse((self.dst / "skills/two/stale.md").exists())

    def test_files_outside_declared_paths_are_left_alone(self):
        sync_bundles.sync(self.root)
        write(self.dst / "skills/own/SKILL.md", "plugin's own skill\n")
        write(self.dst / "references/x.json", "{}\n")
        self.assertEqual(sync_bundles.sync(self.root), [])
        self.assertTrue((self.dst / "skills/own/SKILL.md").is_file())

    def test_bytecode_caches_are_ignored(self):
        write(self.root / "plugins/src/scripts/__pycache__/tool.cpython-312.pyc", "x")
        sync_bundles.sync(self.root)
        self.assertFalse((self.dst / "scripts/__pycache__").exists())
        write(self.dst / "scripts/__pycache__/tool.cpython-312.pyc", "y")
        self.assertEqual(sync_bundles.sync(self.root, write=False), [])

    def test_missing_source_path_is_an_error(self):
        config = {"bundles": [{"source": "plugins/src", "target": "plugins/dst", "paths": ["nope"]}]}
        write(self.root / "tools/bundles.json", json.dumps(config))
        with self.assertRaises(sync_bundles.BundleError):
            sync_bundles.sync(self.root)

    def test_paths_must_stay_inside_the_plugins(self):
        for bad in ("../x", "/etc", "skills/../../x"):
            config = {"bundles": [{"source": "plugins/src", "target": "plugins/dst", "paths": [bad]}]}
            write(self.root / "tools/bundles.json", json.dumps(config))
            with self.assertRaises(sync_bundles.BundleError, msg=bad):
                sync_bundles.sync(self.root)

    def test_main_check_exit_codes(self):
        self.assertEqual(sync_bundles.main(["--check", str(self.root)]), 1)
        self.assertEqual(sync_bundles.main([str(self.root)]), 0)
        self.assertEqual(sync_bundles.main(["--check", str(self.root)]), 0)

    def test_repository_config_is_valid(self):
        repo = TOOLS.parent
        config = sync_bundles.load_config(repo)
        for bundle in config:
            self.assertTrue((repo / bundle["source"]).is_dir(), bundle["source"])


if __name__ == "__main__":
    unittest.main()

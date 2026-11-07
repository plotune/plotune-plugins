import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import sync_opencode  # noqa: E402

TEMPLATE = "// adapter v1\n"


def make_tree(root: Path) -> Path:
    (root / "tools").mkdir()
    (root / "tools/opencode-adapter.js").write_text(TEMPLATE, encoding="utf-8")
    manifest = {"name": "demo", "version": "1.2.3", "description": "Demo plugin.",
                "license": "Apache-2.0", "homepage": "https://example.com/demo",
                "repository": "https://github.com/example/repo"}
    p = root / "plugins/demo/.claude-plugin/plugin.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(manifest), encoding="utf-8")
    return root


class SyncOpencodeTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = make_tree(Path(self._tmp.name))
        self.demo = self.root / "plugins/demo"

    def test_creates_index_js_and_package_json(self):
        changed = sync_opencode.sync(self.root)
        self.assertEqual((self.demo / "index.js").read_text(encoding="utf-8"), TEMPLATE)
        pkg = json.loads((self.demo / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg["name"], "demo")
        self.assertEqual(pkg["version"], "1.2.3")
        self.assertEqual(pkg["main"], "index.js")
        self.assertEqual(pkg["type"], "module")
        self.assertEqual(pkg["license"], "Apache-2.0")
        self.assertTrue(pkg["private"])
        self.assertEqual(sorted(changed), ["plugins/demo/index.js", "plugins/demo/package.json"])

    def test_is_idempotent(self):
        sync_opencode.sync(self.root)
        self.assertEqual(sync_opencode.sync(self.root), [])

    def test_refreshes_a_stale_index_js_but_keeps_existing_package_json(self):
        sync_opencode.sync(self.root)
        (self.demo / "index.js").write_text("// edited by hand\n", encoding="utf-8")
        pkg_path = self.demo / "package.json"
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        pkg["description"] = "custom"
        pkg_path.write_text(json.dumps(pkg), encoding="utf-8")
        changed = sync_opencode.sync(self.root)
        self.assertEqual(changed, ["plugins/demo/index.js"])
        self.assertEqual((self.demo / "index.js").read_text(encoding="utf-8"), TEMPLATE)
        self.assertEqual(json.loads(pkg_path.read_text(encoding="utf-8"))["description"], "custom")

    def test_check_mode_reports_without_writing(self):
        changed = sync_opencode.sync(self.root, write=False)
        self.assertEqual(len(changed), 2)
        self.assertFalse((self.demo / "index.js").exists())

    def test_main_check_exit_codes(self):
        self.assertEqual(sync_opencode.main(["--check", str(self.root)]), 1)
        self.assertEqual(sync_opencode.main([str(self.root)]), 0)
        self.assertEqual(sync_opencode.main(["--check", str(self.root)]), 0)

    def test_plugin_without_manifest_is_skipped(self):
        (self.root / "plugins/empty").mkdir()
        sync_opencode.sync(self.root)
        self.assertFalse((self.root / "plugins/empty/index.js").exists())


if __name__ == "__main__":
    unittest.main()

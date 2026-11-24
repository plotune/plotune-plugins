import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import build_claude_directory as build  # noqa: E402

MANIFEST = {
    "name": "plotune", "version": "1.2.3", "description": "d", "author": {"name": "Plotune"},
    "keywords": ["plotune"], "skills": "./skills/", "mcpServers": "./.mcp.json", "displayName": "Plotune",
    "homepage": "https://github.com/plotune/plotune-plugins/tree/main/plugins/plotune",
    "repository": "https://github.com/plotune/plotune-plugins", "license": "Apache-2.0",
    "icon": "./assets/logo.png", "privacyPolicyUrl": "https://www.plotune.net/privacy",
}


def write(path: Path, text, binary=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")


def make_repo(root: Path) -> Path:
    src = root / "plugins/plotune"
    write(src / ".claude-plugin/plugin.json", json.dumps(MANIFEST))
    write(src / ".codex-plugin/plugin.json", "{}")
    write(src / ".mcp.json", '{"mcpServers": {"plotune": {"type": "http", "url": "https://mcp.plotune.net/mcp"}}}')
    write(src / "mcp.json", "{}")
    write(src / "skills/one/SKILL.md", "---\nname: one\n---\nUse it.\n")
    write(src / "skills/two/roles/pool.md", "Role.\n")
    write(src / "assets/logo.png", b"\x89PNG\r\n\x1a\nfake", binary=True)
    write(src / "references/gateway-tools.json", "[]")
    write(src / "schema/data-model.json", "{}")
    write(src / "docs/guide.md", "Guide.\n")
    write(src / "examples/sample.json", "{}")
    write(src / "CHANGELOG.md", "# Changelog\n")
    write(src / "README.md", "Full plugin readme.\n")
    # Everything the directory refuses for a non-Verified organization.
    write(src / "scripts/pool.py", "#!/usr/bin/env python3\nprint(1)\n")
    write(src / "hooks/hooks.json", '{"hooks": {}}')
    write(src / "templates/csv/a.csv", "a,b\n")
    write(src / "migrations/m.sql", "select 1;\n")
    write(src / "evals/case/prompt.md", "Eval.\n")
    write(src / "index.js", "export default {}\n")
    write(src / "package.json", '{"name": "plotune", "main": "index.js"}')
    write(root / "LICENSE", "Apache License\n")
    write(root / build.README_TEMPLATE, "# Plotune\n\nDirectory edition, version {version}.\n")
    return root


def files(root: Path) -> set:
    return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}


class BuildClaudeDirectoryTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = make_repo(Path(self._tmp.name))
        self.out = self.root / build.TARGET

    def test_builds_only_files_the_directory_accepts(self):
        build.build(self.root)
        self.assertEqual(files(self.out), {
            ".claude-plugin/plugin.json", ".mcp.json", "skills/one/SKILL.md", "skills/two/roles/pool.md",
            "assets/logo.png", "references/gateway-tools.json", "schema/data-model.json", "docs/guide.md",
            "examples/sample.json", "CHANGELOG.md", "README.md", "LICENSE",
        })
        manifest = json.loads((self.out / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "plotune")
        self.assertEqual(manifest["version"], "1.2.3")
        self.assertEqual(manifest["homepage"], build.HOMEPAGE)
        self.assertEqual((self.out / "README.md").read_text(encoding="utf-8"), "# Plotune\n\nDirectory edition, version 1.2.3.\n")
        self.assertEqual((self.out / "LICENSE").read_text(encoding="utf-8"), "Apache License\n")

    def test_check_passes_after_build_and_reports_drift(self):
        build.build(self.root)
        self.assertEqual(build.differences(self.root), [])
        manifest = dict(MANIFEST, version="1.2.4")
        write(self.root / "plugins/plotune/.claude-plugin/plugin.json", json.dumps(manifest))
        write(self.out / "stray.md", "left over\n")
        write(self.root / "plugins/plotune/skills/one/SKILL.md", "---\nname: one\n---\nChanged.\n")
        diff = build.differences(self.root)
        self.assertIn(".claude-plugin/plugin.json", " ".join(diff))
        self.assertIn("README.md", " ".join(diff))
        self.assertIn("stray.md", " ".join(diff))
        self.assertIn("skills/one/SKILL.md", " ".join(diff))
        build.build(self.root)
        self.assertEqual(build.differences(self.root), [])
        self.assertFalse((self.out / "stray.md").exists())

    def test_refuses_files_the_directory_would_block(self):
        cases = [
            ("skills/one/run.py", "print(1)\n", "not an allowed file type"),
            ("skills/one/CLAUDE.md", "x\n", "not allowed"),
            ("skills/one/agents.md", "x\n", "not allowed"),
            ("docs/start.md", "#!/bin/sh\necho\n", "starts with #!"),
        ]
        for path, text, message in cases:
            with self.subTest(path=path):
                target = self.root / "plugins/plotune" / path
                write(target, text)
                with self.assertRaisesRegex(build.DirectoryError, message):
                    build.build(self.root)
                target.unlink()

    def test_refuses_manifest_fields_outside_the_allowed_list(self):
        write(self.root / "plugins/plotune/.claude-plugin/plugin.json", json.dumps(dict(MANIFEST, hooks="./hooks/hooks.json")))
        with self.assertRaisesRegex(build.DirectoryError, "hooks"):
            build.build(self.root)

    def test_check_command_exit_codes(self):
        self.assertEqual(build.main(["--check", str(self.root)]), 1)
        self.assertEqual(build.main([str(self.root)]), 0)
        self.assertEqual(build.main(["--check", str(self.root)]), 0)


if __name__ == "__main__":
    unittest.main()

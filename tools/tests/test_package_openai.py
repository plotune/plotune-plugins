import json
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import check_manifests  # noqa: E402
import package_openai  # noqa: E402

REPO_ROOT = TOOLS.parent


def png(size=64) -> bytes:
    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\x00\x00\x00\xff" * size for _ in range(size))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def write(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(data if isinstance(data, str) else json.dumps(data, indent=2), encoding="utf-8")


def make_tree(root: Path) -> Path:
    p = root / "plugins/demo"
    write(p / ".claude-plugin/plugin.json", {"name": "demo", "version": "1.2.3", "mcpServers": "./.mcp.json"})
    servers = {"mcpServers": {"demo": {"type": "http", "url": "https://mcp.example.com/mcp"}}}
    write(p / ".mcp.json", servers)
    write(p / "mcp.json", servers)
    write(p / "skills/get-started/SKILL.md", "---\nname: get-started\ndescription: Start here.\n---\nBody\n")
    write(p / "skills/other/SKILL.md", "---\nname: other\ndescription: Other.\n---\nBody\n")
    write(p / "assets/icon.png", png())
    write(p / "assets/logo.png", png())
    write(p / "scripts/tool.py", "print('x')\n")
    write(p / "references/gateway-tools.json", {"tools": ["plotune_projects_list"]})
    # never shipped
    write(p / "hooks/hooks.json", {"hooks": {}})
    write(p / "evals/case/prompt.md", "x")
    write(p / "index.js", "x")
    write(p / "package.json", "{}")
    write(p / ".codex-plugin/plugin.json", "{}")
    write(p / "README.md", "readme")
    write(p / "scripts/__pycache__/tool.cpython-312.pyc", b"\x00")
    pos = {"description": "d", "prompt": "p", "tools_triggered": "plotune_projects_list", "expected_behavior": "e"}
    neg = {"description": "n", "prompt": "q"}
    write(p / ".openai-plugin/plugin.json", {
        "$schema": check_manifests.OPENAI_SCHEMA, "name": "demo", "description": "Demo.",
        "extensions": {"com.openai": {
            "interface": {
                "displayName": "Demo", "shortDescription": "Short", "longDescription": "Long.",
                "developerName": "Demo", "category": "Developer Tools",
                "websiteURL": "https://example.com", "supportURL": "https://example.com/contact",
                "privacyPolicyURL": "https://example.com/privacy", "termsOfServiceURL": "https://example.com/terms",
                "composerIcon": "./assets/icon.png", "logo": "./assets/logo.png"},
            "onboardingSkill": "./skills/get-started/SKILL.md",
            "review": {"test_cases": {"positive": [pos] * 5, "negative": [neg] * 3},
                       "demo_recording_url": "https://example.com/demo"}}}})
    return root


class PackageOpenAITest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = make_tree(Path(self._tmp.name))

    def build(self):
        return package_openai.build(self.root, "demo")

    def names(self, zip_path):
        with zipfile.ZipFile(zip_path) as z:
            return set(z.namelist())

    def read(self, zip_path, name):
        with zipfile.ZipFile(zip_path) as z:
            return json.loads(z.read(name))

    def test_zip_goes_to_dist_and_has_the_root_layout(self):
        path = self.build()
        self.assertEqual(path, self.root / "dist/demo-1.2.3-openai.zip")
        names = self.names(path)
        for expected in ("plugin.json", "mcp.json", "skills/get-started/SKILL.md", "skills/other/SKILL.md",
                         "assets/icon.png", "assets/logo.png", "scripts/tool.py", "references/gateway-tools.json"):
            self.assertIn(expected, names)

    def test_nothing_from_other_tools_or_hooks_is_shipped(self):
        names = self.names(self.build())
        for banned in ("hooks/hooks.json", "evals/case/prompt.md", "index.js", "package.json", "README.md",
                       ".mcp.json", ".claude-plugin/plugin.json", ".codex-plugin/plugin.json",
                       ".openai-plugin/plugin.json", "scripts/__pycache__/tool.cpython-312.pyc"):
            self.assertNotIn(banned, names)
        self.assertFalse([n for n in names if n.startswith(("dist/", "hooks/")) or "__pycache__" in n])

    def test_plugin_json_takes_the_version_from_the_claude_manifest(self):
        manifest = self.read(self.build(), "plugin.json")
        self.assertEqual(manifest["version"], "1.2.3")
        self.assertEqual(manifest["$schema"], check_manifests.OPENAI_SCHEMA)
        self.assertEqual(list(manifest)[0], "$schema")

    def test_mcp_json_is_converted_to_the_portable_format(self):
        mcp = self.read(self.build(), "mcp.json")
        self.assertEqual(mcp, {"$schema": package_openai.MCP_SCHEMA,
                               "mcpServers": {"demo": {"type": "streamable-http",
                                                       "url": "https://mcp.example.com/mcp"}}})

    def test_build_is_deterministic(self):
        first = self.build().read_bytes()
        self.assertEqual(first, self.build().read_bytes())

    def test_valid_package_validates_without_errors_or_warnings(self):
        errors, warnings = package_openai.validate(self.build())
        self.assertEqual((errors, warnings), ([], []))

    def test_missing_owner_items_are_warnings_not_errors(self):
        def strip(d):
            o = d["extensions"]["com.openai"]
            o["interface"].pop("termsOfServiceURL")
            o["review"].pop("demo_recording_url")
            o["review"]["test_cases"]["positive"] = o["review"]["test_cases"]["positive"][:4]
        p = self.root / "plugins/demo/.openai-plugin/plugin.json"
        d = json.loads(p.read_text()); strip(d); write(p, d)
        errors, warnings = package_openai.validate(self.build())
        self.assertEqual(errors, [])
        text = "\n".join(warnings)
        for needle in ("termsOfServiceURL", "demo_recording_url", "5 positive"):
            self.assertIn(needle, text)

    def test_validate_rejects_a_package_with_hooks(self):
        path = self.build()
        bad = path.with_name("bad.zip")
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(bad, "w") as dst:
            for n in src.namelist():
                dst.writestr(n, src.read(n))
            dst.writestr("hooks/hooks.json", "{}")
        errors, _ = package_openai.validate(bad)
        self.assertTrue(any("hooks" in e for e in errors), errors)

    def test_validate_rejects_a_missing_icon_and_onboarding_skill(self):
        path = self.build()
        bad = path.with_name("bad.zip")
        with zipfile.ZipFile(path) as src, zipfile.ZipFile(bad, "w") as dst:
            for n in src.namelist():
                if n not in ("assets/logo.png", "skills/get-started/SKILL.md"):
                    dst.writestr(n, src.read(n))
        errors, _ = package_openai.validate(bad)
        text = "\n".join(errors)
        self.assertIn("assets/logo.png", text)
        self.assertIn("get-started/SKILL.md", text)

    def test_validate_rejects_small_or_non_square_icons(self):
        write(self.root / "plugins/demo/assets/icon.png", png(32))
        errors, _ = package_openai.validate(self.build())
        self.assertTrue(any("icon.png" in e and "48" in e for e in errors), errors)

    def test_validate_rejects_a_skill_without_name_or_description(self):
        write(self.root / "plugins/demo/skills/other/SKILL.md", "---\nname: other\n---\nBody\n")
        errors, _ = package_openai.validate(self.build())
        self.assertTrue(any("other/SKILL.md" in e and "description" in e for e in errors), errors)

    def test_validate_rejects_two_servers_and_non_https(self):
        path = self.build()
        for servers, needle in (
                ({"a": {"type": "streamable-http", "url": "https://a.example/mcp"},
                  "b": {"type": "streamable-http", "url": "https://b.example/mcp"}}, "exactly one"),
                ({"a": {"type": "streamable-http", "url": "http://a.example/mcp"}}, "https"),
                ({"a": {"type": "http", "url": "https://a.example/mcp"}}, "streamable-http")):
            bad = path.with_name("bad.zip")
            with zipfile.ZipFile(path) as src, zipfile.ZipFile(bad, "w") as dst:
                for n in src.namelist():
                    dst.writestr(n, json.dumps({"$schema": package_openai.MCP_SCHEMA, "mcpServers": servers})
                                 if n == "mcp.json" else src.read(n))
            errors, _ = package_openai.validate(bad)
            self.assertTrue(any(needle in e for e in errors), (needle, errors))

    def test_build_refuses_files_that_look_like_secrets(self):
        write(self.root / "plugins/demo/scripts/.env", "TOKEN=abc")
        with self.assertRaises(package_openai.PackageError):
            self.build()
        (self.root / "plugins/demo/scripts/.env").unlink()
        write(self.root / "plugins/demo/scripts/key.txt", "-----BEGIN PRIVATE KEY-----\nabc\n")
        with self.assertRaises(package_openai.PackageError):
            self.build()

    def test_build_refuses_an_invalid_source_manifest(self):
        p = self.root / "plugins/demo/.openai-plugin/plugin.json"
        d = json.loads(p.read_text()); d["name"] = "other"; write(p, d)
        with self.assertRaises(package_openai.PackageError):
            self.build()

    def test_dist_is_gitignored_in_this_repo(self):
        ignore = (REPO_ROOT / ".gitignore").read_text()
        self.assertIn("dist/", ignore.split())

    def test_main_exit_codes(self):
        self.assertEqual(package_openai.main(["demo", "--root", str(self.root)]), 0)
        p = self.root / "plugins/demo/.openai-plugin/plugin.json"
        d = json.loads(p.read_text()); d["extensions"]["com.openai"]["interface"].pop("termsOfServiceURL"); write(p, d)
        self.assertEqual(package_openai.main(["demo", "--root", str(self.root)]), 0)
        self.assertEqual(package_openai.main(["demo", "--root", str(self.root), "--strict"]), 1)

    def test_real_plotune_plugin_builds_and_validates(self):
        with tempfile.TemporaryDirectory() as out:
            path = package_openai.build(REPO_ROOT, "plotune", out_dir=Path(out))
            errors, _ = package_openai.validate(path)
            self.assertEqual(errors, [])
            names = self.names(path)
            self.assertNotIn("hooks/hooks.json", names)
            self.assertIn("skills/plotune-orientation/SKILL.md", names)

    def test_review_doc_matches_the_manifest_and_the_gateway_catalog(self):
        doc = (REPO_ROOT / "docs/plotune-review-test-cases.md").read_text(encoding="utf-8")
        manifest = json.loads((REPO_ROOT / "plugins/plotune/.openai-plugin/plugin.json").read_text(encoding="utf-8"))
        openai = manifest["extensions"]["com.openai"]
        cases = openai["review"]["test_cases"]
        self.assertEqual((len(cases["positive"]), len(cases["negative"])), (5, 3))
        for case in cases["positive"] + cases["negative"]:
            self.assertIn(f"**Prompt:** {case['prompt']}", doc)
        for prompt in openai["interface"]["defaultPrompt"]:
            self.assertIn(prompt, doc)
        tools = set(json.loads((REPO_ROOT / "plugins/plotune/references/gateway-tools.json")
                               .read_text(encoding="utf-8"))["tools"])
        named = {t for line in doc.splitlines() if line.startswith("- **Tools:**")
                 for t in __import__("re").findall(r"`([a-z][a-z0-9_]*)`", line)}
        self.assertTrue(named)
        self.assertEqual(sorted(named - tools), [])


if __name__ == "__main__":
    unittest.main()

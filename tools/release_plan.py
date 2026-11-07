#!/usr/bin/env python3
"""Work out which plugin releases still need a git tag and GitHub Release.

A plugin's current version (from .claude-plugin/plugin.json) is released as the tag
`<plugin>--v<version>` (the convention Claude Code uses to resolve plugin dependency
versions). A plugin whose current version has no tag yet is planned for release; the
release notes are the matching section of the plugin's CHANGELOG.md.

Prints one JSON object per planned release (tag, plugin, version, title, notes), nothing
when everything is already tagged. The release workflow turns each into a tag + Release.

Usage:
    python tools/release_plan.py            # existing tags come from `git tag`
    python tools/release_plan.py --tags "a--v1.0.0,b--v2.0.0"   # explicit (tests)
"""
import argparse
import json
import re
import subprocess
import sys
from collections import namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_version_bumps import parse_version  # noqa: E402

Release = namedtuple("Release", "plugin version tag notes")


def tag_name(plugin: str, version: str) -> str:
    return f"{plugin}--v{version}"


def _notes(root: Path, plugin: str, version: str) -> str:
    fallback = f"Release {plugin} {version}."
    changelog = root / "plugins" / plugin / "CHANGELOG.md"
    try:
        text = changelog.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return fallback
    # a "## <version>" heading, then everything up to the next "## " heading
    match = re.search(rf"^##\s+{re.escape(version)}(?=\s|$)[^\n]*\n(.*?)(?=^##\s|\Z)", text, re.DOTALL | re.MULTILINE)
    if not match:
        return fallback
    heading = re.search(rf"^##\s+{re.escape(version)}(?=\s|$)[^\n]*$", text, re.MULTILINE).group(0)
    title = re.sub(rf"^##\s+{re.escape(version)}\s*[—-]?\s*", "", heading).strip()
    body = match.group(1).strip()
    return "\n\n".join(part for part in (title, body) if part) or fallback


def plan(root: Path, existing_tags) -> list:
    root = Path(root)
    releases = []
    for manifest in sorted((root / "plugins").glob("*/.claude-plugin/plugin.json")):
        plugin = manifest.parent.parent.name
        try:
            version = json.loads(manifest.read_text(encoding="utf-8")).get("version")
        except (OSError, ValueError):
            continue
        try:
            parse_version(version)
        except ValueError:
            continue  # never tag a version that is not strict MAJOR.MINOR.PATCH
        tag = tag_name(plugin, version)
        if tag not in existing_tags:
            releases.append(Release(plugin, version, tag, _notes(root, plugin, version)))
    return releases


def _git_tags(root: Path) -> set:
    out = subprocess.run(["git", "tag", "--list"], cwd=root, check=True, capture_output=True, text=True).stdout
    return {line.strip() for line in out.splitlines() if line.strip()}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--tags", help="comma-separated existing tags instead of asking git")
    args = parser.parse_args(argv)
    root = Path(args.root)
    tags = {t for t in args.tags.split(",") if t} if args.tags is not None else _git_tags(root)
    for release in plan(root, tags):
        print(json.dumps({"tag": release.tag, "plugin": release.plugin, "version": release.version,
                          "title": f"{release.plugin} {release.version}", "notes": release.notes},
                         ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

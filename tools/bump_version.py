#!/usr/bin/env python3
"""Bump a plugin's version everywhere it is recorded, in one command.

Updates every manifest of the plugin (.claude-plugin, .codex-plugin, and, when present,
.cursor-plugin and package.json) plus the version column of the root README table.
With --note, also appends a heading to the plugin's CHANGELOG.md.
Edits are textual, so the rest of each file keeps its formatting.

Usage:
    python tools/bump_version.py <plugin> <new-version> [--note "what changed"]
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_version_bumps import parse_version  # noqa: E402

VERSION_FILES = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json",
                 ".cursor-plugin/plugin.json", "package.json")
_VERSION_FIELD = re.compile(r'("version"\s*:\s*")([^"]*)(")')


def _current(path: Path) -> str:
    match = _VERSION_FIELD.search(path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{path}: no version field")
    return match.group(2)


def bump(root: Path, plugin: str, new_version: str, note: str = None) -> list:
    root = Path(root)
    pdir = root / "plugins" / plugin
    if not pdir.is_dir():
        raise ValueError(f"unknown plugin {plugin!r}")
    files = [pdir / rel for rel in VERSION_FILES if (pdir / rel).is_file()]
    if not files:
        raise ValueError(f"plugins/{plugin} has no manifest")

    versions = {f: _current(f) for f in files}
    if len(set(versions.values())) != 1:
        detail = ", ".join(f"{f.relative_to(root).as_posix()}={v}" for f, v in versions.items())
        raise ValueError(f"manifests disagree, fix that first: {detail}")
    current = next(iter(versions.values()))
    if parse_version(new_version) <= parse_version(current):
        raise ValueError(f"new version {new_version} must be higher than {current}")

    changed = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        f.write_text(_VERSION_FIELD.sub(lambda m: m.group(1) + new_version + m.group(3), text, count=1),
                     encoding="utf-8")
        changed.append(f.relative_to(root).as_posix())

    readme = root / "README.md"
    if readme.is_file():
        row = re.compile(r"(\| \[`" + re.escape(plugin) + r"`\]\([^)]*\) \| )" + re.escape(current) + r"( \|)")
        text = readme.read_text(encoding="utf-8")
        updated = row.sub(lambda m: m.group(1) + new_version + m.group(2), text, count=1)
        if updated != text:
            readme.write_text(updated, encoding="utf-8")
            changed.append("README.md")

    if note:
        log = pdir / "CHANGELOG.md"
        existing = log.read_text(encoding="utf-8") if log.is_file() else "# Changelog\n"
        log.write_text(existing.rstrip("\n") + f"\n\n## {new_version} — {note}\n", encoding="utf-8")
        changed.append(log.relative_to(root).as_posix())
    return changed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("plugin")
    parser.add_argument("version")
    parser.add_argument("--note")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args(argv)
    try:
        changed = bump(Path(args.root), args.plugin, args.version, args.note)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1
    for path in changed:
        print(f"updated {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

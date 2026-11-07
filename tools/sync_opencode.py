#!/usr/bin/env python3
"""Give every plugin its OpenCode entry point.

Copies tools/opencode-adapter.js to plugins/<name>/index.js (always refreshed, so the copies
cannot drift) and creates plugins/<name>/package.json from the Claude manifest when it is
missing (an existing package.json is left alone; bump_version.py keeps its version current).

Usage:
    python tools/sync_opencode.py [--check] [repo-root]
        --check  report what is out of date and exit 1, without writing
"""
import argparse
import json
import sys
from pathlib import Path


def _package_json(manifest: dict) -> dict:
    package = {
        "name": manifest["name"],
        "version": manifest["version"],
        "description": manifest.get("description", ""),
        "type": "module",
        "main": "index.js",
        "private": True,
    }
    for key in ("license", "homepage"):
        if manifest.get(key):
            package[key] = manifest[key]
    if manifest.get("repository"):
        package["repository"] = {"type": "git", "url": manifest["repository"]}
    return package


def sync(root: Path, write: bool = True) -> list:
    """Return the repo-relative paths that were (or, with write=False, would be) changed."""
    root = Path(root)
    template = (root / "tools" / "opencode-adapter.js").read_text(encoding="utf-8")
    changed = []
    for pdir in sorted((root / "plugins").glob("*")):
        manifest_path = pdir / ".claude-plugin" / "plugin.json"
        if not manifest_path.is_file():
            continue
        index = pdir / "index.js"
        if not index.is_file() or index.read_text(encoding="utf-8") != template:
            if write:
                index.write_text(template, encoding="utf-8")
            changed.append(index.relative_to(root).as_posix())
        package = pdir / "package.json"
        if not package.is_file():
            if write:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                package.write_text(json.dumps(_package_json(manifest), ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")
            changed.append(package.relative_to(root).as_posix())
    return changed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    changed = sync(Path(args.root), write=not args.check)
    for path in changed:
        print(("out of date: " if args.check else "wrote ") + path)
    if args.check and changed:
        print("Run: python tools/sync_opencode.py")
        return 1
    if not changed:
        print("OK: OpenCode entry points are up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())

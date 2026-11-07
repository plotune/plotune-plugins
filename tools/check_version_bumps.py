#!/usr/bin/env python3
"""Fail when a plugin's files change but its version does not go up.

Claude Code treats an installed plugin as current while the `version` in its
`.claude-plugin/plugin.json` is unchanged, so a change shipped without a bump never
reaches anyone who already installed the plugin. This compares HEAD against its merge
base with a base ref (the pull request target in CI) and requires every plugin with
functional changes to raise its version.

Not counted as functional: CHANGELOG.md, README.md, tests/ and evals/.
Only the Claude manifest is compared; check_manifests.py keeps the others equal to it.

Usage:
    python tools/check_version_bumps.py [--base origin/main] [--root .]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

MANIFEST = ".claude-plugin/plugin.json"
IGNORED_FILES = {"CHANGELOG.md", "README.md"}
IGNORED_DIRS = {"tests", "evals"}
_SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def parse_version(text: str) -> tuple:
    match = _SEMVER.fullmatch(text) if isinstance(text, str) else None
    if not match:
        raise ValueError(f"not a MAJOR.MINOR.PATCH version: {text!r}")
    return tuple(int(part) for part in match.groups())


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True,
                          capture_output=True, text=True).stdout


def _version_at(root: Path, ref: str, plugin: str):
    """Version of a plugin at a git ref, or None if the manifest does not exist there."""
    try:
        raw = _git(root, "show", f"{ref}:plugins/{plugin}/{MANIFEST}")
    except subprocess.CalledProcessError:
        return None
    try:
        return json.loads(raw).get("version")
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"{MANIFEST} at {ref} cannot be read ({exc})") from exc


def _exists_at(root: Path, ref: str, plugin: str) -> bool:
    """Does the plugin directory hold any file at this ref?"""
    try:
        return bool(_git(root, "ls-tree", "-r", "--name-only", ref, f"plugins/{plugin}/").strip())
    except subprocess.CalledProcessError:
        return False


def _is_functional(parts: tuple) -> bool:
    """parts = path relative to the plugin directory."""
    if parts[-1] in IGNORED_FILES and len(parts) == 1:
        return False
    return parts[0] not in IGNORED_DIRS


def check(root: Path, base: str) -> list:
    root = Path(root)
    try:
        merge_base = _git(root, "merge-base", base, "HEAD").strip()
        changed = _git(root, "diff", "--name-only", merge_base, "HEAD").splitlines()
    except subprocess.CalledProcessError as exc:
        return [f"cannot compare against base ref {base!r}: {exc.stderr.strip() or exc}"]

    touched = set()
    for name in changed:
        parts = PurePosixPath(name).parts
        if len(parts) >= 3 and parts[0] == "plugins" and _is_functional(parts[2:]):
            touched.add(parts[1])

    errors = []
    for plugin in sorted(touched):
        try:
            before = _version_at(root, merge_base, plugin)
            if before is None:
                continue  # new plugin: nothing to bump
            if not _exists_at(root, "HEAD", plugin):
                continue  # plugin removed or renamed: nothing to bump
            after = _version_at(root, "HEAD", plugin)
            if after is None or parse_version(after) <= parse_version(before):
                errors.append(
                    f"plugins/{plugin}: files changed but version is still {after!r} "
                    f"(was {before!r}); bump it with tools/bump_version.py")
        except ValueError as exc:
            errors.append(f"plugins/{plugin}: {exc}")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args(argv)
    errors = check(Path(args.root), args.base)
    for e in errors:
        print(f"ERROR: {e}")
    if not errors:
        print("OK: every changed plugin has a higher version")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

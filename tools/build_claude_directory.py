#!/usr/bin/env python3
"""Build the Claude directory edition of the plotune plugin.

The Claude plugin directory accepts, from an organization that is not Verified, only Markdown, JSON,
YAML, text and images: no hooks, scripts, programs, package files, CSV or SQL templates, and only the
manifest fields Claude Code reads. plugins/plotune ships those for its other uses (the bundled
requirements scripts and hook, the OpenCode adapter), so the directory gets a generated copy at
directory/claude/plotune with only what it accepts. That copy is what the directory submission points
at (plugin path `directory/claude/plotune`); it is never edited by hand.

What it holds: the plugin manifest (homepage set to the public docs), the MCP config, every skill,
the JSON references, schemas and examples the skills cite, the Markdown docs, the PNG assets, the
changelog, the repository LICENSE, and a README from tools/claude-directory/README.md with {version}
filled in. The skills are unchanged: their local-workspace and AI-pool steps are already optional
("where available") and need the full plugin from the Plotune marketplace.

Usage:
    python tools/build_claude_directory.py [--check] [repo-root]
        --check  report what differs and exit 1, without writing
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

SOURCE = "plugins/plotune"
TARGET = "directory/claude/plotune"
README_TEMPLATE = "tools/claude-directory/README.md"
HOMEPAGE = "https://www.plotune.net/docs/mcp"

# Copied from the plugin when present: (path, allowed suffixes). A directory is copied whole.
COPIED = [
    (".mcp.json", {".json"}),
    ("skills", {".md"}),
    ("assets", {".png"}),
    ("references", {".json", ".md"}),
    ("schema", {".json"}),
    ("docs", {".md"}),
    ("examples", {".json"}),
    ("CHANGELOG.md", {".md"}),
]
MANIFEST_FIELDS = {"name", "version", "description", "author", "keywords", "skills", "mcpServers", "displayName",
                   "homepage", "repository", "license", "icon", "privacyPolicyUrl"}
REFUSED_NAMES = {"claude.md", "claude.local.md", "agents.md"}


class DirectoryError(Exception):
    pass


def _files(base: Path) -> list:
    if base.is_file():
        return [base]
    return sorted(p for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts)


def _checked(path: Path, rel: str, suffixes: set) -> bytes:
    if path.name.lower() in REFUSED_NAMES:
        raise DirectoryError(f"{rel}: this file name is not allowed in the directory")
    if path.suffix.lower() not in suffixes:
        raise DirectoryError(f"{rel}: not an allowed file type here ({', '.join(sorted(suffixes))})")
    data = path.read_bytes()
    if data.startswith(b"#!"):
        raise DirectoryError(f"{rel}: starts with #!")
    if path.suffix.lower() != ".png":
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise DirectoryError(f"{rel}: not UTF-8") from exc
        if "\x00" in text:
            raise DirectoryError(f"{rel}: contains a NUL byte")
    return data


def generate(root: Path) -> dict:
    """Return {relative path: bytes} of the directory edition."""
    root = Path(root)
    src = root / SOURCE
    try:
        manifest = json.loads((src / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DirectoryError(f"{SOURCE}/.claude-plugin/plugin.json: cannot read ({exc})") from exc
    extra = sorted(set(manifest) - MANIFEST_FIELDS)
    if extra:
        raise DirectoryError(f"plugin.json: fields the directory does not accept: {', '.join(extra)}")
    manifest["homepage"] = HOMEPAGE
    out = {".claude-plugin/plugin.json": (json.dumps(manifest, indent=2, ensure_ascii=False) + "\n").encode("utf-8")}
    for path, suffixes in COPIED:
        base = src / path
        if not base.exists():
            continue
        for file in _files(base):
            rel = file.relative_to(src).as_posix()
            out[rel] = _checked(file, rel, suffixes)
    try:
        template = (root / README_TEMPLATE).read_text(encoding="utf-8")
        out["LICENSE"] = (root / "LICENSE").read_bytes()
    except OSError as exc:
        raise DirectoryError(f"cannot read {exc.filename}") from exc
    out["README.md"] = template.replace("{version}", str(manifest.get("version", ""))).encode("utf-8")
    return out


def differences(root: Path) -> list:
    """What differs between the generated edition and the committed one."""
    wanted = generate(root)
    target = Path(root) / TARGET
    present = {p.relative_to(target).as_posix(): p for p in _files(target)} if target.exists() else {}
    diff = [f"missing: {rel}" for rel in sorted(set(wanted) - set(present))]
    diff += [f"differs: {rel}" for rel in sorted(set(wanted) & set(present)) if present[rel].read_bytes() != wanted[rel]]
    diff += [f"not generated: {rel}" for rel in sorted(set(present) - set(wanted))]
    return diff


def build(root: Path) -> list:
    """Write the edition, removing anything else in the target; return what changed."""
    changed = differences(root)
    wanted = generate(root)
    target = Path(root) / TARGET
    if target.exists():
        shutil.rmtree(target)
    for rel, data in wanted.items():
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return changed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("root", nargs="?", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args(argv)
    try:
        if args.check:
            diff = differences(Path(args.root))
            for line in diff:
                print(f"{TARGET}: {line}")
            if diff:
                print("Run: python tools/build_claude_directory.py")
                return 1
            print(f"OK: {TARGET} matches {SOURCE}")
            return 0
        changed = build(Path(args.root))
        print(f"{TARGET}: {len(changed)} change(s)" if changed else f"{TARGET}: up to date")
        return 0
    except DirectoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

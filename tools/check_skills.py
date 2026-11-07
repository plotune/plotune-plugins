#!/usr/bin/env python3
"""Validate SKILL.md frontmatter for every skill under plugins/*/skills/.

Rules: a skill directory contains SKILL.md; the file starts with a ---frontmatter---
block; `name` is present, lowercase-hyphenated, at most 64 characters and equal to the
directory name; `description` is present, non-empty and at most 1024 characters.

Usage:
    python tools/check_skills.py [repo-root]
"""
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_NAME = 64
MAX_DESCRIPTION = 1024


def parse_frontmatter(text: str):
    """Return {key: value} from a leading ---/--- block, or None if absent/unclosed.

    Handles plain, quoted and YAML block-scalar (> or |) values and indented
    continuation lines. It is not a full YAML parser; nested maps flatten into the
    parent key, which is enough for name and description.
    """
    match = re.match(r"^---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|$)", text, re.DOTALL)
    if not match:
        return None
    result, last = {}, None
    for raw in match.group(1).split("\n"):
        line = raw.rstrip("\r")
        colon = line.find(":")
        if colon > 0 and not line[0].isspace():
            last = line[:colon].strip()
            value = line[colon + 1:].strip()
            result[last] = "" if re.fullmatch(r"[>|][+-]?", value) else value
        elif last is not None and line.strip():
            result[last] = f"{result[last]} {line.strip()}".strip()
    for key, value in result.items():
        result[key] = re.sub(r"^([\"'])(.*)\1$", r"\2", value, flags=re.DOTALL)
    return result


def check(root: Path) -> list:
    root = Path(root)
    errors = []
    for skills_dir in sorted((root / "plugins").glob("*/skills")):
        if not skills_dir.is_dir():
            continue
        for sdir in sorted(p for p in skills_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
            rel = sdir.relative_to(root).as_posix()
            skill_md = sdir / "SKILL.md"
            if not skill_md.is_file():
                errors.append(f"{rel}: missing SKILL.md")
                continue
            try:
                frontmatter = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError) as exc:
                errors.append(f"{rel}/SKILL.md: cannot read ({exc})")
                continue
            if frontmatter is None:
                errors.append(f"{rel}/SKILL.md: missing or unclosed frontmatter")
                continue
            name = frontmatter.get("name", "")
            if not name:
                errors.append(f"{rel}/SKILL.md: name is missing")
            else:
                if not NAME_RE.match(name):
                    errors.append(f"{rel}/SKILL.md: name {name!r} must be lowercase letters, digits and hyphens")
                if len(name) > MAX_NAME:
                    errors.append(f"{rel}/SKILL.md: name is longer than {MAX_NAME} characters")
                if name != sdir.name:
                    errors.append(f"{rel}/SKILL.md: name {name!r} must equal the directory name {sdir.name!r}")
            description = frontmatter.get("description", "")
            if not description:
                errors.append(f"{rel}/SKILL.md: description is missing or empty")
            elif len(description) > MAX_DESCRIPTION:
                errors.append(f"{rel}/SKILL.md: description is {len(description)} characters, over {MAX_DESCRIPTION}")
    return errors


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent
    errors = check(root)
    for e in errors:
        print(f"ERROR: {e}")
    if not errors:
        print("OK: all skills have valid frontmatter")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

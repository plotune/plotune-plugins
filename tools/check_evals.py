#!/usr/bin/env python3
"""Structural check for plugin eval suites (plugins/*/evals/<case>/).

`claude plugin eval` scores behaviour; this only catches the mistakes that would make a
case silently meaningless: a missing or placeholder prompt, no graders, an unknown grader
type, a regex that does not compile, or a `tool_used: Skill` grader naming a skill that the
plugin does not ship. Running the evals themselves needs a model and is done by hand
before releases (see CONTRIBUTING.md).

Usage:
    python tools/check_evals.py [repo-root]
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_skills import parse_frontmatter  # noqa: E402

GRADER_TYPES = {"regex", "tool_used", "tool_order", "file_exists", "llm", "baseline"}
PLACEHOLDER = "TODO"


def _body(text: str) -> str:
    return re.sub(r"^---\r?\n.*?\r?\n---[ \t]*(?:\r?\n|$)", "", text, count=1, flags=re.DOTALL)


def _quote_problem(value: str):
    """Why a quoted YAML scalar is invalid, or None. Handles '...' (doubled '' escape) and "..." (backslash escape)."""
    if value[0] == "'":
        if len(value) < 2 or value[-1] != "'":
            return "unterminated single-quoted value"
        if "'" in value[1:-1].replace("''", ""):
            return "unescaped single quote inside a single-quoted value (double it as '')"
    elif value[0] == '"':
        i = 1
        while i < len(value) and value[i] != '"':
            i += 2 if value[i] == "\\" else 1
        if i >= len(value):
            return "unterminated double-quoted value"
        if i != len(value) - 1:
            return 'unescaped double quote inside a double-quoted value (write it as \\")'
    return None


def _check_quotes(text: str, rel: str, errors: list):
    """The eval harness skips a case whose frontmatter is invalid YAML, silently to a reader of
    the repo. Catch the usual cause: a stray quote inside a quoted value."""
    match = re.match(r"^---\r?\n(.*?)\r?\n---", text, re.DOTALL)
    if not match:
        return
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        value = value.strip()
        if sep and not line[0].isspace() and value and value[0] in "'\"":
            problem = _quote_problem(value)
            if problem:
                errors.append(f"{rel}: {key.strip()}: {problem} (invalid YAML quote; the eval would be skipped)")


def _read(path: Path, rel: str, errors: list):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"{rel}: cannot read ({exc})")
        return None


def _check_prompt(case: Path, rel: str, errors: list):
    prompt = case / "prompt.md"
    if not prompt.is_file():
        errors.append(f"{rel}: missing prompt.md")
        return
    text = _read(prompt, f"{rel}/prompt.md", errors)
    if text is None:
        return
    _check_quotes(text, f"{rel}/prompt.md", errors)
    body = _body(text).strip()
    if not body:
        errors.append(f"{rel}/prompt.md: prompt body is empty")
    elif PLACEHOLDER in body:
        errors.append(f"{rel}/prompt.md: prompt is still a TODO placeholder")


def _check_grader(path: Path, rel: str, skills: set, errors: list):
    text = _read(path, rel, errors)
    if text is None:
        return
    _check_quotes(text, rel, errors)
    front = parse_frontmatter(text)
    gtype = (front or {}).get("type")
    if not gtype:
        errors.append(f"{rel}: grader needs a frontmatter type")
        return
    if gtype not in GRADER_TYPES:
        errors.append(f"{rel}: unknown grader type {gtype!r}")
        return
    if gtype == "llm" and PLACEHOLDER in _body(text):
        errors.append(f"{rel}: llm rubric is still a TODO placeholder")
    if gtype == "regex":
        pattern = front.get("pattern")
        if not pattern:
            errors.append(f"{rel}: regex grader needs a pattern")
        else:
            try:
                re.compile(pattern)
            except re.error as exc:
                errors.append(f"{rel}: regex pattern does not compile ({exc})")
    if gtype == "tool_used" and front.get("tool") == "Skill":
        match = front.get("input_match", "")
        if not any(re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", match) for name in skills):
            named = re.findall(r"([a-z0-9]+(?:-[a-z0-9]+)+)\"?\s*$", match) or [match or "(empty)"]
            errors.append(f"{rel}: Skill grader must name one of this plugin's skills, got {named[0]!r}")


def check(root: Path) -> list:
    root = Path(root)
    errors = []
    for evals in sorted((root / "plugins").glob("*/evals")):
        if not evals.is_dir():
            continue
        plugin = evals.parent
        skills = {p.name for p in (plugin / "skills").glob("*") if p.is_dir()}
        for case in sorted(p for p in evals.iterdir() if p.is_dir() and p.name not in ("results", "mocks")):
            rel = case.relative_to(root).as_posix()
            _check_prompt(case, rel, errors)
            graders = sorted((case / "graders").glob("*.md")) if (case / "graders").is_dir() else []
            if not graders:
                errors.append(f"{rel}: needs at least one grader in graders/")
            for grader in graders:
                _check_grader(grader, grader.relative_to(root).as_posix(), skills, errors)
    return errors


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent
    errors = check(root)
    for e in errors:
        print(f"ERROR: {e}")
    if not errors:
        print("OK: eval suites are well-formed")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

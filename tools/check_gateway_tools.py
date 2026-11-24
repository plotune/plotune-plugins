#!/usr/bin/env python3
"""Check that the Plotune gateway skills only name tools the gateway offers.

Reads plugins/plotune/references/gateway-tools.json (made by tools/generate_gateway_tools.py from the
monorepo catalog; this check never needs the monorepo) and scans every Markdown file under
plugins/plotune/skills/ (the bundled requirements skills included).

What counts as a tool name (a deliberately simple heuristic):
  * A snake_case word (letters, digits, underscores; a name written inside a path or file name such as
    docs/work_patterns.md or pool_hook.py is not a word) is checked when it is
      - an OLD name of a renamed tool (list_jobs_tool, wait_for_job, ...): error naming the gateway name;
      - the name of a tool the gateway does not offer (principal_context, projects_list, ...): error;
      - prefixed nexus_ or plotune_ but not a gateway tool: error (that prefix is the gateway's namespace);
      - written in backticks in a call-like context and not a gateway tool: error. Call-like means
        `name(`, or `name` right after "call", "calls", "calling", "invoke", "invokes" or "tool", or
        right before "tool".
  * A one-word old or excluded name (exec) is only checked inside backticks, because it is also a word.
  * Gateway names always pass. Every other snake_case word (project_id, expected_revision, ...) is ignored.
  * Inside fenced code blocks the same rules apply; only `name(` counts as call-like there.

Usage:
    python tools/check_gateway_tools.py [repo-root]
"""
import json
import re
import sys
from pathlib import Path

REFERENCE = "plugins/plotune/references/gateway-tools.json"
SKILLS = "plugins/plotune/skills"
PROJECTS_TOOL = "plotune_projects_list"
NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
TOKEN = re.compile(r"(?<![A-Za-z0-9_./\\-])[a-z][a-z0-9]*(?:_[a-z0-9]+)*(?![A-Za-z0-9_/]|\.[A-Za-z]|-[A-Za-z])")
SPAN = re.compile(r"`([^`\n]+)`")
BEFORE_CALL = re.compile(r"\b(?:calls?|calling|invokes?|tool)\s+$", re.IGNORECASE)
AFTER_TOOL = re.compile(r"^\s+tool\b", re.IGNORECASE)
FENCE = re.compile(r"^\s*(```|~~~)")
NAMESPACES = ("nexus_", "plotune_")


def load_reference(root: Path, errors: list):
    path = Path(root) / REFERENCE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"{REFERENCE}: cannot read ({exc}); generate it with tools/generate_gateway_tools.py")
        return None
    tools = data.get("tools") if isinstance(data, dict) else None
    if not isinstance(tools, list) or not all(isinstance(t, str) for t in tools):
        errors.append(f"{REFERENCE}: 'tools' must be a list of names")
        return None
    for name in tools:
        if not NAME_RE.match(name):
            errors.append(f"{REFERENCE}: invalid tool name {name!r}")
    if PROJECTS_TOOL not in tools:
        errors.append(f"{REFERENCE}: {PROJECTS_TOOL} is missing from 'tools'")
    renamed = data.get("renamed") if isinstance(data.get("renamed"), dict) else {}
    for old, new in renamed.items():
        if new not in tools:
            errors.append(f"{REFERENCE}: {old!r} is renamed to {new!r}, which is not in 'tools'")
    excluded = data.get("excluded") if isinstance(data.get("excluded"), dict) else {}
    return set(tools), renamed, excluded


def _problem(token, tools, renamed, excluded, in_code, call_like):
    """Why a token is wrong, or None."""
    if token in tools:
        return None
    word = "_" not in token
    if token in renamed and (in_code or not word):
        return f"old tool name {token}; the gateway name is {renamed[token]}"
    if token in excluded and (in_code or not word):
        return f"{token} is not offered by the gateway ({excluded[token]})"
    if token.startswith(NAMESPACES):
        return f"{token} is not a gateway tool"
    if in_code and call_like and not word:
        return f"{token} is not a gateway tool"
    return None


def scan(text: str, tools, renamed, excluded):
    """Yield (line number, message) for the problems in one Markdown text."""
    fenced = False
    for number, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            spans = [(0, len(line))]
        else:
            spans = [m.span(1) for m in SPAN.finditer(line)]
        for match in TOKEN.finditer(line):
            start, end = match.span()
            span = next(((a, b) for a, b in spans if a <= start and end <= b), None)
            if span is not None and fenced:
                call_like = line[end:end + 1] == "("
            elif span is not None:
                alone = line[span[0]:span[1]] == match.group()
                call_like = (line[end:end + 1] == "("
                             or (alone and (bool(BEFORE_CALL.search(line[:span[0] - 1]))
                                            or bool(AFTER_TOOL.match(line[span[1] + 1:])))))
            else:
                call_like = False
            message = _problem(match.group(), tools, renamed, excluded, span is not None, call_like)
            if message:
                yield number, message


def check(root: Path) -> list:
    root = Path(root)
    errors: list = []
    reference = load_reference(root, errors)
    if reference is None:
        return errors
    tools, renamed, excluded = reference
    for path in sorted((root / SKILLS).rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"{rel}: cannot read ({exc})")
            continue
        for number, message in scan(text, tools, renamed, excluded):
            errors.append(f"{rel}:{number}: {message}")
    return errors


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = Path(argv[0]) if argv else Path(__file__).resolve().parent.parent
    errors = check(root)
    for e in errors:
        print(f"ERROR: {e}")
    if not errors:
        print("OK: skills name only gateway tools")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

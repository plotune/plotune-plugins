#!/usr/bin/env python3
"""Compare offline calibration parameter snapshots from CSV, JSON, or simple text."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from safe_paths import require_regular_input, require_safe_output


def parse_snapshot(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    suffix = path.suffix.lower()
    if suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid calibration JSON: {path}: {error}") from error
        if isinstance(data, dict) and isinstance(data.get("parameters"), dict):
            data = data["parameters"]
        if not isinstance(data, dict):
            raise SystemExit(f"Calibration JSON must be an object or contain parameters: {path}")
        return {str(key): str(value) for key, value in data.items()}
    if suffix == ".csv":
        rows = list(csv.DictReader(text.splitlines()))
        result: dict[str, str] = {}
        for row in rows:
            name = row.get("name") or row.get("parameter") or row.get("symbol")
            value = row.get("value") or row.get("physical") or row.get("raw")
            if name is not None and value is not None:
                result[name.strip()] = value.strip()
        return result
    result = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", ";", "[")):
            continue
        if "=" in stripped:
            key, value = stripped.split("=", 1)
        else:
            parts = stripped.split(None, 1)
            if len(parts) != 2:
                continue
            key, value = parts
        result[key.strip()] = value.strip()
    return result


def analyze(base_path: Path, candidate_path: Path) -> dict[str, Any]:
    base = parse_snapshot(base_path)
    candidate = parse_snapshot(candidate_path)
    changed = [
        {"name": name, "base": base[name], "candidate": candidate[name]}
        for name in sorted(set(base) & set(candidate))
        if base[name] != candidate[name]
    ]
    return {
        "source": {"base": str(base_path), "candidate": str(candidate_path)},
        "summary": {
            "base_parameters": len(base),
            "candidate_parameters": len(candidate),
            "changed": len(changed),
            "added": len(set(candidate) - set(base)),
            "removed": len(set(base) - set(candidate)),
        },
        "changes": {
            "changed": changed,
            "added": sorted(set(candidate) - set(base)),
            "removed": sorted(set(base) - set(candidate)),
        },
        "notes": ["This compares offline snapshots only. It does not read or write ECU memory."],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Calibration Diff",
        "",
        f"Base: `{report['source']['base']}`",
        f"Candidate: `{report['source']['candidate']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key.replace('_', ' ')}: {value}")
    return "\n".join(lines) + "\n"


def emit(report: dict[str, Any], fmt: str, output: Path | None) -> None:
    text = json.dumps(report, indent=2, sort_keys=True) + "\n" if fmt == "json" else render_markdown(report)
    output = require_safe_output(output)
    if output is None:
        print(text, end="")
    else:
        output.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    require_regular_input(args.base, "Base calibration")
    require_regular_input(args.candidate, "Candidate calibration")
    emit(analyze(args.base, args.candidate), args.format, args.output)


if __name__ == "__main__":
    main()

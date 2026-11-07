#!/usr/bin/env python3
"""Create an offline evidence manifest with SHA-256 hashes for automotive artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from safe_paths import require_regular_input, require_safe_output


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def analyze(inputs: list[Path], classification: str, assumption: list[str]) -> dict[str, Any]:
    artifacts = [
        {
            "path": str(path),
            "name": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "classification": classification,
        }
        for path in inputs
    ]
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"artifacts": len(artifacts), "classification": classification},
        "assumptions": assumption,
        "artifacts": artifacts,
        "notes": [
            "This manifest records local files only; it does not certify content correctness.",
            "Use live classifications only for reports produced by authorized Nexus runs.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Automotive Evidence Pack",
        "",
        f"Created: `{report['created_at']}`",
        f"Classification: `{report['summary']['classification']}`",
        "",
        "## Artifacts",
        "",
    ]
    for artifact in report["artifacts"]:
        lines.append(f"- `{artifact['path']}`: `{artifact['sha256']}` ({artifact['size_bytes']} bytes)")
    if report["assumptions"]:
        lines.extend(["", "## Assumptions", ""])
        for assumption in report["assumptions"]:
            lines.append(f"- {assumption}")
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
    parser.add_argument("--inputs", nargs="+", required=True, type=Path)
    parser.add_argument("--classification", choices=("offline", "live-nexus", "mixed"), default="offline")
    parser.add_argument("--assumption", action="append", default=[])
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    for path in args.inputs:
        require_regular_input(path, "Evidence artifact")
    emit(analyze(args.inputs, args.classification, args.assumption), args.format, args.output)


if __name__ == "__main__":
    main()

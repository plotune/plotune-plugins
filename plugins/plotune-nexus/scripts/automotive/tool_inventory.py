#!/usr/bin/env python3
"""Read-only local inventory for common automotive engineering tools."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

from safe_paths import require_safe_output


TOOL_CATALOG = {
    "can": ["candump", "cansend", "canplayer", "canbusload", "savvycan"],
    "diagnostics": ["odxtools", "asammdf", "doipclient"],
    "calibration": ["asammdf", "pyxcp", "canape", "inca"],
    "autosar": ["arxml", "arccore", "artop"],
    "testing": ["pytest", "lcov", "gcov", "genhtml"],
    "static-analysis": ["cppcheck", "clang-tidy", "flawfinder"],
    "simulation": ["carla", "sumo", "gazebo"],
}


def analyze(include_paths: bool = False) -> dict[str, Any]:
    categories: dict[str, list[dict[str, Any]]] = {}
    for category, tools in TOOL_CATALOG.items():
        categories[category] = []
        for tool in tools:
            location = shutil.which(tool)
            item: dict[str, Any] = {"tool": tool, "found": bool(location)}
            if include_paths and location:
                item["path"] = location
            categories[category].append(item)
    env_hints = [
        key
        for key in ("ASAMMDF_HOME", "AUTOSAR_HOME", "CANAPE_HOME", "INCA_HOME", "VECTOR_HOME")
        if os.environ.get(key)
    ]
    return {
        "summary": {
            "categories": len(categories),
            "tools_checked": sum(len(items) for items in categories.values()),
            "tools_found": sum(1 for items in categories.values() for item in items if item["found"]),
        },
        "categories": categories,
        "environment_hints": env_hints,
        "notes": [
            "Read-only inventory. Versions are not executed and no installer or package manager is invoked.",
            "Full executable paths are omitted unless --include-paths is provided; redact paths before sharing reports.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Automotive Tool Inventory",
        "",
        f"- Tools checked: {report['summary']['tools_checked']}",
        f"- Tools found: {report['summary']['tools_found']}",
        "",
    ]
    for category, tools in report["categories"].items():
        lines.extend([f"## {category}", ""])
        for tool in tools:
            state = "found" if tool["found"] else "not found"
            lines.append(f"- `{tool['tool']}`: {state}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def emit(report: dict[str, Any], fmt: str, output: Path | None) -> None:
    text = json.dumps(report, indent=2, sort_keys=True) + "\n" if fmt == "json" else render_markdown(report)
    output = require_safe_output(output)
    if output is None:
        print(text, end="")
    else:
        output.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-paths", action="store_true", help="Include full executable paths; redact before sharing.")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    emit(analyze(args.include_paths), args.format, args.output)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Print a static automotive tool comparison matrix for offline planning."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from safe_paths import require_safe_output


MATRIX = [
    {
        "category": "can",
        "commercial": ["Vector CANoe", "Vector CANalyzer", "Kvaser CanKing", "PCAN-View"],
        "open_source_or_low_cost": ["SocketCAN utilities", "SavvyCAN", "BUSMASTER", "python-can"],
        "handoff_to_nexus": "Use Plotune Nexus for bounded CAN capture, artifact storage, gateway tests, and repeatable bus evidence.",
    },
    {
        "category": "diagnostics",
        "commercial": ["Vector CANoe Diagnostics", "ODXStudio", "CANdelaStudio"],
        "open_source_or_low_cost": ["odxtools", "python-uds examples", "DoIP client libraries"],
        "handoff_to_nexus": "Use Plotune Nexus for approved UDS/DoIP requests with lease, target, timeout, and stop conditions.",
    },
    {
        "category": "calibration",
        "commercial": ["ETAS INCA", "Vector CANape", "dSPACE ControlDesk"],
        "open_source_or_low_cost": ["asammdf", "pyXCP", "A2L text inspection"],
        "handoff_to_nexus": "Use Plotune Nexus for live XCP measurement and artifact-backed recording after offline A2L review.",
    },
    {
        "category": "autosar",
        "commercial": ["DaVinci Developer", "EB tresos", "SystemDesk", "ARCTIC Studio"],
        "open_source_or_low_cost": ["ARTOP", "ARXML XML tooling", "custom schema checks"],
        "handoff_to_nexus": "Use Plotune Nexus for runtime evidence tied to network, diagnostic, and container behavior.",
    },
    {
        "category": "testing",
        "commercial": ["dSPACE SCALEXIO", "NI VeriStand", "Vector VT System"],
        "open_source_or_low_cost": ["pytest", "Robot Framework", "SIL fixtures", "virtual CAN"],
        "handoff_to_nexus": "Use Plotune Nexus test sequences for bounded bench validation and report artifacts.",
    },
]


def analyze(category: str | None = None) -> dict[str, Any]:
    rows = [row for row in MATRIX if category is None or row["category"] == category]
    return {
        "summary": {"categories": len(rows)},
        "matrix": rows,
        "notes": [
            "Static planning aid only. Tool suitability depends on project constraints, licensing, safety process, and data ownership.",
            "No installation or tool probing is performed.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = ["# Automotive Tool Comparison", ""]
    for row in report["matrix"]:
        lines.extend(
            [
                f"## {row['category']}",
                "",
                f"- Commercial: {', '.join(row['commercial'])}",
                f"- Open source or low cost: {', '.join(row['open_source_or_low_cost'])}",
                f"- Nexus handoff: {row['handoff_to_nexus']}",
                "",
            ]
        )
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
    parser.add_argument("--category", choices=sorted(row["category"] for row in MATRIX))
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    emit(analyze(args.category), args.format, args.output)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Draft an offline XCP DAQ measurement plan from A2L and optional LAB symbols."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a2l_lab_check import parse_a2l, parse_lab
from safe_paths import require_regular_input, require_safe_output


def analyze(a2l_path: Path, lab_path: Path | None, max_signals_per_list: int) -> dict[str, Any]:
    parsed = parse_a2l(a2l_path)
    lab_symbols = parse_lab(lab_path)
    measurements = {item["name"]: item for item in parsed["measurements"]}
    characteristics = {item["name"]: item for item in parsed["characteristics"]}
    axis_points = {item["name"]: item for item in parsed.get("axis_points", [])}
    selected_names = lab_symbols if lab_symbols else sorted(measurements)
    selected = [measurements[name] for name in selected_names if name in measurements]
    missing = sorted(name for name in selected_names if name not in measurements)
    missing_symbol_hints = []
    for name in missing:
        if name in characteristics:
            missing_symbol_hints.append({"name": name, "kind": "CHARACTERISTIC", "note": "present in A2L but not DAQ-able as a MEASUREMENT"})
        elif name in axis_points:
            missing_symbol_hints.append({"name": name, "kind": "AXIS_PTS", "note": "present in A2L as axis metadata, not a MEASUREMENT"})
        else:
            missing_symbol_hints.append({"name": name, "kind": "absent", "note": "not found in parsed A2L inventory"})
    daq_lists = []
    for offset in range(0, len(selected), max_signals_per_list):
        chunk = selected[offset : offset + max_signals_per_list]
        daq_lists.append(
            {
                "name": f"DAQ_LIST_{len(daq_lists) + 1:02d}",
                "event": "EVENT_UNSPECIFIED",
                "measurements": [item["name"] for item in chunk],
                "addresses": [item.get("address") for item in chunk],
            }
        )
    return {
        "source": {"a2l": str(a2l_path), "lab": str(lab_path) if lab_path else None},
        "summary": {
            "available_measurements": len(measurements),
            "requested_measurements": len(selected_names),
            "planned_measurements": len(selected),
            "daq_lists": len(daq_lists),
            "missing_requested_measurements": len(missing),
        },
        "xcp_hints": {
            "if_data": parsed["if_data"],
            "requires_live_target_context": ["transport", "station_address", "event_channel", "sample_rate", "buffer_limits"],
        },
        "plan": {
            "daq_lists": daq_lists,
            "missing_measurements": missing,
            "missing_symbol_hints": missing_symbol_hints,
        },
        "notes": ["Draft plan only. It does not connect to a target or allocate live DAQ lists."],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# XCP DAQ Plan",
        "",
        f"A2L: `{report['source']['a2l']}`",
        f"LAB: `{report['source']['lab']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key.replace('_', ' ')}: {value}")
    lines.extend(["", "## DAQ Lists", ""])
    for daq in report["plan"]["daq_lists"]:
        lines.append(f"- `{daq['name']}`: {len(daq['measurements'])} measurements")
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
    parser.add_argument("--a2l", required=True, type=Path)
    parser.add_argument("--lab", type=Path)
    parser.add_argument("--max-signals-per-list", type=int, default=8)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    require_regular_input(args.a2l, "A2L")
    if args.lab is not None:
        require_regular_input(args.lab, "LAB")
    emit(analyze(args.a2l, args.lab, max(args.max_signals_per_list, 1)), args.format, args.output)


if __name__ == "__main__":
    main()

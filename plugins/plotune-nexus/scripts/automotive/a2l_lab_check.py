#!/usr/bin/env python3
"""Offline A2L/LAB inventory and consistency checks."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from safe_paths import require_regular_input, require_safe_output


BEGIN_RE = re.compile(r"/begin\s+(\S+)\s+(\S+)")
ADDRESS_RE = re.compile(r"\b(?:ECU_ADDRESS|VALUE)\s+(0x[0-9A-Fa-f]+|\d+)")
UNIT_RE = re.compile(r"\bUNIT\s+\"([^\"]+)\"")
IF_DATA_RE = re.compile(r"/begin\s+IF_DATA\s+(\S+)")
CAN_ID_RE = re.compile(r"\b(CAN_ID_\S+)\s+(0x[0-9A-Fa-f]+|\d+)")


def parse_a2l(path: Path) -> dict[str, Any]:
    measurements: list[dict[str, Any]] = []
    characteristics: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    compu_methods: list[str] = []
    record_layouts: list[str] = []
    axis_points: list[dict[str, Any]] = []
    if_data: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_kind = ""
    current_if_data: dict[str, Any] | None = None
    mentions_xcp = False
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if "XCP" in line:
            mentions_xcp = True
        if_data_match = IF_DATA_RE.search(line)
        if if_data_match:
            current_if_data = {"name": if_data_match.group(1), "can_ids": {}}
            if_data.append(current_if_data)
        if current_if_data is not None:
            can_id = CAN_ID_RE.search(line)
            if can_id:
                current_if_data["can_ids"][can_id.group(1)] = can_id.group(2)
            if line.startswith("/end IF_DATA"):
                current_if_data = None
        begin = BEGIN_RE.search(line)
        if begin:
            current_kind = begin.group(1)
            name = begin.group(2)
            if current is not None and current_kind.startswith("REF_"):
                current_kind = "GROUP"
                continue
            current = {"name": name, "address": None, "unit": None}
            if current_kind == "MEASUREMENT":
                measurements.append(current)
            elif current_kind == "CHARACTERISTIC":
                characteristics.append(current)
            elif current_kind == "GROUP":
                current = {"name": name, "symbols": []}
                groups.append(current)
            elif current_kind == "COMPU_METHOD":
                compu_methods.append(name)
                current = None
            elif current_kind == "RECORD_LAYOUT":
                record_layouts.append(name)
                current = None
            elif current_kind == "AXIS_PTS":
                current = {"name": name, "address": None, "unit": None}
                axis_points.append(current)
            continue
        if current is not None:
            address = ADDRESS_RE.search(line)
            if address and current["address"] is None:
                current["address"] = address.group(1)
            unit = UNIT_RE.search(line)
            if unit:
                current["unit"] = unit.group(1)
            if current_kind == "GROUP" and line and not line.startswith(("/begin", "/end")):
                current["symbols"].extend(token for token in line.split() if token.isidentifier())
        if line.startswith("/end ") and current_kind in line:
            current = None
            current_kind = ""
    return {
        "measurements": measurements,
        "characteristics": characteristics,
        "groups": groups,
        "compu_methods": compu_methods,
        "record_layouts": record_layouts,
        "axis_points": axis_points,
        "if_data": if_data,
        "mentions_xcp": mentions_xcp,
    }


def parse_lab(path: Path | None) -> list[str]:
    if path is None:
        return []
    symbols: list[str] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("[", ";", "#")):
            continue
        symbols.append(line.split()[0])
    return symbols


def analyze(a2l_path: Path, lab_path: Path | None) -> dict[str, Any]:
    parsed = parse_a2l(a2l_path)
    all_symbols = parsed["measurements"] + parsed["characteristics"] + parsed["axis_points"]
    names = [item["name"] for item in all_symbols]
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    missing_units = sorted(item["name"] for item in all_symbols if not item.get("unit"))
    lab_symbols = parse_lab(lab_path)
    a2l_name_set = set(names)
    addresses = []
    for item in all_symbols:
        address = item.get("address")
        if address:
            try:
                addresses.append(int(str(address), 0))
            except ValueError:
                pass
    return {
        "source": {"a2l": str(a2l_path), "lab": str(lab_path) if lab_path else None},
        "summary": {
            "measurements": len(parsed["measurements"]),
            "characteristics": len(parsed["characteristics"]),
            "axis_points": len(parsed["axis_points"]),
            "groups": len(parsed["groups"]),
            "compu_methods": len(parsed["compu_methods"]),
            "record_layouts": len(parsed["record_layouts"]),
            "if_data_blocks": len(parsed["if_data"]),
            "lab_symbols": len(lab_symbols),
        },
        "issues": {
            "duplicate_symbols": duplicates,
            "symbols_missing_units": missing_units,
            "symbols_missing_addresses": sorted(item["name"] for item in all_symbols if not item.get("address")),
            "lab_symbols_missing_from_a2l": sorted(symbol for symbol in lab_symbols if symbol not in a2l_name_set),
        },
        "xcp_hints": {
            "mentions_xcp": bool(parsed["mentions_xcp"]),
            "if_data": parsed["if_data"],
            "note": "Inspect IF_DATA transport settings before planning XCP acquisition." if parsed["mentions_xcp"] else "No XCP IF_DATA block detected by text scan.",
        },
        "memory_ranges": {
            "min_address": f"0x{min(addresses):X}" if addresses else None,
            "max_address": f"0x{max(addresses):X}" if addresses else None,
            "addressed_symbols": len(addresses),
        },
        "inventory": {
            "measurements": parsed["measurements"],
            "characteristics": parsed["characteristics"],
            "axis_points": parsed["axis_points"],
            "groups": parsed["groups"],
            "compu_methods": parsed["compu_methods"],
            "record_layouts": parsed["record_layouts"],
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# A2L/LAB Check Report",
        "",
        f"A2L: `{report['source']['a2l']}`",
        f"LAB: `{report['source']['lab']}`",
        "",
        "## Summary",
        "",
        f"- Measurements: {report['summary']['measurements']}",
        f"- Characteristics: {report['summary']['characteristics']}",
        f"- Axis points: {report['summary']['axis_points']}",
        f"- Groups: {report['summary']['groups']}",
        f"- COMPU methods: {report['summary']['compu_methods']}",
        f"- Record layouts: {report['summary']['record_layouts']}",
        f"- IF_DATA blocks: {report['summary']['if_data_blocks']}",
        f"- LAB symbols: {report['summary']['lab_symbols']}",
        "",
        "## Issues",
        "",
    ]
    for name, values in report["issues"].items():
        lines.append(f"- {name.replace('_', ' ')}: {len(values)}")
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
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    require_regular_input(args.a2l, "A2L")
    if args.lab is not None:
        require_regular_input(args.lab, "LAB")
    emit(analyze(args.a2l, args.lab), args.format, args.output)


if __name__ == "__main__":
    main()

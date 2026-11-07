#!/usr/bin/env python3
"""Generate or lint offline functional-safety workproduct tables."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from safe_paths import require_regular_input, require_safe_output


KIND_COLUMNS = {
    "hara": ["hazard_id", "hazardous_event", "severity", "exposure", "controllability", "asil", "safety_goal", "safe_state"],
    "fmea": ["failure_mode_id", "item", "failure_mode", "effect", "cause", "severity", "occurrence", "detection", "rpn", "action"],
    "fta": ["top_event", "intermediate_event", "basic_event", "gate", "mitigation", "evidence"],
    "safety-goal": ["safety_goal_id", "description", "asil", "safe_state", "linked_hazards", "verification"],
    "safety-case": ["claim_id", "claim", "argument", "evidence", "status", "owner"],
}


def normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def parse_markdown_table(text: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return []
    headers = [normalize_key(cell) for cell in lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        values = [cell.strip() for cell in line.strip("|").split("|")]
        if len(values) == len(headers):
            rows.append(dict(zip(headers, values)))
    return rows


def load_rows(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid safety JSON: {path}: {error}") from error
        if isinstance(data, dict):
            data = data.get("rows", data.get("items", []))
        if not isinstance(data, list):
            raise SystemExit(f"Safety JSON must be a list or contain rows: {path}")
        return [{normalize_key(str(key)): "" if value is None else str(value).strip() for key, value in row.items()} for row in data]
    if path.suffix.lower() == ".csv":
        return [
            {normalize_key(str(key)): "" if value is None else str(value).strip() for key, value in row.items()}
            for row in csv.DictReader(text.splitlines())
        ]
    rows = parse_markdown_table(text)
    if rows:
        return rows
    raise SystemExit(f"Unsupported or empty safety workproduct: {path}")


def template(kind: str, item: str, rows: int) -> dict[str, Any]:
    columns = KIND_COLUMNS[kind]
    generated_rows: list[dict[str, str]] = []
    for index in range(1, rows + 1):
        row = {column: "" for column in columns}
        first_key = columns[0]
        row[first_key] = f"{kind.upper().replace('-', '')}-{index:03d}"
        if "item" in row:
            row["item"] = item
        generated_rows.append(row)
    return {
        "kind": kind,
        "item": item,
        "status": "draft_not_certification_evidence",
        "columns": columns,
        "rows": generated_rows,
        "notes": [
            "Draft aid only. Final workproducts require qualified review and project-specific safety lifecycle evidence.",
            "Keep assumptions, operating modes, interfaces, and evidence identifiers explicit.",
        ],
    }


def lint(kind: str, path: Path) -> dict[str, Any]:
    rows = load_rows(path)
    required = KIND_COLUMNS[kind]
    missing_columns = sorted(column for column in required if rows and column not in rows[0])
    incomplete_rows: list[dict[str, Any]] = []
    high_risk_without_action: list[str] = []
    for index, row in enumerate(rows, start=1):
        missing = [column for column in required if not row.get(column)]
        if missing:
            incomplete_rows.append({"row": index, "missing": missing})
        if kind == "hara":
            if row.get("asil") in {"B", "C", "D"} and not row.get("safety_goal"):
                high_risk_without_action.append(row.get("hazard_id") or f"row:{index}")
        if kind == "fmea":
            try:
                rpn = int(row.get("rpn", "0"))
            except ValueError:
                rpn = 0
            if rpn >= 80 and not row.get("action"):
                high_risk_without_action.append(row.get("failure_mode_id") or f"row:{index}")
    return {
        "kind": kind,
        "source": str(path),
        "status": "draft_lint_not_certification_evidence",
        "summary": {"rows": len(rows), "required_columns": len(required)},
        "issues": {
            "missing_columns": missing_columns,
            "incomplete_rows": incomplete_rows,
            "high_risk_rows_without_action": high_risk_without_action,
        },
        "rows": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Safety Workproduct: {report['kind']}",
        "",
        f"Status: `{report['status']}`",
        "",
    ]
    if "columns" in report:
        lines.extend(["| " + " | ".join(report["columns"]) + " |", "| " + " | ".join("---" for _ in report["columns"]) + " |"])
        for row in report["rows"]:
            lines.append("| " + " | ".join(row.get(column, "") for column in report["columns"]) + " |")
    else:
        lines.extend(["## Issues", ""])
        for key, values in report["issues"].items():
            lines.append(f"- {key.replace('_', ' ')}: {len(values)}")
    return "\n".join(lines) + "\n"


def emit(report: dict[str, Any], fmt: str, output: Path | None) -> None:
    text = json.dumps(report, indent=2, sort_keys=True) + "\n" if fmt == "json" else render_markdown(report)
    output = require_safe_output(output)
    if output is None:
        print(text, end="")
    else:
        output.write_text(text, encoding="utf-8")


def main() -> None:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--kind", required=True, choices=sorted(KIND_COLUMNS))
    common.add_argument("--format", choices=("json", "markdown"), default="markdown")
    common.add_argument("--output", type=Path)
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    template_parser = subparsers.add_parser("template", parents=[common])
    template_parser.add_argument("--item", required=True)
    template_parser.add_argument("--rows", type=int, default=3)
    lint_parser = subparsers.add_parser("lint", parents=[common])
    lint_parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()

    if args.command == "template":
        report = template(args.kind, args.item, max(args.rows, 1))
    else:
        require_regular_input(args.input, "Safety workproduct")
        report = lint(args.kind, args.input)
    emit(report, args.format, args.output)


if __name__ == "__main__":
    main()

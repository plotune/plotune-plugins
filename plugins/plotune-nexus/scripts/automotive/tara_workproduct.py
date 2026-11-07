#!/usr/bin/env python3
"""Generate or lint offline automotive cybersecurity TARA workproduct tables."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from safe_paths import require_regular_input, require_safe_output


KIND_COLUMNS = {
    "asset": ["asset_id", "asset", "interface", "trust_boundary", "security_property", "owner"],
    "attack-surface": ["surface_id", "interface", "entry_point", "privilege", "exposure", "notes"],
    "damage-scenario": ["damage_id", "asset_id", "damage_scenario", "impact", "stakeholder"],
    "threat-scenario": [
        "threat_id",
        "damage_id",
        "threat_scenario",
        "attack_path",
        "impact",
        "feasibility",
        "risk",
        "treatment",
        "cybersecurity_goal",
    ],
    "risk-treatment": ["risk_id", "threat_id", "decision", "mitigation", "verification", "evidence"],
}
HIGH_RISK = {"high", "critical", "severe"}


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
            raise SystemExit(f"Invalid TARA JSON: {path}: {error}") from error
        if isinstance(data, dict):
            data = data.get("rows", data.get("items", []))
        if not isinstance(data, list):
            raise SystemExit(f"TARA JSON must be a list or contain rows: {path}")
        return [{normalize_key(str(key)): "" if value is None else str(value).strip() for key, value in row.items()} for row in data]
    if path.suffix.lower() == ".csv":
        return [
            {normalize_key(str(key)): "" if value is None else str(value).strip() for key, value in row.items()}
            for row in csv.DictReader(text.splitlines())
        ]
    rows = parse_markdown_table(text)
    if rows:
        return rows
    raise SystemExit(f"Unsupported or empty TARA workproduct: {path}")


def template(kind: str, asset: str, rows: int) -> dict[str, Any]:
    columns = KIND_COLUMNS[kind]
    generated_rows: list[dict[str, str]] = []
    prefix = kind.upper().replace("-", "")
    for index in range(1, rows + 1):
        row = {column: "" for column in columns}
        row[columns[0]] = f"{prefix}-{index:03d}"
        if "asset" in row:
            row["asset"] = asset
        if "asset_id" in row and columns[0] != "asset_id":
            row["asset_id"] = "ASSET-001"
        generated_rows.append(row)
    return {
        "kind": kind,
        "asset": asset,
        "status": "draft_not_cybersecurity_case_evidence",
        "columns": columns,
        "rows": generated_rows,
        "notes": [
            "Draft aid only. Final cybersecurity workproducts require project-specific ISO/SAE 21434 process evidence.",
            "Do not use this script for active scanning or unauthorized access.",
        ],
    }


def lint(kind: str, path: Path) -> dict[str, Any]:
    rows = load_rows(path)
    required = KIND_COLUMNS[kind]
    missing_columns = sorted(column for column in required if rows and column not in rows[0])
    incomplete_rows: list[dict[str, Any]] = []
    high_risk_without_treatment: list[str] = []
    for index, row in enumerate(rows, start=1):
        missing = [column for column in required if not row.get(column)]
        if missing:
            incomplete_rows.append({"row": index, "missing": missing})
        risk = row.get("risk", "").lower()
        if risk in HIGH_RISK and not row.get("treatment"):
            high_risk_without_treatment.append(row.get("threat_id") or row.get("risk_id") or f"row:{index}")
    return {
        "kind": kind,
        "source": str(path),
        "status": "draft_lint_not_cybersecurity_case_evidence",
        "summary": {"rows": len(rows), "required_columns": len(required)},
        "issues": {
            "missing_columns": missing_columns,
            "incomplete_rows": incomplete_rows,
            "high_risk_rows_without_treatment": high_risk_without_treatment,
        },
        "rows": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# TARA Workproduct: {report['kind']}",
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
    template_parser.add_argument("--asset", required=True)
    template_parser.add_argument("--rows", type=int, default=3)
    lint_parser = subparsers.add_parser("lint", parents=[common])
    lint_parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()

    if args.command == "template":
        report = template(args.kind, args.asset, max(args.rows, 1))
    else:
        require_regular_input(args.input, "TARA workproduct")
        report = lint(args.kind, args.input)
    emit(report, args.format, args.output)


if __name__ == "__main__":
    main()

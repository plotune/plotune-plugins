#!/usr/bin/env python3
"""Lint offline UDS sequence drafts from JSON, CSV, or Markdown tables."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from safe_paths import require_regular_input, require_safe_output
from odx_inspect import analyze as inspect_odx
from uds_payload import decode_payload, clean_hex


RISKY_SERVICES = {0x14, 0x2E, 0x31, 0x34, 0x36, 0x37, 0x85}
RISKY_ROUTINE_WORDS = ("erase", "clear", "reset", "program", "download", "flash", "unlock")


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


def load_steps(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid UDS sequence JSON: {path}: {error}") from error
        if isinstance(data, dict):
            data = data.get("steps", data.get("requests", []))
        if not isinstance(data, list):
            raise SystemExit(f"UDS sequence JSON must be a list or contain steps: {path}")
        return [{normalize_key(str(key)): "" if value is None else str(value).strip() for key, value in row.items()} for row in data]
    if path.suffix.lower() == ".csv":
        return [
            {normalize_key(str(key)): "" if value is None else str(value).strip() for key, value in row.items()}
            for row in csv.DictReader(text.splitlines())
        ]
    rows = parse_markdown_table(text)
    if rows:
        return rows
    raise SystemExit(f"Unsupported or empty UDS sequence artifact: {path}")


def payload_for_step(step: dict[str, str]) -> str:
    for key in ("request_hex", "payload_hex", "request", "payload"):
        if step.get(key):
            return step[key]
    return ""


def normalize_hex_identifier(value: str | None, width: int = 4) -> str | None:
    if not value:
        return None
    try:
        return f"0x{int(value, 0):0{width}X}"
    except ValueError:
        return value


def odx_routine_index(odx_path: Path | None) -> dict[str, str]:
    if odx_path is None:
        return {}
    report = inspect_odx(odx_path)
    routines: dict[str, str] = {}
    for document in report.get("documents", []):
        for routine in document.get("inventory", {}).get("routines", []):
            identifier = normalize_hex_identifier(routine.get("identifier"))
            if identifier:
                routines[identifier] = routine.get("name", "")
    return routines


def routine_semantic_issue(cleaned: str, routine_names: dict[str, str]) -> dict[str, str] | None:
    if len(cleaned) < 6 or cleaned[:2] != "31":
        return None
    routine_id_hex = cleaned[4:8] if len(cleaned) >= 8 else cleaned[2:6]
    routine_id = f"0x{int(routine_id_hex, 16):04X}"
    routine_name = routine_names.get(routine_id)
    if not routine_name:
        return None
    lowered = routine_name.lower()
    if not any(word in lowered for word in RISKY_ROUTINE_WORDS):
        return None
    return {
        "routine_id": routine_id,
        "routine_name": routine_name,
        "reason": "ODX routine name indicates destructive or programming-related behavior",
    }


def analyze(path: Path, odx_path: Path | None = None) -> dict[str, Any]:
    steps = load_steps(path)
    routine_names = odx_routine_index(odx_path)
    decoded_steps: list[dict[str, Any]] = []
    malformed: list[dict[str, Any]] = []
    risky_without_preconditions: list[dict[str, Any]] = []
    odx_risky_routines: list[dict[str, Any]] = []
    has_non_default_session = False
    has_security = False

    for index, step in enumerate(steps, start=1):
        payload = payload_for_step(step)
        if not payload:
            malformed.append({"step": index, "reason": "missing request payload"})
            continue
        try:
            cleaned = clean_hex(payload)
            decoded = decode_payload(cleaned)
        except SystemExit as error:
            malformed.append({"step": index, "reason": str(error)})
            continue
        sid = int(cleaned[:2], 16)
        if sid == 0x10 and len(cleaned) >= 4 and cleaned[2:4] != "01":
            has_non_default_session = True
        if sid == 0x27:
            has_security = True
        if sid in RISKY_SERVICES:
            missing = []
            if sid in {0x2E, 0x31, 0x34, 0x36, 0x37, 0x85} and not has_non_default_session:
                missing.append("non-default diagnostic session before risky service")
            if sid in {0x2E, 0x31, 0x34, 0x36, 0x37} and not has_security:
                missing.append("security access evidence before risky service")
            if missing:
                risky_without_preconditions.append({"step": index, "sid": f"0x{sid:02X}", "missing": missing})
        semantic_issue = routine_semantic_issue(cleaned, routine_names)
        if semantic_issue:
            odx_risky_routines.append({"step": index, **semantic_issue})
        decoded_steps.append({"step": index, "payload_hex": cleaned, "decoded": decoded})

    return {
        "source": str(path),
        "summary": {
            "steps": len(steps),
            "decoded_steps": len(decoded_steps),
            "malformed_steps": len(malformed),
            "risky_steps_without_preconditions": len(risky_without_preconditions),
            "odx_risky_routines": len(odx_risky_routines),
        },
        "issues": {
            "malformed_steps": malformed,
            "risky_steps_without_preconditions": risky_without_preconditions,
            "odx_risky_routines": odx_risky_routines,
        },
        "decoded_steps": decoded_steps,
        "notes": [
            "This lints bytes and sequence assumptions only. It does not transmit requests.",
            "ODX routine semantics are advisory and depend on lightweight metadata extraction.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# UDS Sequence Lint",
        "",
        f"Source: `{report['source']}`",
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
    parser.add_argument("--sequence", required=True, type=Path)
    parser.add_argument("--odx", type=Path, help="Optional ODX/PDX metadata for DID and routine semantics.")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    require_regular_input(args.sequence, "UDS sequence")
    if args.odx is not None:
        require_regular_input(args.odx, "ODX/PDX")
    emit(analyze(args.sequence, args.odx), args.format, args.output)


if __name__ == "__main__":
    main()

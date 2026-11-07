#!/usr/bin/env python3
"""Lint requirements and test traceability artifacts from CSV, JSON, or Markdown tables."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from safe_paths import require_regular_input, require_safe_output


VAGUE_TERMS = {
    "shall be robust",
    "as soon as possible",
    "user friendly",
    "reasonable",
    "sufficient",
    "fast",
    "accurate",
    "reliable",
    "easy",
    "safe",
}
VERIFY_FIELDS = ("verification", "verification_method", "method", "test_method")
EVIDENCE_FIELDS = ("evidence", "evidence_id", "report", "artifact")
REQ_ID_FIELDS = ("id", "requirement_id", "req_id", "requirement")
TEST_ID_FIELDS = ("test_id", "test", "case_id", "verification_id")
TEXT_FIELDS = ("text", "description", "requirement_text", "statement")


def normalize_key(value: str) -> str:
    return value.strip().lower().replace(" ", "_").replace("-", "_")


def normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for row in rows:
        item: dict[str, str] = {}
        for key, value in row.items():
            item[normalize_key(str(key))] = "" if value is None else str(value).strip()
        normalized.append(item)
    return normalized


def parse_markdown_table(text: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return []
    headers = [normalize_key(cell) for cell in lines[0].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[2:]:
        values = [cell.strip() for cell in line.strip("|").split("|")]
        if len(values) != len(headers):
            continue
        rows.append(dict(zip(headers, values)))
    return rows


def parse_artifact(path: Path) -> list[dict[str, str]]:
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid requirements JSON: {path}: {error}") from error
        if isinstance(data, dict):
            if isinstance(data.get("requirements"), list):
                return normalize_rows(data["requirements"])
            if isinstance(data.get("rows"), list):
                return normalize_rows(data["rows"])
        if isinstance(data, list):
            return normalize_rows(data)
        raise SystemExit(f"JSON requirements artifact must be a list or contain rows: {path}")
    if suffix == ".csv":
        return normalize_rows(list(csv.DictReader(text.splitlines())))
    rows = parse_markdown_table(text)
    if rows:
        return rows
    raise SystemExit(f"Unsupported or empty requirements artifact: {path}")


def first_value(row: dict[str, str], fields: tuple[str, ...]) -> str:
    for field in fields:
        if row.get(field):
            return row[field]
    return ""


def split_refs(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[,; ]+", value) if part.strip()]


def analyze(requirements_path: Path, tests_path: Path | None = None) -> dict[str, Any]:
    requirements = parse_artifact(requirements_path)
    tests = parse_artifact(tests_path) if tests_path else []
    req_ids = [first_value(row, REQ_ID_FIELDS) for row in requirements]
    req_id_set = {req_id for req_id in req_ids if req_id}
    duplicate_req_ids = sorted(req_id for req_id in req_id_set if req_ids.count(req_id) > 1)
    orphan_tests: list[dict[str, str]] = []
    linked_req_ids: set[str] = set()
    vague_requirements: list[dict[str, str]] = []
    missing_verification: list[str] = []
    missing_evidence: list[str] = []
    missing_ids: list[int] = []

    for index, row in enumerate(requirements, start=1):
        req_id = first_value(row, REQ_ID_FIELDS)
        text = first_value(row, TEXT_FIELDS)
        if not req_id:
            missing_ids.append(index)
        lower_text = text.lower()
        vague_hits = sorted(term for term in VAGUE_TERMS if term in lower_text)
        if vague_hits:
            vague_requirements.append({"id": req_id or f"row:{index}", "terms": vague_hits, "text": text})
        if not first_value(row, VERIFY_FIELDS):
            missing_verification.append(req_id or f"row:{index}")
        if not first_value(row, EVIDENCE_FIELDS):
            missing_evidence.append(req_id or f"row:{index}")

    for test in tests:
        refs = split_refs(first_value(test, ("requirement_id", "req_id", "requirement", "requirements")))
        test_id = first_value(test, TEST_ID_FIELDS)
        known_refs = [ref for ref in refs if ref in req_id_set]
        linked_req_ids.update(known_refs)
        if refs and not known_refs:
            orphan_tests.append({"test_id": test_id, "refs": refs})
        elif not refs:
            orphan_tests.append({"test_id": test_id, "refs": []})

    return {
        "source": {"requirements": str(requirements_path), "tests": str(tests_path) if tests_path else None},
        "summary": {
            "requirements": len(requirements),
            "tests": len(tests),
            "requirements_with_test_links": len(linked_req_ids),
        },
        "issues": {
            "missing_requirement_ids": missing_ids,
            "duplicate_requirement_ids": duplicate_req_ids,
            "vague_requirements": vague_requirements,
            "missing_verification_method": sorted(missing_verification),
            "missing_evidence": sorted(missing_evidence),
            "orphan_tests": orphan_tests,
            "requirements_without_tests": sorted(req_id_set - linked_req_ids) if tests else [],
        },
        "rows": {"requirements": requirements, "tests": tests},
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Requirements Traceability Lint",
        "",
        f"Requirements: `{report['source']['requirements']}`",
        f"Tests: `{report['source']['tests']}`",
        "",
        "## Summary",
        "",
        f"- Requirements: {report['summary']['requirements']}",
        f"- Tests: {report['summary']['tests']}",
        f"- Requirements with test links: {report['summary']['requirements_with_test_links']}",
        "",
        "## Issues",
        "",
    ]
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", required=True, type=Path)
    parser.add_argument("--tests", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    require_regular_input(args.requirements, "Requirements")
    if args.tests is not None:
        require_regular_input(args.tests, "Tests")
    emit(analyze(args.requirements, args.tests), args.format, args.output)


if __name__ == "__main__":
    main()

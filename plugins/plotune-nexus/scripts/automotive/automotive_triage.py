#!/usr/bin/env python3
"""Run offline automotive analyzers against a mixed set of local artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

import a2l_lab_check
import autosar_architecture_report
import can_trace_summarize
import dbc_sanity
import odx_inspect
import requirements_trace_lint
import safety_workproduct
import tara_workproduct
import uds_sequence_lint
from safe_paths import require_regular_input, require_safe_output


def lower_suffix(path: Path) -> str:
    return path.suffix.lower()


def looks_like_trace(path: Path) -> bool:
    if lower_suffix(path) in {".asc", ".trc", ".log"}:
        text = path.read_text(encoding="utf-8", errors="replace")[:2048]
        return "#" in text or " Rx " in text or " Tx " in text
    return False


def classify_table(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="replace")[:4096].lower()
    if "request_hex" in text or "payload_hex" in text:
        return "uds_sequence"
    if "threat_id" in text or "attack_path" in text or "cybersecurity_goal" in text:
        return "tara"
    if "hazard_id" in text or "failure_mode_id" in text or "safety_goal" in text:
        return "safety"
    if "requirement_id" in text or "verification_method" in text or "evidence" in text:
        return "requirements"
    return None


def first_by_suffix(paths: list[Path], suffixes: set[str]) -> Path | None:
    for path in paths:
        if lower_suffix(path) in suffixes:
            return path
    return None


def run_checked(label: str, path: Path, call: Callable[[], dict[str, Any]], handoff: str) -> dict[str, Any]:
    try:
        return {"kind": label, "source": str(path), "status": "ok", "report": call(), "nexus_handoff": handoff}
    except SystemExit as error:
        return {"kind": label, "source": str(path), "status": "error", "error": str(error), "nexus_handoff": handoff}
    except Exception as error:
        return {"kind": label, "source": str(path), "status": "error", "error": f"{type(error).__name__}: {error}", "nexus_handoff": handoff}


def analyze(inputs: list[Path], bitrate: int | None = None) -> dict[str, Any]:
    dbc = first_by_suffix(inputs, {".dbc"})
    lab = first_by_suffix(inputs, {".lab"})
    manifest = first_by_suffix(inputs, {".json"})
    results: list[dict[str, Any]] = []

    for path in inputs:
        suffix = lower_suffix(path)
        if suffix == ".dbc":
            results.append(
                run_checked(
                    "dbc_sanity",
                    path,
                    lambda path=path: dbc_sanity.analyze(path),
                    "Use plotune-can-workflows only after the DBC issues and frame IDs are understood.",
                )
            )
        elif looks_like_trace(path):
            results.append(
                run_checked(
                    "can_trace_summary",
                    path,
                    lambda path=path: can_trace_summarize.summarize(path, dbc, bitrate),
                    "Use plotune-can-workflows for bounded live capture or replay after offline trace findings are reviewed.",
                )
            )
        elif suffix in {".a2l", ".aml"}:
            results.append(
                run_checked(
                    "a2l_lab_check",
                    path,
                    lambda path=path: a2l_lab_check.analyze(path, lab),
                    "Use plotune-xcp-workflows for live measurement only with target, transport, and rollback context.",
                )
            )
        elif suffix in {".odx", ".odx-d", ".pdx", ".xml"} and "odx" in path.name.lower():
            results.append(
                run_checked(
                    "odx_inspect",
                    path,
                    lambda path=path: odx_inspect.analyze(path),
                    "Use plotune-uds-doip-diagnostics for bounded diagnostic execution after payloads are approved.",
                )
            )
        elif suffix in {".arxml"}:
            results.append(
                run_checked(
                    "autosar_architecture_report",
                    path,
                    lambda path=path: autosar_architecture_report.analyze(path, manifest if manifest != path else None),
                    "Use Nexus evidence collection only after expected network, diagnostic, or container behavior is explicit.",
                )
            )
        elif suffix in {".csv", ".md", ".json"}:
            table_kind = classify_table(path)
            if table_kind == "uds_sequence":
                results.append(
                    run_checked(
                        "uds_sequence_lint",
                        path,
                        lambda path=path: uds_sequence_lint.analyze(path),
                        "Use plotune-uds-doip-diagnostics only after risky sequence preconditions are closed.",
                    )
                )
            elif table_kind == "tara":
                results.append(
                    run_checked(
                        "tara_lint",
                        path,
                        lambda path=path: tara_workproduct.lint("threat-scenario", path),
                        "Use Nexus only for authorized evidence collection, not active attack execution.",
                    )
                )
            elif table_kind == "safety":
                results.append(
                    run_checked(
                        "safety_lint",
                        path,
                        lambda path=path: safety_workproduct.lint("hara", path),
                        "Use Nexus only to gather bounded verification evidence tied to approved safety tests.",
                    )
                )
            elif table_kind == "requirements":
                results.append(
                    run_checked(
                        "requirements_trace_lint",
                        path,
                        lambda path=path: requirements_trace_lint.analyze(path),
                        "Use plotune-test-sequences-reporting to draft bounded tests from closed requirements.",
                    )
                )

    return {
        "inputs": [str(path) for path in inputs],
        "summary": {
            "inputs": len(inputs),
            "analyzers_run": len(results),
            "errors": sum(1 for result in results if result["status"] != "ok"),
        },
        "results": results,
        "notes": [
            "Triage is offline and read-only except for an explicit --output report.",
            "Live Nexus actions are handoffs, not actions performed by this script.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Automotive Artifact Triage",
        "",
        "## Summary",
        "",
        f"- Inputs: {report['summary']['inputs']}",
        f"- Analyzers run: {report['summary']['analyzers_run']}",
        f"- Errors: {report['summary']['errors']}",
        "",
        "## Results",
        "",
    ]
    for result in report["results"]:
        lines.append(f"- `{result['kind']}` on `{result['source']}`: {result['status']}")
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
    parser.add_argument("--bitrate", type=int)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    for path in args.inputs:
        require_regular_input(path, "Input artifact")
    emit(analyze(args.inputs, args.bitrate), args.format, args.output)


if __name__ == "__main__":
    main()

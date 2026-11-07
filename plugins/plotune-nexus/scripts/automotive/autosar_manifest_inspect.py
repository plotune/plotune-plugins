#!/usr/bin/env python3
"""Offline AUTOSAR ARXML and Adaptive manifest inventory checks."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any

from safe_paths import require_regular_input, require_safe_output


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(element: ET.Element, name: str) -> str | None:
    for child in element:
        if local_name(child.tag) == name and child.text:
            return child.text.strip()
    return None


def iter_elements(root: ET.Element, local: str) -> list[ET.Element]:
    return [element for element in root.iter() if local_name(element.tag) == local]


def collect_arxml(path: Path) -> dict[str, Any]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        raise SystemExit(f"Invalid ARXML XML: {path}: {error}") from error
    short_names = [element.text.strip() for element in iter_elements(root, "SHORT-NAME") if element.text and element.text.strip()]
    components: list[str] = []
    interfaces: list[str] = []
    executables: list[str] = []
    references: list[str] = []
    for element in root.iter():
        tag = local_name(element.tag)
        name = child_text(element, "SHORT-NAME")
        if name and "COMPONENT-TYPE" in tag:
            components.append(name)
        elif name and tag.endswith("INTERFACE"):
            interfaces.append(name)
        elif name and tag == "EXECUTABLE":
            executables.append(name)
        if tag.endswith("TREF") or tag.endswith("REF"):
            if element.text and element.text.strip().startswith("/"):
                references.append(element.text.strip())
    known_paths = set()
    for name in short_names:
        known_paths.add(f"/{name}")
        known_paths.add(name)
    # Add simple package path combinations for common single-package ARXML files.
    package_names = [child_text(element, "SHORT-NAME") for element in iter_elements(root, "AR-PACKAGE")]
    for package in [item for item in package_names if item]:
        for name in short_names:
            known_paths.add(f"/{package}/{name}")
    unresolved = sorted(ref for ref in references if ref not in known_paths)
    return {
        "short_names": short_names,
        "components": sorted(set(components)),
        "interfaces": sorted(set(interfaces)),
        "executables": sorted(set(executables)),
        "references": sorted(set(references)),
        "duplicate_short_names": sorted(name for name, count in Counter(short_names).items() if count > 1),
        "unresolved_references": unresolved,
    }


def collect_manifest(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"executables": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid manifest JSON: {path}: {error}") from error
    if isinstance(data, dict):
        executables = data.get("executables", [])
        if isinstance(executables, list):
            return {"executables": executables}
    return {"executables": []}


def analyze(arxml_path: Path, manifest_path: Path | None) -> dict[str, Any]:
    arxml = collect_arxml(arxml_path)
    manifest = collect_manifest(manifest_path)
    return {
        "source": {"arxml": str(arxml_path), "manifest": str(manifest_path) if manifest_path else None},
        "summary": {
            "short_names": len(arxml["short_names"]),
            "components": len(arxml["components"]),
            "interfaces": len(arxml["interfaces"]),
            "executables": len(arxml["executables"]),
            "manifest_executables": len(manifest["executables"]),
        },
        "issues": {
            "duplicate_short_names": arxml["duplicate_short_names"],
            "unresolved_references": arxml["unresolved_references"],
        },
        "inventory": {
            "components": arxml["components"],
            "interfaces": arxml["interfaces"],
            "executables": arxml["executables"],
            "manifest_executables": manifest["executables"],
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# AUTOSAR Manifest Inspection",
        "",
        f"ARXML: `{report['source']['arxml']}`",
        f"Manifest: `{report['source']['manifest']}`",
        "",
        "## Summary",
        "",
        f"- Components: {report['summary']['components']}",
        f"- Interfaces: {report['summary']['interfaces']}",
        f"- ARXML executables: {report['summary']['executables']}",
        f"- Manifest executables: {report['summary']['manifest_executables']}",
        "",
        "## Issues",
        "",
        f"- Duplicate short names: {len(report['issues']['duplicate_short_names'])}",
        f"- Unresolved references: {len(report['issues']['unresolved_references'])}",
    ]
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
    parser.add_argument("--arxml", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    require_regular_input(args.arxml, "ARXML")
    if args.manifest is not None:
        require_regular_input(args.manifest, "Manifest")
    emit(analyze(args.arxml, args.manifest), args.format, args.output)


if __name__ == "__main__":
    main()

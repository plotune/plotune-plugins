#!/usr/bin/env python3
"""Build a lightweight AUTOSAR architecture inventory from ARXML and optional manifest JSON."""

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


def descendant_text(element: ET.Element, name: str) -> str | None:
    for child in element.iter():
        if local_name(child.tag) == name and child.text:
            return child.text.strip()
    return None


def reference_texts(element: ET.Element) -> list[str]:
    refs: list[str] = []
    for child in element.iter():
        tag = local_name(child.tag)
        if (tag.endswith("REF") or tag.endswith("TREF")) and child.text and child.text.strip():
            refs.append(child.text.strip())
    return refs


def parse_arxml(path: Path) -> dict[str, Any]:
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        raise SystemExit(f"Invalid ARXML XML: {path}: {error}") from error

    short_names = [element.text.strip() for element in root.iter() if local_name(element.tag) == "SHORT-NAME" and element.text and element.text.strip()]
    packages = [child_text(element, "SHORT-NAME") for element in root.iter() if local_name(element.tag) == "AR-PACKAGE"]
    components: list[dict[str, Any]] = []
    interfaces: list[dict[str, Any]] = []
    ports: list[dict[str, Any]] = []
    runnables: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    connectors: list[dict[str, Any]] = []
    services: list[dict[str, Any]] = []
    executables: list[dict[str, Any]] = []
    references: list[str] = []

    for element in root.iter():
        tag = local_name(element.tag)
        name = child_text(element, "SHORT-NAME")
        references.extend(reference_texts(element))
        if name and "COMPONENT-TYPE" in tag:
            port_count = sum(1 for child in element.iter() if local_name(child.tag).endswith("PORT-PROTOTYPE"))
            components.append({"name": name, "kind": tag, "port_count": port_count})
        elif name and tag.endswith("INTERFACE"):
            interfaces.append({"name": name, "kind": tag})
        elif name and tag.endswith("PORT-PROTOTYPE"):
            refs = reference_texts(element)
            ports.append({"name": name, "kind": tag, "references": refs})
        elif name and "RUNNABLE" in tag:
            runnables.append({"name": name, "kind": tag})
        elif name and tag.endswith("EVENT"):
            events.append({"name": name, "kind": tag, "start_on_event": descendant_text(element, "START-ON-EVENT-REF")})
        elif name and "CONNECTOR" in tag:
            connectors.append({"name": name, "kind": tag, "references": reference_texts(element)})
        elif name and ("SERVICE" in tag or "SOMEIP" in tag or "SOME-IP" in tag):
            services.append({"name": name, "kind": tag})
        elif name and tag == "EXECUTABLE":
            executables.append({"name": name, "kind": tag})

    known_paths = set(short_names)
    for name in short_names:
        known_paths.add(f"/{name}")
    for package in [item for item in packages if item]:
        for name in short_names:
            known_paths.add(f"/{package}/{name}")
    unresolved = sorted(ref for ref in set(references) if ref.startswith("/") and ref not in known_paths)
    return {
        "summary": {
            "packages": len([item for item in packages if item]),
            "short_names": len(short_names),
            "components": len(components),
            "interfaces": len(interfaces),
            "ports": len(ports),
            "runnables": len(runnables),
            "events": len(events),
            "connectors": len(connectors),
            "services": len(services),
            "executables": len(executables),
        },
        "inventory": {
            "components": components,
            "interfaces": interfaces,
            "ports": ports,
            "runnables": runnables,
            "events": events,
            "connectors": connectors,
            "services": services,
            "executables": executables,
        },
        "issues": {
            "duplicate_short_names": sorted(name for name, count in Counter(short_names).items() if count > 1),
            "unresolved_references": unresolved,
            "ports_without_interface_refs": [port["name"] for port in ports if not port["references"]],
            "components_without_ports": [component["name"] for component in components if component["port_count"] == 0],
        },
    }


def parse_manifest(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"executables": [], "services": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid manifest JSON: {path}: {error}") from error
    if not isinstance(data, dict):
        return {"executables": [], "services": []}
    return {
        "executables": data.get("executables", []) if isinstance(data.get("executables", []), list) else [],
        "services": data.get("services", []) if isinstance(data.get("services", []), list) else [],
    }


def analyze(arxml_path: Path, manifest_path: Path | None) -> dict[str, Any]:
    arxml = parse_arxml(arxml_path)
    manifest = parse_manifest(manifest_path)
    return {
        "source": {"arxml": str(arxml_path), "manifest": str(manifest_path) if manifest_path else None},
        "summary": {**arxml["summary"], "manifest_executables": len(manifest["executables"]), "manifest_services": len(manifest["services"])},
        "issues": arxml["issues"],
        "inventory": {**arxml["inventory"], "manifest": manifest},
        "notes": ["This is an offline architecture inventory. Vendor schema validation remains a separate step."],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# AUTOSAR Architecture Report",
        "",
        f"ARXML: `{report['source']['arxml']}`",
        f"Manifest: `{report['source']['manifest']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key.replace('_', ' ')}: {value}")
    lines.extend(["", "## Issues", ""])
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

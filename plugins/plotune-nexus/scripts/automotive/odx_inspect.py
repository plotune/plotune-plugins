#!/usr/bin/env python3
"""Inspect ODX or PDX diagnostic database metadata without diagnostic transport access."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

from safe_paths import require_regular_input, require_safe_output


MAX_PDX_DOCUMENTS = 64
MAX_XML_BYTES = 8 * 1024 * 1024
MAX_PDX_TOTAL_BYTES = 32 * 1024 * 1024


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(element: ET.Element, name: str) -> str | None:
    for child in element:
        if local_name(child.tag) == name and child.text:
            return child.text.strip()
    return None


def text_of_first(element: ET.Element, names: set[str]) -> str | None:
    for child in element.iter():
        if local_name(child.tag) in names and child.text and child.text.strip():
            return child.text.strip()
    return None


def hex_or_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    try:
        return f"0x{int(cleaned, 0):X}"
    except ValueError:
        return cleaned


def read_xml_documents(path: Path) -> list[tuple[str, bytes]]:
    suffix = path.suffix.lower()
    if suffix == ".pdx" or zipfile.is_zipfile(path):
        documents: list[tuple[str, bytes]] = []
        total_bytes = 0
        with zipfile.ZipFile(path) as archive:
            infos = [
                info
                for info in archive.infolist()
                if info.filename.lower().endswith((".odx", ".odx-d", ".xml")) and not info.filename.endswith("/")
            ]
            if len(infos) > MAX_PDX_DOCUMENTS:
                raise SystemExit(f"PDX contains too many ODX/XML documents: {len(infos)} > {MAX_PDX_DOCUMENTS}")
            for info in sorted(infos, key=lambda item: item.filename):
                if info.file_size > MAX_XML_BYTES:
                    raise SystemExit(f"PDX member too large: {info.filename} ({info.file_size} bytes)")
                total_bytes += info.file_size
                if total_bytes > MAX_PDX_TOTAL_BYTES:
                    raise SystemExit(f"PDX ODX/XML payload too large: {total_bytes} bytes")
                documents.append((info.filename, archive.read(info.filename)))
        if not documents:
            raise SystemExit(f"No ODX/XML documents found in PDX: {path}")
        return documents
    if path.stat().st_size > MAX_XML_BYTES:
        raise SystemExit(f"ODX/XML file too large: {path} ({path.stat().st_size} bytes)")
    return [(path.name, path.read_bytes())]


def collect_document(name: str, payload: bytes) -> dict[str, Any]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise SystemExit(f"Invalid ODX XML in {name}: {error}") from error

    variants: list[str] = []
    services: list[dict[str, Any]] = []
    dids: list[dict[str, Any]] = []
    dtcs: list[dict[str, Any]] = []
    routines: list[dict[str, Any]] = []
    sessions: list[dict[str, Any]] = []
    references: list[str] = []
    short_names: list[str] = []
    known_ids: list[str] = []

    for element in root.iter():
        tag = local_name(element.tag)
        short_name = child_text(element, "SHORT-NAME")
        if short_name:
            short_names.append(short_name)
        for key in ("ID", "ODX-LINK-ID"):
            value = element.attrib.get(key)
            if value:
                known_ids.append(value)
        if tag == "ODX-LINK-ID" and element.text and element.text.strip():
            known_ids.append(element.text.strip())
        if tag.endswith("REF") or tag.endswith("SNREF"):
            ref_id = (
                element.attrib.get("ID-REF")
                or element.attrib.get("ODX-LINK-REF")
                or element.attrib.get("SHORT-NAME")
                or (element.text or "").strip()
            )
            if ref_id:
                references.append(ref_id)
        if short_name and "ECU-VARIANT" in tag:
            variants.append(short_name)
        elif short_name and "DIAG-SERVICE" in tag:
            service_id = hex_or_text(text_of_first(element, {"SERVICE-ID", "CODED-VALUE", "BYTE-VALUE"}))
            services.append({"name": short_name, "service_id": service_id})
        elif short_name and ("DATA-IDENTIFIER" in tag or tag.endswith("DID")):
            dids.append({"name": short_name, "identifier": hex_or_text(text_of_first(element, {"ID", "CODED-VALUE"}))})
        elif short_name and ("DTC" in tag or "TROUBLE-CODE" in tag):
            dtcs.append({"name": short_name, "code": hex_or_text(text_of_first(element, {"TROUBLE-CODE", "CODE", "CODED-VALUE"}))})
        elif short_name and ("ROUTINE" in tag):
            routines.append({"name": short_name, "identifier": hex_or_text(text_of_first(element, {"ROUTINE-ID", "CODED-VALUE"}))})
        elif short_name and ("SESSION" in tag):
            sessions.append({"name": short_name, "identifier": hex_or_text(text_of_first(element, {"SESSION-ID", "CODED-VALUE"}))})

    known = set(short_names) | set(known_ids)
    unresolved = sorted(ref for ref in references if ref and ref not in known)
    return {
        "document": name,
        "summary": {
            "short_names": len(short_names),
            "variants": len(set(variants)),
            "services": len(services),
            "dids": len(dids),
            "dtcs": len(dtcs),
            "routines": len(routines),
            "sessions": len(sessions),
            "references": len(references),
        },
        "inventory": {
            "variants": sorted(set(variants)),
            "services": services,
            "dids": dids,
            "dtcs": dtcs,
            "routines": routines,
            "sessions": sessions,
        },
        "issues": {
            "unresolved_references": unresolved,
        },
    }


def analyze(path: Path) -> dict[str, Any]:
    documents = [collect_document(name, payload) for name, payload in read_xml_documents(path)]
    summary = {
        "documents": len(documents),
        "variants": sum(doc["summary"]["variants"] for doc in documents),
        "services": sum(doc["summary"]["services"] for doc in documents),
        "dids": sum(doc["summary"]["dids"] for doc in documents),
        "dtcs": sum(doc["summary"]["dtcs"] for doc in documents),
        "routines": sum(doc["summary"]["routines"] for doc in documents),
        "sessions": sum(doc["summary"]["sessions"] for doc in documents),
    }
    return {
        "source": str(path),
        "summary": summary,
        "documents": documents,
        "notes": [
            "This is a lightweight metadata inventory, not a substitute for licensed ODX validation tooling.",
            "No ECU, DoIP, CAN, or ISO-TP connection is opened.",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# ODX/PDX Inspection",
        "",
        f"Source: `{report['source']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key.replace('_', ' ')}: {value}")
    lines.extend(["", "## Documents", ""])
    for document in report["documents"]:
        issues = len(document["issues"]["unresolved_references"])
        lines.append(f"- `{document['document']}`: {document['summary']['services']} services, {issues} unresolved references")
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
    parser.add_argument("--odx", required=True, type=Path, help="ODX, ODX-D, XML, or PDX file.")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    require_regular_input(args.odx, "ODX/PDX")
    emit(analyze(args.odx), args.format, args.output)


if __name__ == "__main__":
    main()

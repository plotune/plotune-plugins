#!/usr/bin/env python3
"""
Signal backtrace orchestrator: traces a signal through A2L, Intel HEX, and EHB files.

Imports inspect_a2l, inspect_ehb, and resolve_hex from the same directory.
Run from the plugin package root (directory containing skills/, scripts/, references/).
"""
import argparse
import json
import re
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import inspect_a2l
import inspect_ehb
import resolve_hex


MAX_BOUNDARY_SYMBOLS = 40


def normalize_groups(groups):
    return [group.strip() for group in groups or [] if group and group.strip()]


def matches_group(name, groups):
    if not groups:
        return True
    lowered_name = name.lower()
    for group in groups:
        lowered_group = group.lower()
        if lowered_group == "fid":
            if "fid" in lowered_name or "dinh_stfid" in lowered_name:
                return True
        elif lowered_group == "mil":
            if "mil" in lowered_name or "malfunction indicator lamp" in lowered_name or "obd lamp" in lowered_name:
                return True
        elif lowered_group in lowered_name:
            return True
    return False


def determine_start_kind(symbol_result):
    if symbol_result["measurements"]:
        return "measurement"
    if symbol_result["characteristics"]:
        return "characteristic"
    return "signal"


def evidence_from_a2l_match(match, kind, a2l_path):
    return {
        "source": str(a2l_path),
        "kind": kind,
        "line": match.get("start_line"),
        "detail": match.get("description") or match.get("name", ""),
    }


def add_node(nodes_by_id, node_id, kind, level, label="", evidence=None):
    if node_id not in nodes_by_id:
        nodes_by_id[node_id] = {
            "id": node_id,
            "kind": kind,
            "level": level,
            "label": label,
            "evidence": evidence or [],
        }
    else:
        nodes_by_id[node_id]["level"] = min(nodes_by_id[node_id]["level"], level)
        nodes_by_id[node_id]["evidence"].extend(evidence or [])


def collect_candidate_sources(signal, function_summary):
    candidates = []
    if signal in function_summary.get("loc_measurement", []) or signal in function_summary.get("out_measurement", []):
        for source_name in function_summary.get("in_measurement", []):
            candidates.append((source_name, "input_measurement"))
        for calibration_name in function_summary.get("def_characteristic", []):
            candidates.append((calibration_name, "calibration_dependency"))
    return candidates


def unique_candidates(candidates, limit=80):
    seen = set()
    unique = []
    for candidate_name, candidate_kind in candidates:
        if candidate_name in seen:
            continue
        seen.add(candidate_name)
        unique.append((candidate_name, candidate_kind))
        if len(unique) >= limit:
            break
    return unique


def parse_hex_address(address_text):
    if not address_text:
        return None
    try:
        return int(address_text, 0)
    except ValueError:
        return None


def characteristic_length(characteristic):
    record_layout = characteristic.get("record_layout", "").lower()
    if "64" in record_layout:
        return 8
    if "32" in record_layout:
        return 4
    if "16" in record_layout or "word" in record_layout:
        return 2
    return 1


def resolve_calibrations(a2l_path, hex_path, calibration_names):
    if not calibration_names:
        return []
    calibration_result = inspect_a2l.inspect_a2l_file(a2l_path, calibration_names[:40])
    decisions_by_name = {}
    resolution_requests = []
    characteristic_by_name = {}
    for calibration_name in calibration_names[:40]:
        symbol_result = calibration_result["symbols"].get(calibration_name, {})
        characteristics = symbol_result.get("characteristics", [])
        if not characteristics:
            decisions_by_name[calibration_name] = {
                "name": calibration_name,
                "address": "",
                "raw_bytes": "",
                "decoded_value": None,
                "confidence": "unresolved",
                "decision": "unresolved",
                "reason": "characteristic metadata not found in A2L",
                "evidence": [],
            }
            continue
        characteristic = characteristics[0]
        address_text = characteristic.get("address", "")
        address = parse_hex_address(address_text)
        evidence = [evidence_from_a2l_match(characteristic, "characteristic", a2l_path)]
        if address is None:
            decisions_by_name[calibration_name] = {
                "name": calibration_name,
                "address": address_text,
                "raw_bytes": "",
                "decoded_value": None,
                "confidence": "unresolved",
                "decision": "unresolved",
                "reason": "characteristic address unavailable or not parseable",
                "evidence": evidence,
            }
            continue
        characteristic_by_name[calibration_name] = (characteristic, evidence)
        resolution_requests.append((calibration_name, address, characteristic_length(characteristic)))

    resolved_by_name = resolve_hex.resolve_many_bytes(hex_path, resolution_requests) if resolution_requests else {}
    for calibration_name, (characteristic, evidence) in characteristic_by_name.items():
        resolved = resolved_by_name[calibration_name]
        decisions_by_name[calibration_name] = {
            "name": calibration_name,
            "address": resolved["address"],
            "raw_bytes": resolved.get("raw_bytes", ""),
            "decoded_value": None,
            "raw_unsigned_big_endian": resolved.get("unsigned_big_endian"),
            "raw_unsigned_little_endian": resolved.get("unsigned_little_endian"),
            "confidence": "unresolved",
            "decision": "unresolved",
            "reason": "condition semantics unavailable; value resolved but route enablement is not claimed",
            "evidence": evidence,
            "hex_status": resolved["status"],
        }
    return [decisions_by_name[calibration_name] for calibration_name in calibration_names[:40]]


def collect_contexts(a2l_path, symbols):
    if not symbols:
        return {}
    a2l_result = inspect_a2l.inspect_a2l_file(a2l_path, symbols)
    contexts = {}
    for symbol in symbols:
        symbol_result = a2l_result["symbols"].get(symbol, inspect_a2l.empty_symbol_result())
        function_evidence = []
        candidate_sources = []
        for function_summary in symbol_result["functions"]:
            function_evidence.append(evidence_from_a2l_match(function_summary, "function", a2l_path))
            candidate_sources.extend(collect_candidate_sources(symbol, function_summary))
        contexts[symbol] = {
            "symbol_result": symbol_result,
            "function_evidence": function_evidence,
            "candidate_sources": unique_candidates(candidate_sources),
        }
    return contexts


def skipped_route(candidate_name, target_name, reason, detail, evidence):
    return {
        "from": candidate_name,
        "to": target_name,
        "reason": reason,
        "detail": detail,
        "evidence": evidence,
    }


def calibration_skip_reason(decision):
    if decision.get("decision") == "disabled":
        return "disabled_calibration"
    return "unresolved_calibration"


def mermaid_id(node_id):
    sanitized = re.sub(r"[^0-9A-Za-z_]", "_", node_id)
    if not sanitized or sanitized[0].isdigit():
        sanitized = f"n_{sanitized}"
    return sanitized


def build_mermaid(nodes, edges):
    lines = ["graph TD"]
    if not edges:
        for node in nodes:
            lines.append(f'  {mermaid_id(node["id"])}["{node["id"]}"]')
        return "\n".join(lines)
    for edge in edges:
        from_id = mermaid_id(edge["from"])
        to_id = mermaid_id(edge["to"])
        label = edge.get("kind", "edge")
        lines.append(f'  {from_id}["{edge["from"]}"] -->|{label}| {to_id}["{edge["to"]}"]')
    return "\n".join(lines)


def run_signal_backtrace(signal, a2l_path, hex_path, ehb_paths, max_depth, groups=None):
    normalized_groups = normalize_groups(groups)
    initial_context = collect_contexts(a2l_path, [signal])[signal]
    symbol_result = initial_context["symbol_result"]
    nodes_by_id = {}
    start_evidence = []
    for measurement in symbol_result["measurements"]:
        start_evidence.append(evidence_from_a2l_match(measurement, "measurement", a2l_path))
    for characteristic in symbol_result["characteristics"]:
        start_evidence.append(evidence_from_a2l_match(characteristic, "characteristic", a2l_path))
    add_node(
        nodes_by_id,
        signal,
        determine_start_kind(symbol_result),
        0,
        symbol_result["measurements"][0]["description"] if symbol_result["measurements"] else "",
        start_evidence,
    )

    edges = []
    skipped_routes = []
    calibration_decisions = []
    calibration_decisions_by_name = {}
    seen_symbols = {signal}
    frontier = [signal]

    for parent_level in range(max_depth):
        contexts = initial_context if parent_level == 0 and frontier == [signal] else None
        context_by_symbol = {signal: initial_context} if contexts is not None else collect_contexts(a2l_path, frontier)
        next_frontier = []
        level_calibration_names = []
        candidate_rows = []
        for target_name in frontier:
            context = context_by_symbol.get(target_name)
            if not context:
                continue
            for candidate_name, candidate_kind in context["candidate_sources"]:
                candidate_rows.append(
                    (
                        target_name,
                        candidate_name,
                        candidate_kind,
                        context["function_evidence"][:3],
                    )
                )
                seen_symbols.add(candidate_name)
                if candidate_kind == "calibration_dependency" and candidate_name not in calibration_decisions_by_name:
                    level_calibration_names.append(candidate_name)

        if level_calibration_names:
            unique_level_calibration_names = [
                candidate_name
                for candidate_name, _candidate_kind in unique_candidates(
                    [(name, "calibration_dependency") for name in level_calibration_names],
                    limit=40,
                )
            ]
            new_decisions = resolve_calibrations(a2l_path, hex_path, unique_level_calibration_names)
            for decision in new_decisions:
                calibration_decisions.append(decision)
                calibration_decisions_by_name[decision["name"]] = decision

        for target_name, candidate_name, candidate_kind, evidence in candidate_rows:
            edge = {
                "from": candidate_name,
                "to": target_name,
                "kind": candidate_kind,
                "confidence": "confirmed",
                "evidence": evidence,
            }
            if not matches_group(candidate_name, normalized_groups):
                skipped_routes.append(
                    skipped_route(
                        candidate_name,
                        target_name,
                        "filtered",
                        f"outside requested groups: {', '.join(normalized_groups)}",
                        edge["evidence"],
                    )
                )
                continue
            if candidate_kind == "calibration_dependency":
                decision = calibration_decisions_by_name.get(candidate_name)
                if not decision or decision.get("decision") != "enabled":
                    detail = decision["reason"] if decision else "calibration decision unavailable"
                    skipped_routes.append(
                        skipped_route(
                            candidate_name,
                            target_name,
                            calibration_skip_reason(decision or {}),
                            detail,
                            edge["evidence"],
                        )
                    )
                    continue
                edge["confidence"] = "calibration_confirmed"
            add_node(nodes_by_id, candidate_name, candidate_kind, parent_level + 1, "", evidence)
            edges.append(edge)
            if candidate_kind == "input_measurement" and candidate_name not in next_frontier:
                next_frontier.append(candidate_name)
        frontier = next_frontier
        if not frontier:
            break

    if max_depth > 0 and frontier:
        boundary_contexts = collect_contexts(a2l_path, frontier[:MAX_BOUNDARY_SYMBOLS])
        for target_name, context in boundary_contexts.items():
            for candidate_name, _candidate_kind in context["candidate_sources"]:
                seen_symbols.add(candidate_name)
                skipped_routes.append(
                    skipped_route(
                        candidate_name,
                        target_name,
                        "depth_limited",
                        f"max_depth={max_depth} stops expansion beyond level {max_depth}",
                        context["function_evidence"][:3],
                    )
                )

    if max_depth == 0:
        for candidate_name, candidate_kind in initial_context["candidate_sources"]:
            skipped_routes.append(
                skipped_route(
                    candidate_name,
                    signal,
                    "depth_limited",
                    "max_depth=0 stops level 1 expansion",
                    initial_context["function_evidence"][:3],
                )
            )

    ehb_symbols = list(seen_symbols)[:40]
    ehb_result = inspect_ehb.search_ehb_files(ehb_paths, ehb_symbols, max_matches=40)
    evidence_entries = [
        {
            "source": match["file"],
            "entry": match["entry"],
            "symbol": match["symbol"],
            "kind": "ehb_text_match",
            "detail": match["snippet"],
        }
        for match in ehb_result["matches"]
    ]

    nodes = list(nodes_by_id.values())
    graph_text = build_mermaid(nodes, edges)
    return {
        "request": {
            "signal": signal,
            "max_depth": max_depth,
            "groups": normalized_groups,
            "files": {
                "a2l": str(a2l_path),
                "hex": str(hex_path),
                "ehb": [str(ehb_path) for ehb_path in ehb_paths],
            },
        },
        "nodes": nodes,
        "edges": edges,
        "calibration_decisions": calibration_decisions,
        "skipped_routes": skipped_routes,
        "evidence": evidence_entries,
        "graph": {
            "format": "mermaid",
            "text": graph_text,
        },
        "summary": (
            f"Traced {signal} to depth {max_depth}. "
            f"Followed {len(edges)} edge(s), skipped {len(skipped_routes)} route(s), "
            f"and found {len(evidence_entries)} EHB evidence item(s)."
        ),
        "open_questions": build_open_questions(calibration_decisions),
    }


def build_open_questions(calibration_decisions):
    questions = []
    for decision in calibration_decisions:
        if decision["decision"] == "unresolved":
            questions.append(f"{decision['name']}: {decision['reason']}")
    return questions


def parse_args():
    parser = argparse.ArgumentParser(description="Backtrace a signal through A2L, Intel HEX, and EHB documentation.")
    parser.add_argument("--signal", required=True, help="Start signal name (exact match)")
    parser.add_argument("--a2l", required=True, help="Path to A2L file")
    parser.add_argument("--hex", required=True, help="Path to Intel HEX calibration file")
    parser.add_argument("--ehb", action="append", required=True, help="Path to EHB file (repeat for multiple)")
    parser.add_argument("--max-depth", type=int, required=True, help="Maximum trace depth")
    parser.add_argument("--group", action="append", default=[], help="Optional group filter (FID, MIL, or prefix)")
    parser.add_argument("--output", help="Write JSON result to this file instead of stdout")
    return parser.parse_args()


def main():
    args = parse_args()
    result = run_signal_backtrace(
        signal=args.signal,
        a2l_path=Path(args.a2l),
        hex_path=Path(args.hex),
        ehb_paths=[Path(ehb_path) for ehb_path in args.ehb],
        max_depth=args.max_depth,
        groups=args.group,
    )
    output_json = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(output_json, encoding="utf-8")
        print(args.output)
    else:
        print(output_json)


if __name__ == "__main__":
    main()

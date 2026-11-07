#!/usr/bin/env python3
"""Convert signal-backtrace JSON outputs into human-readable Markdown reports with CSV exports."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def markdown_escape(value):
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def code(value):
    return f"`{markdown_escape(value)}`"


def count_by(items, key):
    return Counter(item.get(key, "unknown") for item in items)


def table(headers, rows):
    if not rows:
        return "_None._\n"
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _header in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(markdown_escape(cell) for cell in row) + " |")
    return "\n".join(lines) + "\n"


def limited(items, max_items):
    return items[:max_items]


def trace_request(trace):
    return trace.get("request", {})


def source_files(request):
    files = request.get("files", {})
    lines = []
    for key in ("a2l", "hex"):
        if files.get(key):
            lines.append(f"- {key.upper()}: {code(files[key])}")
    for ehb_file in as_list(files.get("ehb")):
        lines.append(f"- EHB: {code(ehb_file)}")
    return "\n".join(lines) if lines else "- No source files listed."


def build_reason_rows(skipped_routes):
    return [
        [code(reason), count]
        for reason, count in count_by(skipped_routes, "reason").most_common()
    ]


def build_edge_rows(edges, max_items):
    rows = []
    for edge in limited(edges, max_items):
        evidence = edge.get("evidence") or []
        first_evidence = evidence[0] if evidence else {}
        evidence_text = first_evidence.get("detail") or first_evidence.get("source") or ""
        rows.append(
            [
                code(edge.get("from", "")),
                code(edge.get("to", "")),
                code(edge.get("kind", "")),
                code(edge.get("confidence", "")),
                evidence_text,
            ]
        )
    return rows


def build_skipped_rows(skipped_routes, max_items):
    rows = []
    for route in limited(skipped_routes, max_items):
        rows.append(
            [
                code(route.get("from", "")),
                code(route.get("to", "")),
                code(route.get("reason", "")),
                route.get("detail", ""),
            ]
        )
    return rows


def build_calibration_rows(calibration_decisions, max_items):
    rows = []
    for decision in limited(calibration_decisions, max_items):
        rows.append(
            [
                code(decision.get("name", "")),
                code(decision.get("decision", "")),
                code(decision.get("confidence", "")),
                code(decision.get("address", "")),
                code(decision.get("raw_bytes", "")),
                decision.get("reason", ""),
            ]
        )
    return rows


def build_evidence_rows(evidence_entries, max_items):
    rows = []
    for evidence in limited(evidence_entries, max_items):
        rows.append(
            [
                code(evidence.get("symbol", "")),
                code(evidence.get("source", "")),
                code(evidence.get("entry", "")),
                evidence.get("detail", "")[:160],
            ]
        )
    return rows


def section_limit_note(items, max_items):
    if len(items) <= max_items:
        return ""
    return f"\n_Showing first {max_items} of {len(items)} rows._\n"


def human_limit_note(items, max_items):
    if len(items) <= max_items:
        return ""
    return f"\n_Table is summarized here; all {len(items)} rows are available in the CSV exports._\n"


def first_evidence(evidence_items):
    evidence = evidence_items[0] if evidence_items else {}
    return {
        "source": evidence.get("source", ""),
        "line": evidence.get("line", ""),
        "entry": evidence.get("entry", ""),
        "detail": evidence.get("detail", ""),
    }


def write_csv(path, fieldnames, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def export_trace_tables(input_paths, traces, export_dir):
    export_dir = Path(export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    node_rows = []
    followed_rows = []
    skipped_rows = []
    calibration_rows = []
    evidence_rows = []

    for input_path, trace in zip(input_paths, traces):
        trace_file = Path(input_path).name
        request = trace_request(trace)
        groups = request.get("groups") or []
        summary_rows.append(
            {
                "trace_file": trace_file,
                "signal": request.get("signal", ""),
                "max_depth": request.get("max_depth", ""),
                "groups": ", ".join(groups) if groups else "",
                "nodes": len(trace.get("nodes", [])),
                "followed_edges": len(trace.get("edges", [])),
                "skipped_routes": len(trace.get("skipped_routes", [])),
                "calibration_decisions": len(trace.get("calibration_decisions", [])),
                "evidence_entries": len(trace.get("evidence", [])),
                "open_questions": len(trace.get("open_questions", [])),
            }
        )
        for node in trace.get("nodes", []):
            node_rows.append(
                {
                    "trace_file": trace_file,
                    "id": node.get("id", ""),
                    "kind": node.get("kind", ""),
                    "level": node.get("level", ""),
                    "label": node.get("label", ""),
                }
            )
        for edge in trace.get("edges", []):
            evidence = first_evidence(edge.get("evidence") or [])
            followed_rows.append(
                {
                    "trace_file": trace_file,
                    "from": edge.get("from", ""),
                    "to": edge.get("to", ""),
                    "kind": edge.get("kind", ""),
                    "confidence": edge.get("confidence", ""),
                    "evidence_source": evidence["source"],
                    "evidence_line": evidence["line"],
                    "evidence_detail": evidence["detail"],
                }
            )
        for route in trace.get("skipped_routes", []):
            evidence = first_evidence(route.get("evidence") or [])
            skipped_rows.append(
                {
                    "trace_file": trace_file,
                    "from": route.get("from", ""),
                    "to": route.get("to", ""),
                    "reason": route.get("reason", ""),
                    "detail": route.get("detail", ""),
                    "evidence_source": evidence["source"],
                    "evidence_line": evidence["line"],
                    "evidence_detail": evidence["detail"],
                }
            )
        for decision in trace.get("calibration_decisions", []):
            evidence = first_evidence(decision.get("evidence") or [])
            calibration_rows.append(
                {
                    "trace_file": trace_file,
                    "name": decision.get("name", ""),
                    "decision": decision.get("decision", ""),
                    "confidence": decision.get("confidence", ""),
                    "address": decision.get("address", ""),
                    "raw_bytes": decision.get("raw_bytes", ""),
                    "raw_unsigned_big_endian": decision.get("raw_unsigned_big_endian", ""),
                    "raw_unsigned_little_endian": decision.get("raw_unsigned_little_endian", ""),
                    "hex_status": decision.get("hex_status", ""),
                    "reason": decision.get("reason", ""),
                    "evidence_source": evidence["source"],
                    "evidence_line": evidence["line"],
                    "evidence_detail": evidence["detail"],
                }
            )
        for evidence in trace.get("evidence", []):
            evidence_rows.append(
                {
                    "trace_file": trace_file,
                    "symbol": evidence.get("symbol", ""),
                    "source": evidence.get("source", ""),
                    "entry": evidence.get("entry", ""),
                    "kind": evidence.get("kind", ""),
                    "detail": evidence.get("detail", ""),
                }
            )

    exports = {
        "summary.csv": (
            ["trace_file", "signal", "max_depth", "groups", "nodes", "followed_edges", "skipped_routes", "calibration_decisions", "evidence_entries", "open_questions"],
            summary_rows,
        ),
        "nodes.csv": (["trace_file", "id", "kind", "level", "label"], node_rows),
        "followed_routes.csv": (
            ["trace_file", "from", "to", "kind", "confidence", "evidence_source", "evidence_line", "evidence_detail"],
            followed_rows,
        ),
        "skipped_routes.csv": (
            ["trace_file", "from", "to", "reason", "detail", "evidence_source", "evidence_line", "evidence_detail"],
            skipped_rows,
        ),
        "calibration_decisions.csv": (
            [
                "trace_file", "name", "decision", "confidence", "address", "raw_bytes",
                "raw_unsigned_big_endian", "raw_unsigned_little_endian", "hex_status",
                "reason", "evidence_source", "evidence_line", "evidence_detail",
            ],
            calibration_rows,
        ),
        "evidence.csv": (["trace_file", "symbol", "source", "entry", "kind", "detail"], evidence_rows),
    }
    manifest = []
    for filename, (fieldnames, rows) in exports.items():
        write_csv(export_dir / filename, fieldnames, rows)
        manifest.append({"filename": filename, "path": str(export_dir / filename), "rows": len(rows)})
    return manifest


def build_export_rows(export_manifest):
    return [[code(item["filename"]), item["rows"], code(item["path"])] for item in export_manifest or []]


def route_metrics(trace):
    request = trace_request(trace)
    signal = request.get("signal", "unknown")
    edges = trace.get("edges", [])
    skipped_routes = trace.get("skipped_routes", [])
    direct_edges = [edge for edge in edges if edge.get("to") == signal]
    second_level_edges = [edge for edge in edges if edge.get("to") != signal]
    skipped_counts = count_by(skipped_routes, "reason")
    return {
        "signal": signal,
        "direct_edges": len(direct_edges),
        "second_level_edges": len(second_level_edges),
        "followed_edges": len(edges),
        "skipped_routes": len(skipped_routes),
        "unresolved_calibration": skipped_counts.get("unresolved_calibration", 0),
        "disabled_calibration": skipped_counts.get("disabled_calibration", 0),
        "depth_limited": skipped_counts.get("depth_limited", 0),
        "filtered": skipped_counts.get("filtered", 0),
    }


def source_family(name):
    text = str(name or "")
    for separator in (".", "_"):
        if separator in text:
            return text.split(separator)[0]
    return text[:24] or "unknown"


def top_followed_families(edges, max_items):
    counts = Counter(source_family(edge.get("from", "")) for edge in edges)
    return [[code(name), count] for name, count in counts.most_common(max_items)]


def top_targets(edges, max_items):
    counts = Counter(edge.get("to", "unknown") for edge in edges)
    return [[code(name), count] for name, count in counts.most_common(max_items)]


def evidence_module(entry):
    parts = str(entry or "").replace("\\", "/").split("/")
    if len(parts) >= 2 and parts[0] == "documentation":
        return parts[1]
    return parts[0] if parts and parts[0] else "unknown"


def build_evidence_source_rows(evidence_entries, max_items):
    grouped = {}
    for evidence in evidence_entries:
        module = evidence_module(evidence.get("entry", ""))
        if module not in grouped:
            grouped[module] = {"count": 0, "symbols": set(), "sources": set()}
        grouped[module]["count"] += 1
        if evidence.get("symbol"):
            grouped[module]["symbols"].add(evidence["symbol"])
        if evidence.get("source"):
            grouped[module]["sources"].add(evidence["source"])
    rows = []
    for module, info in sorted(grouped.items(), key=lambda item: item[1]["count"], reverse=True)[:max_items]:
        sample_symbols = ", ".join(sorted(info["symbols"])[:3])
        sample_sources = ", ".join(sorted(Path(source).name for source in info["sources"])[:2])
        rows.append([code(module), info["count"], sample_symbols, sample_sources])
    return rows


def mermaid_label(text):
    return str(text).replace('"', "'").replace("\n", "<br/>")


def build_trace_overview_diagram(trace):
    metrics = route_metrics(trace)
    signal = mermaid_label(metrics["signal"])
    return "\n".join(
        [
            "flowchart LR",
            f'  target["Target<br/>{signal}"]',
            f'  direct["Direct followed inputs<br/>{metrics["direct_edges"]}"] --> target',
            f'  upstream["Second-level followed inputs<br/>{metrics["second_level_edges"]}"] --> direct',
            f'  cal["Calibration-gated routes not followed<br/>{metrics["unresolved_calibration"] + metrics["disabled_calibration"]}"] -. stopped .-> target',
            f'  depth["Depth-limited stops<br/>{metrics["depth_limited"]}"] -. max depth .-> upstream',
            f'  filtered["Filtered routes<br/>{metrics["filtered"]}"] -. filter .-> target',
        ]
    )


def build_route_decision_diagram(trace):
    metrics = route_metrics(trace)
    candidates = metrics["followed_edges"] + metrics["skipped_routes"]
    return "\n".join(
        [
            "flowchart TB",
            f'  candidates["Candidate routes seen<br/>{candidates}"]',
            f'  followed["Followed<br/>{metrics["followed_edges"]}"]',
            f'  skipped["Not followed<br/>{metrics["skipped_routes"]}"]',
            f'  unresolved["Unresolved calibration<br/>{metrics["unresolved_calibration"]}"]',
            f'  disabled["Disabled calibration<br/>{metrics["disabled_calibration"]}"]',
            f'  limited["Depth limited<br/>{metrics["depth_limited"]}"]',
            f'  filtered["Filtered<br/>{metrics["filtered"]}"]',
            "  candidates --> followed",
            "  candidates --> skipped",
            "  skipped --> unresolved",
            "  skipped --> disabled",
            "  skipped --> limited",
            "  skipped --> filtered",
        ]
    )


def human_takeaway(trace):
    request = trace_request(trace)
    groups = request.get("groups") or []
    metrics = route_metrics(trace)
    lines = [
        f"- The trace followed {code(metrics['followed_edges'])} evidence-backed route(s) within the requested depth.",
        f"- Direct inputs into target: {code(metrics['direct_edges'])}.",
        f"- Second-level followed inputs: {code(metrics['second_level_edges'])}.",
    ]
    if metrics["unresolved_calibration"]:
        lines.append(
            f"- Calibration-gated routes not followed: {code(metrics['unresolved_calibration'])}; raw values may be resolved, but enable/disable semantics were not proven."
        )
    if metrics["disabled_calibration"]:
        lines.append(f"- Disabled calibration routes not followed: {code(metrics['disabled_calibration'])}.")
    if metrics["depth_limited"]:
        lines.append(f"- Depth-limited routes: {code(metrics['depth_limited'])}; these are known candidates beyond the requested depth.")
    if metrics["filtered"]:
        lines.append(f"- Filtered routes: {code(metrics['filtered'])}; these were outside the requested group filter.")
    if groups:
        lines.append(f"- Group filter used: {code(', '.join(groups))}.")
    return "\n".join(lines)


def generated_agent_comments(input_paths, traces):
    comments = []
    for input_path, trace in zip(input_paths, traces):
        metrics = route_metrics(trace)
        request = trace_request(trace)
        groups = request.get("groups") or []
        label = Path(input_path).name
        if metrics["followed_edges"]:
            comments.append(
                f"{code(label)} has a usable evidence-backed trace inside depth {code(request.get('max_depth', ''))}: "
                f"{code(metrics['direct_edges'])} direct target input(s) and {code(metrics['second_level_edges'])} second-level input(s) were followed."
            )
        else:
            comments.append(
                f"{code(label)} did not follow any route. This usually means the requested filter or depth removed all candidate branches."
            )
        if metrics["unresolved_calibration"]:
            comments.append(
                f"Calibration-gated branches were intentionally not followed in {code(label)} because enable/disable semantics were not proven for "
                f"{code(metrics['unresolved_calibration'])} route(s). Treat these as review items, not disabled functionality."
            )
        if metrics["disabled_calibration"]:
            comments.append(
                f"{code(label)} contains {code(metrics['disabled_calibration'])} disabled calibration route(s); these should remain blocked unless calibration data changes."
            )
        if metrics["depth_limited"]:
            comments.append(
                f"Depth-limited candidates mean the graph is incomplete beyond the requested level for {code(label)}. Increase max depth to inspect those branches."
            )
        if metrics["filtered"]:
            group_text = ", ".join(groups) if groups else "the active filter"
            comments.append(
                f"{code(label)} applied {code(group_text)} filtering and skipped {code(metrics['filtered'])} route(s); this is expected when checking only a signal group."
            )
    if not comments:
        comments.append("No trace-specific concerns were detected in the provided JSON.")
    return comments


def trace_summary_row(input_path, trace):
    request = trace_request(trace)
    groups = request.get("groups") or []
    return [
        code(Path(input_path).name),
        code(request.get("signal", "unknown")),
        code(request.get("max_depth", "")),
        code(", ".join(groups) if groups else "none"),
        len(trace.get("nodes", [])),
        len(trace.get("edges", [])),
        len(trace.get("skipped_routes", [])),
        len(trace.get("calibration_decisions", [])),
    ]


def build_human_trace_section(input_path, trace, index, max_items):
    request = trace_request(trace)
    groups = request.get("groups") or []
    edges = trace.get("edges", [])
    skipped_routes = trace.get("skipped_routes", [])
    calibration_decisions = trace.get("calibration_decisions", [])
    evidence_entries = trace.get("evidence", [])
    open_questions = trace.get("open_questions", [])
    section_title = f"Report {index}: {Path(input_path).name}"
    return "\n".join(
        [
            f"## {section_title}",
            "",
            "### What This Means",
            "",
            human_takeaway(trace),
            "",
            "### Trace Overview Diagram",
            "",
            "```mermaid",
            build_trace_overview_diagram(trace),
            "```",
            "",
            "### Route Decision Diagram",
            "",
            "```mermaid",
            build_route_decision_diagram(trace),
            "```",
            "",
            "### Trace Parameters",
            "",
            f"- Signal: {code(request.get('signal', 'unknown'))}",
            f"- Max depth: {code(request.get('max_depth', ''))}",
            f"- Groups: {code(', '.join(groups) if groups else 'none')}",
            "",
            "### Skipped Route Reasons",
            "",
            table(["Reason", "Count"], build_reason_rows(skipped_routes)),
            "### Calibration Decision Summary",
            "",
            table(
                ["Decision", "Count"],
                [[code(decision), count] for decision, count in count_by(calibration_decisions, "decision").most_common()],
            ),
            "### Major Followed Source Families",
            "",
            table(["Source family", "Followed edge count"], top_followed_families(edges, max_items)),
            "### Most Connected Targets",
            "",
            table(["Target", "Incoming followed edges"], top_targets(edges, max_items)),
            "### Calibration Examples",
            "",
            table(
                ["Name", "Decision", "Raw Bytes", "Reason"],
                [
                    [
                        code(decision.get("name", "")),
                        code(decision.get("decision", "")),
                        code(decision.get("raw_bytes", "")),
                        decision.get("reason", ""),
                    ]
                    for decision in limited(calibration_decisions, max_items)
                ],
            ),
            human_limit_note(calibration_decisions, max_items),
            "### Evidence Source Summary",
            "",
            table(["Module", "Evidence count", "Sample symbols", "Source files"], build_evidence_source_rows(evidence_entries, max_items)),
            human_limit_note(evidence_entries, max_items),
            "### Open Questions",
            "",
            "\n".join(f"- {question}" for question in limited(open_questions, max_items)) if open_questions else "_None listed._",
            human_limit_note(open_questions, max_items),
            "### Raw Graph Note",
            "",
            "- Full raw Mermaid graph omitted from this human report because it is too dense to interpret directly.",
            "- Use the JSON file if a machine-readable full edge list is needed.",
            "",
        ]
    )


def build_human_combined_markdown_report(input_paths, traces, title=None, max_items=20, agent_comments=None, export_manifest=None):
    title = title or "Human Signal Trace Report"
    comments = generated_agent_comments(input_paths, traces)
    comments.extend(agent_comments or [])
    lines = [
        f"# {title}",
        "",
        "## Plain-English Conclusion",
        "",
    ]
    for input_path, trace in zip(input_paths, traces):
        metrics = route_metrics(trace)
        groups = trace_request(trace).get("groups") or []
        group_text = ", ".join(groups) if groups else "no group filter"
        lines.append(
            f"- {code(Path(input_path).name)} traced {code(metrics['signal'])} with {group_text}: "
            f"{metrics['followed_edges']} followed, {metrics['skipped_routes']} not followed."
        )
    lines.extend(
        [
            "",
            "## Combined Summary",
            "",
            table(
                ["File", "Signal", "Depth", "Groups", "Nodes", "Edges", "Skipped", "Calibrations"],
                [trace_summary_row(input_path, trace) for input_path, trace in zip(input_paths, traces)],
            ),
            "## How To Read This",
            "",
            "- Followed routes are evidence-backed paths expanded by the trace.",
            "- Skipped routes were intentionally not expanded because they were filtered, depth-limited, disabled, or unresolved.",
            "- Calibration-gated routes marked unresolved are not followed, even when raw HEX bytes are available.",
            "- Diagrams below are intentionally small summaries; the full raw graph is omitted from the human report.",
            "",
            "## Agent Comments",
            "",
            *[f"- {comment}" for comment in comments],
            "",
            "## Full Data Exports",
            "",
            table(["CSV file", "Rows", "Path"], build_export_rows(export_manifest)),
            "Open these CSV files in Excel for the complete row-level trace data. The Markdown report only explains and summarizes them.",
            "",
        ]
    )
    for index, (input_path, trace) in enumerate(zip(input_paths, traces), start=1):
        lines.append(build_human_trace_section(input_path, trace, index, max_items))
    return "\n".join(str(line) for line in lines) + "\n"


def load_trace(input_path):
    return json.loads(Path(input_path).read_text(encoding="utf-8-sig"))


def write_human_combined_report(input_paths, output_path, title=None, max_items=20, agent_comments=None, export_dir=None):
    traces = [load_trace(input_path) for input_path in input_paths]
    export_dir = Path(export_dir) if export_dir else Path(output_path).with_name(f"{Path(output_path).stem}_tables")
    export_manifest = export_trace_tables(input_paths, traces, export_dir)
    markdown = build_human_combined_markdown_report(
        input_paths,
        traces,
        title=title,
        max_items=max_items,
        agent_comments=agent_comments,
        export_manifest=export_manifest,
    )
    Path(output_path).write_text(markdown, encoding="utf-8")
    return markdown


def default_output_path(input_path):
    input_path = Path(input_path)
    return input_path.with_name(f"{input_path.stem}_report.md")


def parse_args():
    parser = argparse.ArgumentParser(description="Convert signal-backtrace JSON into a human-readable Markdown report.")
    parser.add_argument("--input", action="append", required=True, help="Path to signal-backtrace JSON; repeat for multiple")
    parser.add_argument("--output", help="Path to Markdown report")
    parser.add_argument("--title", help="Report title")
    parser.add_argument("--max-items", type=int, default=25, help="Maximum rows per detailed table")
    parser.add_argument("--agent-comment", action="append", default=[], help="Additional agent-authored comment to include")
    parser.add_argument("--export-dir", help="Directory for full CSV exports")
    return parser.parse_args()


def main():
    args = parse_args()
    output_path = args.output or default_output_path(args.input[0])
    write_human_combined_report(
        args.input,
        output_path,
        title=args.title,
        max_items=args.max_items,
        agent_comments=args.agent_comment,
        export_dir=args.export_dir,
    )
    print(output_path)


if __name__ == "__main__":
    main()

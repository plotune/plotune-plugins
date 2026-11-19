#!/usr/bin/env python3
"""Metered, stateless calls to AI command-line runtimes, with an append-only ledger.

The agent that asks for a call does not write the numbers: this wrapper does. Each call
is a fresh process that sees only the prompt file it is given. Before a call it checks
the user's budget; over budget, it refuses without running anything and says so. Usage
the runtime does not report is recorded as unknown, never estimated.

Config (JSON, owned by the user):
  ledger        path of the JSONL ledger, relative to the config file (default ai-pool-ledger.jsonl)
  budget        optional {"calls": n, "tokens": n, "cost": n}
  role_budget   optional {"<role>": {"calls": n, "tokens": n, "cost": n}}
  entries       list of {id, command[], runtime, model, effort, context_limit, usage{}}
Command arguments may contain {prompt_file}, {model} and {effort}. usage maps tokens_in,
tokens_out and cost to dotted paths in the JSON the runtime prints.

Calls the wrapper did not run, such as a host's own subagents, are covered too: `check`
asks whether a role is within budget, and `record` adds a row labelled self_reported.
Rows carry `source` (wrapper, self_reported, or a host hook), so measured and reported
numbers stay apart in the summary.

Usage:
    python scripts/pool.py run --config C --entry E --role R --task T --prompt-file P
    python scripts/pool.py check --config C --role R
    python scripts/pool.py record --config C --role R --task T [--model M --tokens-in N ...]
    python scripts/pool.py summary --config C
Exit codes for run and check: 0 ok, 1 the call failed, 2 bad input, 3 over budget.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LIMIT_KEYS = ("calls", "tokens", "cost")
USAGE_KEYS = ("tokens_in", "tokens_out", "cost")


def _check_limits(value, where):
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object")
    for key, limit in value.items():
        if key not in LIMIT_KEYS:
            raise ValueError(f"{where}: unknown limit {key}")
        if isinstance(limit, bool) or not isinstance(limit, (int, float)) or limit < 0:
            raise ValueError(f"{where}.{key} must be a non-negative number")
    return value


def load_config(path):
    path = Path(path)
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read config: {exc}")
    if not isinstance(cfg, dict):
        raise ValueError("config must be an object")
    entries = cfg.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("entries must be a non-empty list")
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not entry["id"].strip():
            raise ValueError("every entry needs an id")
        if entry["id"] in seen:
            raise ValueError("duplicate entry id " + entry["id"])
        seen.add(entry["id"])
        command = entry.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
            raise ValueError(f"entry {entry['id']}: command must be a non-empty list of strings")
        usage = entry.get("usage", {})
        if not isinstance(usage, dict) or not set(usage) <= set(USAGE_KEYS):
            raise ValueError(f"entry {entry['id']}: usage keys must be among {USAGE_KEYS}")
    _check_limits(cfg.get("budget"), "budget")
    for role, limits in (cfg.get("role_budget") or {}).items():
        _check_limits(limits, f"role_budget.{role}")
    cfg["_dir"] = str(path.parent)
    return cfg


def _ledger_path(cfg):
    return Path(cfg["_dir"]) / cfg.get("ledger", "ai-pool-ledger.jsonl")


def _read_ledger(cfg):
    path = _ledger_path(cfg)
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _append(cfg, row):
    path = _ledger_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()


def _used(rows):
    """Totals over the calls that actually ran; refused calls cost nothing."""
    ran = [r for r in rows if r.get("status") in ("ok", "failed")]
    tokens = sum((r.get("tokens_in") or 0) + (r.get("tokens_out") or 0) for r in ran)
    cost = sum(r.get("cost") or 0 for r in ran)
    return {"calls": len(ran), "tokens": tokens, "cost": cost}


def _exceeded(limits, used):
    for key in LIMIT_KEYS:
        if key in limits and used[key] >= limits[key]:
            return f"{key} budget reached ({used[key]} of {limits[key]})"
    return None


def _dig(data, dotted):
    for part in dotted.split("."):
        if not isinstance(data, dict) or part not in data:
            return None
        data = data[part]
    return data if isinstance(data, (int, float)) and not isinstance(data, bool) else None


def _parse_json(text):
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


def _usage(entry, stdout):
    mapping = entry.get("usage") or {}
    data = _parse_json(stdout) if mapping else None
    found = {key: (_dig(data, mapping[key]) if data is not None and key in mapping else None) for key in USAGE_KEYS}
    return found, ("reported" if any(v is not None for v in found.values()) else "unknown")


def _budget_reason(cfg, rows, role):
    reason = _exceeded(cfg.get("budget") or {}, _used(rows))
    if reason is None:
        role_limits = (cfg.get("role_budget") or {}).get(role) or {}
        reason = _exceeded(role_limits, _used([r for r in rows if r.get("role") == role]))
        if reason:
            reason = f"role {role}: " + reason
    return reason


def check_budget(cfg, role):
    """Ask whether a call by this role would be within budget. Writes nothing."""
    reason = _budget_reason(cfg, _read_ledger(cfg), role)
    return {"status": "no_budget", "reason": reason} if reason else {"status": "ok"}


def record_call(cfg, role, task, model=None, effort=None, runtime=None, tokens_in=None,
                tokens_out=None, cost=None, source="self_reported", status="ok"):
    """Add a row for an AI call this wrapper did not run, such as a host's own subagent.

    The row says where its numbers came from. Whoever calls this reports; nothing here
    can verify the numbers, so the ledger labels them rather than trusting them."""
    numbers = (tokens_in, tokens_out, cost)
    row = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "role": role, "task": task, "entry": "host-subagent",
        "runtime": runtime, "model": model, "effort": effort,
        "status": status, "exit_code": None, "duration_s": 0,
        "tokens_in": tokens_in, "tokens_out": tokens_out, "cost": cost,
        "usage_source": source if any(v is not None for v in numbers) else "unknown",
        "source": source,
    }
    _append(cfg, row)
    return {"status": status}


def run_call(cfg, entry_id, role, task, prompt_file):
    entry = next((e for e in cfg["entries"] if e["id"] == entry_id), None)
    if entry is None:
        raise ValueError("unknown entry " + entry_id)
    prompt_file = Path(prompt_file)
    try:
        prompt_bytes = prompt_file.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read prompt file: {exc}")
    rows = _read_ledger(cfg)
    base = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "role": role, "task": task, "entry": entry_id,
        "runtime": entry.get("runtime"), "model": entry.get("model"), "effort": entry.get("effort"),
        "prompt_sha256": hashlib.sha256(prompt_bytes).hexdigest(),
        "source": "wrapper",
    }
    reason = _budget_reason(cfg, rows, role)
    if reason:
        _append(cfg, dict(base, status="refused", reason=reason, exit_code=None, duration_s=0,
                          tokens_in=None, tokens_out=None, cost=None, usage_source="unknown"))
        return {"status": "no_budget", "reason": reason}
    values = {"prompt_file": str(prompt_file), "model": str(entry.get("model", "")), "effort": str(entry.get("effort", ""))}
    argv = [part.format(**values) for part in entry["command"]]
    started = time.monotonic()
    try:
        done = subprocess.run(argv, capture_output=True, text=True, shell=False)
        exit_code, stdout, stderr = done.returncode, done.stdout, done.stderr
    except OSError as exc:
        exit_code, stdout, stderr = 127, "", str(exc)
    duration = round(time.monotonic() - started, 3)
    found, source = _usage(entry, stdout)
    status = "ok" if exit_code == 0 else "failed"
    _append(cfg, dict(base, status=status, exit_code=exit_code, duration_s=duration,
                      usage_source=source, **found))
    return {"status": status, "exit_code": exit_code, "stdout": stdout, "stderr": stderr}


def summarize(cfg):
    rows = _read_ledger(cfg)

    def bucket(selected):
        ran = [r for r in selected if r.get("status") in ("ok", "failed")]
        return {
            "calls": len(ran),
            "failed": sum(1 for r in ran if r["status"] == "failed"),
            "refused": sum(1 for r in selected if r.get("status") == "refused"),
            "tokens_in": sum(r.get("tokens_in") or 0 for r in ran),
            "tokens_out": sum(r.get("tokens_out") or 0 for r in ran),
            "cost": sum(r.get("cost") or 0 for r in ran),
            "calls_with_unknown_usage": sum(1 for r in ran if r.get("usage_source") != "reported"),
            "seconds": round(sum(r.get("duration_s") or 0 for r in ran), 3),
        }

    out = {"total": bucket(rows), "by_entry": {}, "by_role": {}, "by_source": {}, "budget": {}}
    for key in sorted({r.get("source") for r in rows if r.get("source")}):
        out["by_source"][key] = bucket([r for r in rows if r.get("source") == key])
    for key in sorted({r.get("entry") for r in rows if r.get("entry")}):
        out["by_entry"][key] = bucket([r for r in rows if r.get("entry") == key])
    for key in sorted({r.get("role") for r in rows if r.get("role")}):
        out["by_role"][key] = bucket([r for r in rows if r.get("role") == key])
    used = _used(rows)
    for key, limit in (cfg.get("budget") or {}).items():
        out["budget"][key] = {"limit": limit, "used": used[key]}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--config", required=True)
    run.add_argument("--entry", required=True)
    run.add_argument("--role", required=True)
    run.add_argument("--task", required=True)
    run.add_argument("--prompt-file", required=True)
    summary = sub.add_parser("summary")
    summary.add_argument("--config", required=True)
    check = sub.add_parser("check", help="ask whether a call by this role is within budget; exit 3 if not")
    check.add_argument("--config", required=True)
    check.add_argument("--role", required=True)
    record = sub.add_parser("record", help="record a call this wrapper did not run (self-reported)")
    record.add_argument("--config", required=True)
    record.add_argument("--role", required=True)
    record.add_argument("--task", required=True)
    record.add_argument("--model")
    record.add_argument("--effort")
    record.add_argument("--runtime")
    record.add_argument("--tokens-in", type=int)
    record.add_argument("--tokens-out", type=int)
    record.add_argument("--cost", type=float)
    args = parser.parse_args(argv)
    try:
        cfg = load_config(args.config)
        if args.command == "summary":
            print(json.dumps(summarize(cfg), indent=2))
            return 0
        if args.command == "check":
            result = check_budget(cfg, args.role)
            print(json.dumps(result))
            return 0 if result["status"] == "ok" else 3
        if args.command == "record":
            print(json.dumps(record_call(cfg, args.role, args.task, args.model, args.effort, args.runtime,
                                         args.tokens_in, args.tokens_out, args.cost)))
            return 0
        result = run_call(cfg, args.entry, args.role, args.task, args.prompt_file)
    except ValueError as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    print(json.dumps(result))
    return {"ok": 0, "failed": 1, "no_budget": 3}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())

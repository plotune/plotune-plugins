#!/usr/bin/env python3
"""Claude Code hook: meters the host's own Agent (subagent) calls into the AI pool ledger.

Wired by hooks/hooks.json as PreToolUse and PostToolUse on the Agent tool.
  pre   checks the pool; over budget and rejecting, it denies the call with a reason.
  post  records the call with what Claude Code reports (model, final-request usage, duration).

Inert unless a pool config exists: env PLOTUNE_POOL_CONFIG, else ai-pool.json in the working
directory. It never breaks a session: any error exits 0 silently. Only an explicit deny blocks.
Tokens come from the host's `usage`, which covers the final request only, so the row says
reported_final_request_only; a background launch reports no usage and is recorded as unknown.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pool  # noqa: E402

ROLE = "unattributed"


def _config():
    path = os.environ.get("PLOTUNE_POOL_CONFIG") or "ai-pool.json"
    return pool.load_config(path) if Path(path).is_file() else None


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def handle(phase, event, cfg):
    if phase == "pre":
        result = pool.check_budget(cfg, ROLE)
        if result["status"] == "no_budget":
            return {"hookSpecificOutput": {
                "hookEventName": "PreToolUse", "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "AI pool: " + result["reason"] + ". Do this work yourself, or ask the Orchestrator "
                    "to wait or to extend the pool budget.")}}
        return None
    response = event.get("tool_response")
    response = response if isinstance(response, dict) else {}
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
    tokens_in, tokens_out = _number(usage.get("input_tokens")), _number(usage.get("output_tokens"))
    duration_ms = _number(response.get("totalDurationMs"))
    tool_input = event.get("tool_input") if isinstance(event.get("tool_input"), dict) else {}
    extra = {k: v for k, v in (("agent_id", response.get("agentId")),
                               ("tool_use_count", response.get("totalToolUseCount"))) if v is not None}
    pool.record_call(
        cfg, ROLE, str(tool_input.get("description") or "subagent"),
        model=response.get("resolvedModel"), runtime="claude-code",
        tokens_in=tokens_in, tokens_out=tokens_out, source="claude-code-hook",
        usage_source="reported_final_request_only", duration_s=round(duration_ms / 1000, 3) if duration_ms else 0,
        extra=extra)
    return None


def main(argv):
    try:
        phase = argv[1] if len(argv) > 1 else ""
        cfg = _config()
        if cfg is None or phase not in ("pre", "post"):
            return 0
        event = json.loads(sys.stdin.read() or "null")
        if not isinstance(event, dict):
            return 0
        output = handle(phase, event, cfg)
        if output:
            print(json.dumps(output))
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

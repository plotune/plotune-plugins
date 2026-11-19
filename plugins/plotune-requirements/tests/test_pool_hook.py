"""Claude Code hook for the AI pool: meters the host's own Agent calls into the same ledger.

The hook stays inert unless the user has a pool config. Events below follow the shape
Claude Code documents for the Agent tool; the hook records what the host reports as is.
Run: python -m unittest discover -s tests -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "scripts" / "pool_hook.py"


class PoolHookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)

    def config(self, **extra):
        cfg = {"ledger": "ledger.jsonl", "entries": [{"id": "x", "command": ["true"]}]}
        cfg.update(extra)
        path = self.home / "ai-pool.json"
        path.write_text(json.dumps(cfg))
        return path

    def ledger(self):
        path = self.home / "ledger.jsonl"
        return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []

    def run_hook(self, phase, event, cfg=True, stdin=None):
        env = {k: v for k, v in os.environ.items() if k != "PLOTUNE_POOL_CONFIG"}
        if cfg:
            env["PLOTUNE_POOL_CONFIG"] = str(self.home / "ai-pool.json")
        return subprocess.run([sys.executable, str(HOOK), phase], input=stdin if stdin is not None else json.dumps(event),
                              capture_output=True, text=True, env=env, cwd=self.home)

    def pre_event(self):
        return {"hook_event_name": "PreToolUse", "tool_name": "Agent",
                "tool_input": {"prompt": "do a thing", "description": "scan files", "subagent_type": "Explore", "model": "sonnet"}}

    def post_event(self, response):
        event = self.pre_event()
        event.update({"hook_event_name": "PostToolUse", "tool_response": response})
        return event

    FOREGROUND = {"status": "completed", "agentId": "a1", "resolvedModel": "model-a", "totalTokens": 25,
                  "totalDurationMs": 2500, "totalToolUseCount": 3,
                  "usage": {"input_tokens": 20, "output_tokens": 5}}

    def test_inert_without_a_pool_config(self):
        for phase, event in (("pre", self.pre_event()), ("post", self.post_event(self.FOREGROUND))):
            done = self.run_hook(phase, event, cfg=False)
            self.assertEqual((done.returncode, done.stdout.strip()), (0, ""))
        self.assertEqual(self.ledger(), [])

    def test_pre_allows_within_budget(self):
        self.config(budget={"calls": 5})
        done = self.run_hook("pre", self.pre_event())
        self.assertEqual((done.returncode, done.stdout.strip()), (0, ""))

    def test_pre_denies_over_budget_when_rejecting(self):
        self.config(budget={"calls": 0})
        done = self.run_hook("pre", self.pre_event())
        self.assertEqual(done.returncode, 0)
        out = json.loads(done.stdout)["hookSpecificOutput"]
        self.assertEqual((out["hookEventName"], out["permissionDecision"]), ("PreToolUse", "deny"))
        self.assertIn("pool", out["permissionDecisionReason"].lower())

    def test_pre_allows_over_budget_when_warning(self):
        self.config(budget={"calls": 0}, over_budget="warn")
        done = self.run_hook("pre", self.pre_event())
        self.assertEqual((done.returncode, done.stdout.strip()), (0, ""))

    def test_post_records_what_the_host_reports(self):
        self.config()
        self.assertEqual(self.run_hook("post", self.post_event(self.FOREGROUND)).returncode, 0)
        (row,) = self.ledger()
        self.assertEqual((row["source"], row["runtime"], row["model"]), ("claude-code-hook", "claude-code", "model-a"))
        self.assertEqual((row["tokens_in"], row["tokens_out"]), (20, 5))
        self.assertEqual(row["usage_source"], "reported_final_request_only")
        self.assertEqual((row["agent_id"], row["tool_use_count"], row["duration_s"]), ("a1", 3, 2.5))
        self.assertEqual(row["task"], "scan files")

    def test_background_launch_has_no_usage(self):
        self.config()
        self.run_hook("post", self.post_event({"status": "async_launched", "agentId": "a2", "resolvedModel": "model-b"}))
        (row,) = self.ledger()
        self.assertIsNone(row["tokens_in"])
        self.assertEqual(row["usage_source"], "unknown")
        self.assertEqual(row["model"], "model-b")

    def test_post_flags_use_beyond_budget_when_warning(self):
        self.config(budget={"calls": 0}, over_budget="warn")
        self.run_hook("post", self.post_event(self.FOREGROUND))
        (row,) = self.ledger()
        self.assertIn("calls", row["over_budget"])

    def test_hook_never_breaks_the_session(self):
        self.config()
        for phase in ("pre", "post"):
            for junk in ("", "not json", "[]", json.dumps({"tool_response": "text"})):
                done = self.run_hook(phase, None, stdin=junk)
                self.assertEqual(done.returncode, 0, (phase, junk, done.stderr))
                self.assertNotIn("deny", done.stdout)


if __name__ == "__main__":
    unittest.main()

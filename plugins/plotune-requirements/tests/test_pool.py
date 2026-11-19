"""AI pool wrapper: metered, stateless CLI calls with an append-only ledger.

The fake CLI below stands in for any real command-line AI runtime.
Run: python -m unittest discover -s tests -v
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import pool

FAKE_CLI = r"""
import json, sys
from pathlib import Path
prompt_file, mode, marker = sys.argv[1], sys.argv[2], sys.argv[3]
Path(marker).open("a").write("run\n")
text = Path(prompt_file).read_text()
if mode == "json":
    print(json.dumps({"result": "echo:" + text[:5], "usage": {"in": 10, "out": 5}, "cost": 0.5}))
elif mode == "partial":
    print("some log line")
    print(json.dumps({"usage": {"in": 7}}))
elif mode == "plain":
    print("no usage reported here")
elif mode == "fail":
    print("boom", file=sys.stderr)
    sys.exit(7)
"""


class PoolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        (self.home / "cli.py").write_text(FAKE_CLI)
        self.marker = self.home / "runs.txt"
        self.prompt = self.home / "prompt.txt"
        self.prompt.write_text("hello world, this text must not reach the ledger")

    def config(self, mode="json", **extra):
        cfg = {
            "ledger": "ledger.jsonl",
            "entries": [{
                "id": "fast",
                "runtime": "fake-cli",
                "model": "model-a",
                "effort": "low",
                "context_limit": 1000,
                "command": [sys.executable, str(self.home / "cli.py"), "{prompt_file}", mode, str(self.marker)],
                "usage": {"tokens_in": "usage.in", "tokens_out": "usage.out", "cost": "cost"},
            }],
        }
        cfg.update(extra)
        path = self.home / "ai-pool.json"
        path.write_text(json.dumps(cfg))
        return path

    def ledger(self):
        path = self.home / "ledger.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    def runs(self):
        return len(self.marker.read_text().splitlines()) if self.marker.exists() else 0

    def call(self, cfg, role="designer", task="T1", entry="fast"):
        return pool.run_call(pool.load_config(cfg), entry, role, task, self.prompt)

    def test_run_records_reported_usage(self):
        result = self.call(self.config())
        self.assertEqual(result["status"], "ok")
        self.assertIn("echo:hello", result["stdout"])
        (line,) = self.ledger()
        self.assertEqual((line["tokens_in"], line["tokens_out"], line["cost"]), (10, 5, 0.5))
        self.assertEqual(line["usage_source"], "reported")
        self.assertEqual((line["role"], line["task"], line["entry"]), ("designer", "T1", "fast"))
        self.assertEqual((line["runtime"], line["model"], line["effort"]), ("fake-cli", "model-a", "low"))
        self.assertEqual(line["status"], "ok")
        self.assertIn("prompt_sha256", line)
        self.assertNotIn("must not reach the ledger", json.dumps(line))

    def test_unknown_usage_is_labelled_not_invented(self):
        self.call(self.config("plain"))
        (line,) = self.ledger()
        self.assertIsNone(line["tokens_in"])
        self.assertIsNone(line["cost"])
        self.assertEqual(line["usage_source"], "unknown")

    def test_partial_usage_keeps_what_was_reported(self):
        self.call(self.config("partial"))
        (line,) = self.ledger()
        self.assertEqual(line["tokens_in"], 7)
        self.assertIsNone(line["tokens_out"])
        self.assertIsNone(line["cost"])

    def test_failed_call_is_recorded(self):
        result = self.call(self.config("fail"))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["exit_code"], 7)
        (line,) = self.ledger()
        self.assertEqual((line["status"], line["exit_code"]), ("failed", 7))

    def test_call_budget_refuses_without_running_the_cli(self):
        cfg = self.config(budget={"calls": 1})
        self.assertEqual(self.call(cfg)["status"], "ok")
        second = self.call(cfg)
        self.assertEqual(second["status"], "no_budget")
        self.assertEqual(self.runs(), 1)
        lines = self.ledger()
        self.assertEqual([x["status"] for x in lines], ["ok", "refused"])
        self.assertIn("calls", lines[1]["reason"])

    def test_token_budget_counts_reported_tokens(self):
        cfg = self.config(budget={"tokens": 15})
        self.assertEqual(self.call(cfg)["status"], "ok")
        self.assertEqual(self.call(cfg)["status"], "no_budget")

    def test_cost_budget(self):
        cfg = self.config(budget={"cost": 0.5})
        self.assertEqual(self.call(cfg)["status"], "ok")
        self.assertEqual(self.call(cfg)["status"], "no_budget")

    def test_role_budget_is_per_role(self):
        cfg = self.config(role_budget={"designer": {"calls": 1}})
        self.assertEqual(self.call(cfg, role="designer")["status"], "ok")
        self.assertEqual(self.call(cfg, role="designer")["status"], "no_budget")
        self.assertEqual(self.call(cfg, role="verify")["status"], "ok")

    def test_prompt_path_is_never_interpreted_by_a_shell(self):
        odd = self.home / "a; touch pwned b.txt"
        odd.write_text("odd name")
        result = pool.run_call(pool.load_config(self.config()), "fast", "build", "T2", odd)
        self.assertEqual(result["status"], "ok")
        self.assertFalse((self.home / "pwned").exists())

    def test_config_validation(self):
        bad = [
            {"entries": []},
            {"entries": [{"id": "a", "command": []}]},
            {"entries": [{"id": "a", "command": ["x"]}, {"id": "a", "command": ["y"]}]},
            {"entries": [{"command": ["x"]}]},
            {"entries": [{"id": "a", "command": ["x"]}], "budget": {"calls": -1}},
        ]
        for i, cfg in enumerate(bad):
            path = self.home / f"bad{i}.json"
            path.write_text(json.dumps(cfg))
            with self.assertRaises(ValueError, msg=str(cfg)):
                pool.load_config(path)

    def test_unknown_entry_is_an_error(self):
        with self.assertRaises(ValueError):
            self.call(self.config(), entry="missing")

    def test_summary_aggregates_by_entry_and_role(self):
        cfg = self.config(budget={"calls": 10})
        self.call(cfg, role="designer")
        self.call(cfg, role="verify")
        self.call(self.config("plain", budget={"calls": 10}), role="verify")
        summary = pool.summarize(pool.load_config(cfg))
        self.assertEqual(summary["total"]["calls"], 3)
        self.assertEqual(summary["by_role"]["verify"]["calls"], 2)
        self.assertEqual(summary["by_entry"]["fast"]["calls"], 3)
        self.assertEqual(summary["total"]["tokens_in"], 20)
        self.assertEqual(summary["total"]["calls_with_unknown_usage"], 1)
        self.assertEqual(summary["budget"]["calls"], {"limit": 10, "used": 3})

    def test_cli_exit_codes(self):
        cfg = self.config(budget={"calls": 1})
        base = [sys.executable, str(ROOT / "scripts" / "pool.py"), "run", "--config", str(cfg),
                "--entry", "fast", "--role", "build", "--task", "T3", "--prompt-file", str(self.prompt)]
        first = subprocess.run(base, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(first.stdout)["status"], "ok")
        second = subprocess.run(base, capture_output=True, text=True)
        self.assertEqual(second.returncode, 3)
        self.assertEqual(json.loads(second.stdout)["status"], "no_budget")
        summary = subprocess.run([sys.executable, str(ROOT / "scripts" / "pool.py"), "summary", "--config", str(cfg)],
                                 capture_output=True, text=True)
        self.assertEqual(summary.returncode, 0)
        self.assertEqual(json.loads(summary.stdout)["total"]["calls"], 1)

    def test_wrapper_rows_are_marked_as_measured(self):
        self.call(self.config())
        (line,) = self.ledger()
        self.assertEqual(line["source"], "wrapper")

    def test_record_adds_a_self_reported_row(self):
        cfg = pool.load_config(self.config())
        pool.record_call(cfg, "build", "T4", model="model-b", effort="high", tokens_in=100, tokens_out=40)
        (line,) = self.ledger()
        self.assertEqual((line["source"], line["usage_source"], line["status"]), ("self_reported", "self_reported", "ok"))
        self.assertEqual((line["role"], line["model"], line["tokens_in"], line["tokens_out"]), ("build", "model-b", 100, 40))
        self.assertIsNone(line["cost"])

    def test_record_without_numbers_is_unknown(self):
        pool.record_call(pool.load_config(self.config()), "build", "T4")
        (line,) = self.ledger()
        self.assertEqual(line["usage_source"], "unknown")

    def test_recorded_calls_count_toward_the_budget(self):
        cfg = self.config(budget={"calls": 1})
        pool.record_call(pool.load_config(cfg), "build", "T4")
        self.assertEqual(self.call(cfg)["status"], "no_budget")

    def test_check_reports_budget_and_writes_nothing(self):
        cfg = self.config(budget={"calls": 1})
        loaded = pool.load_config(cfg)
        self.assertEqual(pool.check_budget(loaded, "verify")["status"], "ok")
        pool.record_call(loaded, "verify", "T5")
        self.assertEqual(pool.check_budget(loaded, "verify")["status"], "no_budget")
        self.assertEqual(len(self.ledger()), 1)

    def test_summary_keeps_measured_and_self_reported_apart(self):
        cfg = self.config()
        self.call(cfg)
        pool.record_call(pool.load_config(cfg), "build", "T6", tokens_in=1, tokens_out=1)
        summary = pool.summarize(pool.load_config(cfg))
        self.assertEqual(summary["by_source"]["wrapper"]["calls"], 1)
        self.assertEqual(summary["by_source"]["self_reported"]["calls"], 1)
        self.assertEqual(summary["total"]["calls"], 2)

    def test_cli_record_and_check(self):
        cfg = self.config(budget={"calls": 1})
        script = [sys.executable, str(ROOT / "scripts" / "pool.py")]
        ok = subprocess.run(script + ["check", "--config", str(cfg), "--role", "build"], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0)
        rec = subprocess.run(script + ["record", "--config", str(cfg), "--role", "build", "--task", "T7",
                                       "--model", "model-c", "--tokens-in", "5", "--tokens-out", "2"],
                             capture_output=True, text=True)
        self.assertEqual(rec.returncode, 0, rec.stderr)
        full = subprocess.run(script + ["check", "--config", str(cfg), "--role", "build"], capture_output=True, text=True)
        self.assertEqual(full.returncode, 3)
        self.assertEqual(json.loads(full.stdout)["status"], "no_budget")


if __name__ == "__main__":
    unittest.main()

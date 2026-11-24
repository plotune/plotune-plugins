import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import check_gateway_tools as cgt  # noqa: E402

DATA = {
    "generatedFrom": {"commit": "abc"},
    "tools": ["nexus_exec", "nexus_get_session", "nexus_list_jobs", "nexus_start_session", "plotune_projects_list",
              "events_query", "requirements_get"],
    "renamed": {"exec": "nexus_exec", "list_jobs_tool": "nexus_list_jobs", "get_session": "nexus_get_session"},
    "excluded": {"principal_context": "Describes the per-project token.", "run_command": "Internal."},
}


def make_tree(root: Path, skill_text: str = "", data=None) -> Path:
    ref = root / "plugins/plotune/references/gateway-tools.json"
    ref.parent.mkdir(parents=True)
    ref.write_text(json.dumps(DATA if data is None else data), encoding="utf-8")
    skill = root / "plugins/plotune/skills/demo/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(skill_text, encoding="utf-8")
    return root


class CheckGatewayToolsTest(unittest.TestCase):
    def check(self, text: str, data=None) -> list:
        with tempfile.TemporaryDirectory() as tmp:
            return cgt.check(make_tree(Path(tmp), text, data))

    def test_gateway_names_pass(self):
        self.assertEqual(self.check("Call `plotune_projects_list` first, then nexus_start_session and `events_query`.\n"), [])

    def test_old_renamed_name_names_the_gateway_name(self):
        errors = self.check("Poll with `list_jobs_tool` until done.\n")
        self.assertEqual(len(errors), 1)
        self.assertIn("list_jobs_tool", errors[0])
        self.assertIn("nexus_list_jobs", errors[0])
        self.assertIn("SKILL.md:1", errors[0])

    def test_old_name_is_an_error_even_in_plain_prose(self):
        self.assertEqual(len(self.check("Use list_jobs_tool to poll.\n")), 1)

    def test_single_word_old_name_only_in_backticks(self):
        self.assertEqual(self.check("You can exec the plan later.\n"), [])
        errors = self.check("Run it with `exec` on the Edge.\n")
        self.assertEqual(len(errors), 1)
        self.assertIn("nexus_exec", errors[0])

    def test_excluded_tool_is_an_error(self):
        errors = self.check("Call `principal_context` to see who you are.\n")
        self.assertEqual(len(errors), 1)
        self.assertIn("principal_context", errors[0])
        self.assertIn("not offered", errors[0])

    def test_unknown_nexus_prefixed_name_is_an_error(self):
        errors = self.check("Then nexus_reboot_edge.\n")
        self.assertEqual(len(errors), 1)
        self.assertIn("nexus_reboot_edge", errors[0])

    def test_unknown_name_in_a_call_like_context_is_an_error(self):
        for text in ("Call `made_up_tool` now.\n", "Use `made_up_tool(session_id)`.\n", "The `made_up_tool` tool lists them.\n",
                     "Then calling `made_up_tool`.\n"):
            self.assertEqual(len(self.check(text)), 1, text)

    def test_ordinary_snake_case_words_are_not_tools(self):
        text = "Pass `project_id` and the `session_id`; set `expected_revision`. See docs/work_patterns.md and scripts/pool_hook.py.\n"
        self.assertEqual(self.check(text), [])

    def test_fenced_blocks_are_checked_for_known_names_and_calls(self):
        text = "```\nlist_jobs_tool\nmade_up_tool(1)\nplain_words here\n```\n"
        errors = self.check(text)
        self.assertEqual(len(errors), 2)

    def test_file_names_with_a_known_stem_are_not_tokens(self):
        self.assertEqual(self.check("See references/list_jobs_tool.md and exec/run.\n"), [])

    def test_trailing_sentence_period_still_counts(self):
        self.assertEqual(len(self.check("Never use `principal_context`.\n")), 1)

    def test_scans_every_markdown_file_under_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_tree(Path(tmp), "fine\n")
            extra = root / "plugins/plotune/skills/demo/roles/a.md"
            extra.parent.mkdir()
            extra.write_text("Call `principal_context`.\n", encoding="utf-8")
            errors = cgt.check(root)
        self.assertEqual(len(errors), 1)
        self.assertIn("roles/a.md:1", errors[0])

    def test_other_plugins_are_not_scanned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_tree(Path(tmp), "fine\n")
            other = root / "plugins/plotune-stream/skills/s/SKILL.md"
            other.parent.mkdir(parents=True)
            other.write_text("Call `principal_context`.\n", encoding="utf-8")
            self.assertEqual(cgt.check(root), [])

    def test_reference_file_must_be_consistent(self):
        bad = dict(DATA, tools=["plotune_projects_list", "Bad-Name"])
        errors = self.check("fine\n", data=bad)
        self.assertTrue(any("Bad-Name" in e for e in errors))
        missing = dict(DATA, tools=["nexus_exec"])
        self.assertTrue(any("plotune_projects_list" in e for e in self.check("fine\n", data=missing)))
        dangling = dict(DATA, renamed={"exec": "nexus_gone"})
        self.assertTrue(any("nexus_gone" in e for e in self.check("fine\n", data=dangling)))

    def test_missing_reference_file_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            errors = cgt.check(Path(tmp))
        self.assertTrue(errors and "gateway-tools.json" in errors[0])

    def test_main_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_tree(Path(tmp), "Call `principal_context`.\n")
            self.assertEqual(cgt.main([str(root)]), 1)
            (root / "plugins/plotune/skills/demo/SKILL.md").write_text("Call `plotune_projects_list`.\n", encoding="utf-8")
            self.assertEqual(cgt.main([str(root)]), 0)


if __name__ == "__main__":
    unittest.main()

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import check_evals  # noqa: E402

REPO_ROOT = TOOLS.parent

PROMPT = "---\nmax_turns: 6\nallowed_tools: [Skill]\n---\n\nHow do I do the thing?\n"
SKILL_FIRED = "---\ntype: tool_used\ntool: Skill\ninput_match: '\"skill\"\\s*:\\s*\"(?:[\\w-]+:)?my-skill\"'\n---\n"
LLM = "---\ntype: llm\n---\n\nPASS if it answers. FAIL otherwise.\n"
REGEX = "---\ntype: regex\npattern: 'thing'\nflags: i\n---\n"


def make_tree(root: Path) -> Path:
    skill = root / "plugins/demo/skills/my-skill/SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: my-skill\ndescription: d\n---\n", encoding="utf-8")
    case = root / "plugins/demo/evals/first"
    (case / "graders").mkdir(parents=True)
    (case / "prompt.md").write_text(PROMPT, encoding="utf-8")
    (case / "graders/skill-fired.md").write_text(SKILL_FIRED, encoding="utf-8")
    (case / "graders/answer.md").write_text(LLM, encoding="utf-8")
    return root


class CheckEvalsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = make_tree(Path(self._tmp.name))
        self.case = self.root / "plugins/demo/evals/first"

    def assertError(self, needle):
        errs = check_evals.check(self.root)
        self.assertTrue(any(needle in e for e in errs), f"{needle!r} not in {errs}")

    def test_valid_suite_has_no_errors(self):
        self.assertEqual(check_evals.check(self.root), [])

    def test_plugin_without_evals_is_fine(self):
        import shutil
        shutil.rmtree(self.root / "plugins/demo/evals")
        self.assertEqual(check_evals.check(self.root), [])

    def test_case_needs_prompt_md(self):
        (self.case / "prompt.md").unlink()
        self.assertError("prompt.md")

    def test_prompt_body_must_not_be_empty_or_a_todo(self):
        (self.case / "prompt.md").write_text("---\nmax_turns: 5\n---\n\nTODO: describe what the agent should do\n")
        self.assertError("TODO")
        (self.case / "prompt.md").write_text("---\nmax_turns: 5\n---\n\n   \n")
        self.assertError("empty")

    def test_case_needs_at_least_one_grader(self):
        for f in (self.case / "graders").glob("*.md"):
            f.unlink()
        self.assertError("grader")

    def test_grader_type_must_be_known(self):
        (self.case / "graders/odd.md").write_text("---\ntype: vibes\n---\n")
        self.assertError("vibes")

    def test_grader_without_frontmatter_type(self):
        (self.case / "graders/odd.md").write_text("PASS if good.\n")
        self.assertError("type")

    def test_llm_grader_rubric_must_not_be_a_todo(self):
        (self.case / "graders/answer.md").write_text("---\ntype: llm\n---\n\nTODO: describe what a successful response looks like\n")
        self.assertError("TODO")

    def test_regex_grader_needs_pattern(self):
        (self.case / "graders/r.md").write_text("---\ntype: regex\n---\n")
        self.assertError("pattern")
        (self.case / "graders/r.md").write_text(REGEX)
        self.assertEqual(check_evals.check(self.root), [])

    def test_skill_grader_must_name_an_existing_skill(self):
        (self.case / "graders/skill-fired.md").write_text(SKILL_FIRED.replace("my-skill", "no-such-skill"))
        self.assertError("no-such-skill")

    def test_skill_grader_must_name_a_skill_of_its_own_plugin(self):
        other = self.root / "plugins/other/skills/other-skill/SKILL.md"
        other.parent.mkdir(parents=True)
        other.write_text("---\nname: other-skill\ndescription: d\n---\n")
        (self.case / "graders/skill-fired.md").write_text(SKILL_FIRED.replace("my-skill", "other-skill"))
        self.assertError("other-skill")

    def test_non_skill_tool_used_grader_is_not_checked_against_skills(self):
        (self.case / "graders/t.md").write_text("---\ntype: tool_used\ntool: Bash\nmin: 0\nmax: 0\n---\n")
        self.assertEqual(check_evals.check(self.root), [])

    def test_regex_pattern_must_compile(self):
        (self.case / "graders/r.md").write_text("---\ntype: regex\npattern: '(unclosed'\n---\n")
        self.assertError("pattern")

    def test_unescaped_single_quote_inside_single_quoted_value(self):
        (self.case / "graders/r.md").write_text("---\ntype: regex\npattern: 'I('ve done it)'\n---\n")
        self.assertError("quote")

    def test_doubled_single_quote_is_valid_yaml(self):
        (self.case / "graders/r.md").write_text("---\ntype: regex\npattern: 'I(''ve) done'\n---\n")
        self.assertEqual(check_evals.check(self.root), [])

    def test_unescaped_double_quote_inside_double_quoted_value(self):
        (self.case / "graders/r.md").write_text('---\ntype: regex\npattern: "say "hi" now"\n---\n')
        self.assertError("quote")

    def test_escaped_double_quote_is_valid_yaml(self):
        (self.case / "graders/r.md").write_text('---\ntype: regex\npattern: "say \\"hi\\" now"\n---\n')
        self.assertEqual(check_evals.check(self.root), [])

    def test_unterminated_quoted_value(self):
        (self.case / "prompt.md").write_text("---\nmax_turns: 5\ntags: 'oops\n---\n\nA real prompt.\n")
        self.assertError("quote")

    def test_quote_problem_in_prompt_frontmatter_is_found_too(self):
        (self.case / "prompt.md").write_text("---\nnote: 'it's bad'\n---\n\nA real prompt.\n")
        self.assertError("prompt.md")

    def test_unreadable_file_is_reported_not_raised(self):
        (self.case / "prompt.md").write_bytes(b"---\n\xff\n---\n")
        self.assertError("prompt.md")

    def test_main_exit_codes(self):
        self.assertEqual(check_evals.main([str(self.root)]), 0)
        (self.case / "prompt.md").unlink()
        self.assertEqual(check_evals.main([str(self.root)]), 1)

    def test_real_repo_evals_pass(self):
        self.assertEqual(check_evals.check(REPO_ROOT), [])


if __name__ == "__main__":
    unittest.main()

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import check_skills  # noqa: E402

REPO_ROOT = TOOLS.parent


def write_skill(root: Path, dirname: str, text: str, plugin="demo"):
    p = root / "plugins" / plugin / "skills" / dirname / "SKILL.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


GOOD = "---\nname: my-skill\ndescription: Use when testing things.\n---\n\n# Body\n"


class ParseFrontmatterTest(unittest.TestCase):
    def test_plain_values(self):
        fm = check_skills.parse_frontmatter(GOOD)
        self.assertEqual(fm, {"name": "my-skill", "description": "Use when testing things."})

    def test_quoted_value_is_unquoted(self):
        fm = check_skills.parse_frontmatter('---\nname: "a-b"\ndescription: \'Use it\'\n---\n')
        self.assertEqual(fm["name"], "a-b")
        self.assertEqual(fm["description"], "Use it")

    def test_block_scalar_and_continuation_lines_are_joined(self):
        fm = check_skills.parse_frontmatter("---\nname: a\ndescription: >\n  first line\n  second line\n---\n")
        self.assertEqual(fm["description"], "first line second line")
        fm = check_skills.parse_frontmatter("---\nname: a\ndescription: starts here\n  and continues\n---\n")
        self.assertEqual(fm["description"], "starts here and continues")

    def test_crlf_line_endings(self):
        fm = check_skills.parse_frontmatter("---\r\nname: a\r\ndescription: d\r\n---\r\nbody")
        self.assertEqual(fm, {"name": "a", "description": "d"})

    def test_missing_or_unclosed_returns_none(self):
        self.assertIsNone(check_skills.parse_frontmatter("# no frontmatter\n"))
        self.assertIsNone(check_skills.parse_frontmatter("---\nname: a\n"))


class CheckSkillsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def assertError(self, needle):
        errs = check_skills.check(self.root)
        self.assertTrue(any(needle in e for e in errs), f"{needle!r} not in {errs}")

    def test_valid_skill_has_no_errors(self):
        write_skill(self.root, "my-skill", GOOD)
        self.assertEqual(check_skills.check(self.root), [])

    def test_no_plugins_dir_is_fine(self):
        self.assertEqual(check_skills.check(self.root), [])

    def test_missing_frontmatter(self):
        write_skill(self.root, "my-skill", "# nothing\n")
        self.assertError("frontmatter")

    def test_name_must_match_directory(self):
        write_skill(self.root, "other-dir", GOOD)
        self.assertError("other-dir")

    def test_name_must_be_lowercase_hyphenated(self):
        write_skill(self.root, "My_Skill", "---\nname: My_Skill\ndescription: d\n---\n")
        self.assertError("lowercase")

    def test_name_too_long(self):
        long = "a" * 65
        write_skill(self.root, long, f"---\nname: {long}\ndescription: d\n---\n")
        self.assertError("64")

    def test_missing_name(self):
        write_skill(self.root, "my-skill", "---\ndescription: d\n---\n")
        self.assertError("name")

    def test_missing_or_empty_description(self):
        write_skill(self.root, "a-one", "---\nname: a-one\n---\n")
        write_skill(self.root, "a-two", "---\nname: a-two\ndescription:\n---\n")
        errs = [e for e in check_skills.check(self.root) if "description" in e]
        self.assertEqual(len(errs), 2)

    def test_description_over_1024_chars(self):
        write_skill(self.root, "my-skill", "---\nname: my-skill\ndescription: " + "x" * 1025 + "\n---\n")
        self.assertError("1024")

    def test_skill_directory_without_skill_md(self):
        (self.root / "plugins/demo/skills/empty-one").mkdir(parents=True)
        self.assertError("SKILL.md")

    def test_non_utf8_file_is_reported_not_raised(self):
        p = write_skill(self.root, "my-skill", GOOD)
        p.write_bytes(b"---\nname: my-skill\ndescription: \xff\n---\n")
        self.assertError("my-skill")

    def test_main_exit_codes(self):
        write_skill(self.root, "my-skill", GOOD)
        self.assertEqual(check_skills.main([str(self.root)]), 0)
        write_skill(self.root, "bad", "nope")
        self.assertEqual(check_skills.main([str(self.root)]), 1)

    def test_real_repo_skills_pass(self):
        self.assertEqual(check_skills.check(REPO_ROOT), [])


if __name__ == "__main__":
    unittest.main()

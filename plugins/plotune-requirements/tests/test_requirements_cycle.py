import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/requirements-cycle/SKILL.md"


class RequirementsCycleTests(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text()
        self.lower = self.text.lower()

    def test_roles_and_orchestrator_mode(self):
        for token in ["Designer", "Build", "Verify", "Orchestrator", "Independent reviewer"]:
            self.assertIn(token, self.text)
        self.assertIn("no separate orchestrator agent", self.lower)

    def test_all_nine_v_steps_are_assigned(self):
        for step in ["Need and requirement analysis", "System design", "Architecture design",
                     "Module detail design", "Implementation", "Unit test",
                     "Integration test", "System test", "Acceptance test"]:
            self.assertIn(step, self.text)

    def test_build_has_no_direct_line_to_orchestrator(self):
        self.assertIn("Build has no direct line to the Orchestrator", self.text)

    def test_exactly_two_automatic_stops_and_user_stop(self):
        self.assertIn("in **two** cases", self.text)
        for token in ["Goal deviation", "Impact outside the scope", "no iteration caps", "that is enough"]:
            self.assertIn(token.lower(), self.lower)

    def test_progress_is_per_level_and_pass_needs_evidence(self):
        self.assertIn("not per goal", self.lower)
        self.assertIn("not verified", self.lower)
        self.assertIn("without evidence", self.lower)

    def test_authority_separation(self):
        for token in ["freeze and release are the user's", "never approves it", "never rewrites an approved requirement"]:
            self.assertIn(token, self.lower)

    def test_narrow_requests_skip_the_loop(self):
        self.assertIn("narrow single-role request", self.lower)
        self.assertIn("do not start the loop", self.lower)

    def test_no_private_references(self):
        for token in ["docs.google.com/spreadsheets/d/", "github.com/plotune/"]:
            self.assertNotIn(token, self.text)

    def test_routed_from_agent_execution(self):
        self.assertIn("requirements-cycle", (ROOT / "skills/agent-execution/SKILL.md").read_text())


if __name__ == "__main__":
    unittest.main()

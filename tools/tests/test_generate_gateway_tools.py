import json
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import generate_gateway_tools as gen  # noqa: E402


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def make_catalog(root: Path) -> Path:
    catalog = root / "packages/contracts/mcp-catalog"
    write_json(catalog / "rms.json", {"product": "rms", "tools": [
        {"name": "requirements_get"}, {"name": "admin_projects_list"}]})
    write_json(catalog / "stream.json", {"product": "stream", "tools": [
        {"name": "events_query"}, {"name": "projects_list"}]})
    write_json(catalog / "nexus.json", {"product": "nexus", "tools": [
        {"name": "nexus_start_session"}, {"name": "exec"}, {"name": "list_jobs_tool"}]})
    write_json(catalog / "mapping.json", {
        "renames": {"nexus_exec": {"product": "nexus", "tool": "exec"},
                    "nexus_list_jobs": {"product": "nexus", "tool": "list_jobs_tool"},
                    "get_dds_domain_status": {"product": "nexus", "tool": "get_dds_domain_status_tool"}},
        "titles": {},
        "exclude": {"rms": {"admin_projects_list": "System Admin only."},
                    "stream": {"projects_list": "Superseded by plotune_projects_list."},
                    "nexus": {}},
        "readAuthorized": {"stream": []}})
    write_json(root / "packages/contracts/nexus-v2/fixtures/session-tools.json", {"tools": [
        {"name": "send_can_frame"},
        {"name": "get_dds_domain_status_tool"},
        {"name": "hidden_probe", "_meta": {"nexus": {"internal": True}}}]})
    return catalog


class GenerateGatewayToolsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.catalog = make_catalog(Path(self._tmp.name))

    def test_gateway_names_follow_catalog_ts(self):
        data = gen.generate(self.catalog, commit="abc123")
        self.assertEqual(data["tools"], sorted([
            "plotune_projects_list", "requirements_get", "events_query", "nexus_start_session", "nexus_exec",
            "nexus_list_jobs", "send_can_frame", "get_dds_domain_status"]))

    def test_renames_are_recorded_old_to_new(self):
        data = gen.generate(self.catalog, commit="abc123")
        self.assertEqual(data["renamed"], {"exec": "nexus_exec", "list_jobs_tool": "nexus_list_jobs",
                                           "get_dds_domain_status_tool": "get_dds_domain_status"})

    def test_excluded_and_internal_tools_are_recorded_with_a_reason(self):
        data = gen.generate(self.catalog, commit="abc123")
        self.assertIn("admin_projects_list", data["excluded"])
        self.assertIn("projects_list", data["excluded"])
        self.assertIn("hidden_probe", data["excluded"])
        self.assertNotIn("hidden_probe", data["tools"])
        self.assertNotIn("admin_projects_list", data["tools"])

    def test_records_the_commit(self):
        data = gen.generate(self.catalog, commit="abc123")
        self.assertEqual(data["generatedFrom"]["commit"], "abc123")

    def test_output_is_deterministic_and_check_detects_drift(self):
        out = Path(self._tmp.name) / "out.json"
        self.assertEqual(gen.main([str(self.catalog), "--commit", "abc123", "--out", str(out)]), 0)
        first = out.read_text(encoding="utf-8")
        self.assertEqual(gen.main([str(self.catalog), "--commit", "abc123", "--out", str(out)]), 0)
        self.assertEqual(out.read_text(encoding="utf-8"), first)
        self.assertEqual(gen.main([str(self.catalog), "--check", "--out", str(out)]), 0)
        write_json(self.catalog / "rms.json", {"product": "rms", "tools": [
            {"name": "requirements_get"}, {"name": "requirements_list"}, {"name": "admin_projects_list"}]})
        self.assertEqual(gen.main([str(self.catalog), "--check", "--out", str(out)]), 1)

    def test_missing_catalog_is_an_error(self):
        self.assertEqual(gen.main([str(Path(self._tmp.name) / "nope"), "--commit", "x",
                                   "--out", str(Path(self._tmp.name) / "o.json")]), 2)


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class DecompositionPolicyTests(unittest.TestCase):
 def test_route_is_composable(self):
  for path in ["skills/agent-execution/SKILL.md","skills/work-orchestration/SKILL.md","skills/requirements-governance/SKILL.md","skills/traceable-delivery/SKILL.md"]:
   self.assertIn("requirement-decomposition",(ROOT/path).read_text(),path)
 def test_draft_and_separation(self):
  s=(ROOT/"skills/requirement-decomposition/SKILL.md").read_text()
  for text in ["Draft rev 1", "author", "independently", "Frozen", "In Review", "Superseded", "Rejected", "Retired", "multiple", "approv"]:
   self.assertIn(text.lower(),s.lower())
 def test_portable_schema_unchanged(self):
  import json
  d=json.loads((ROOT/"schema/data-model.json").read_text())
  self.assertEqual(d["schema_version"],"1.1.0")
  self.assertIn("parent_requirement_ids",d["tables"]["requirements"]["columns"])
  self.assertIn("Draft",d["enums"]["requirement_lifecycle_status"])

if __name__=="__main__": unittest.main()

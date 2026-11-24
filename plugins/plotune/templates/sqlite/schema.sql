-- Plotune Requirements portable schema v1.1.0. Blank / user-owned; never contains private data.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS workspace_meta (schema_version TEXT NOT NULL, workspace_id TEXT NOT NULL PRIMARY KEY, display_name TEXT);

CREATE TABLE IF NOT EXISTS products (
  product_id TEXT NOT NULL,
  product_name TEXT,
  parent_id TEXT,
  type TEXT,
  scope TEXT,
  repository_url TEXT,
  PRIMARY KEY (product_id)
);

CREATE TABLE IF NOT EXISTS stakeholder_needs (
  need_id TEXT NOT NULL,
  product_id TEXT,
  statement TEXT,
  stakeholder TEXT,
  source_url TEXT,
  status TEXT,
  rationale TEXT,
  updated_at_utc TEXT,
  PRIMARY KEY (need_id),
  FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS actors (
  actor_id TEXT NOT NULL,
  product_id TEXT,
  name TEXT,
  actor_type TEXT,
  purpose TEXT,
  system_boundary_context TEXT,
  status TEXT,
  source_url TEXT,
  updated_at_utc TEXT,
  notes TEXT,
  PRIMARY KEY (actor_id),
  FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS use_cases (
  use_case_id TEXT NOT NULL,
  product_id TEXT,
  title TEXT,
  goal TEXT,
  operational_context TEXT,
  trigger TEXT,
  preconditions TEXT,
  main_flow TEXT,
  alternates_failure TEXT,
  status TEXT,
  updated_at_utc TEXT,
  notes TEXT,
  PRIMARY KEY (use_case_id),
  FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS requirements (
  requirement_id TEXT NOT NULL,
  product_id TEXT,
  category TEXT,
  requirement TEXT,
  rationale TEXT,
  acceptance_criteria TEXT,
  lifecycle_status TEXT,
  revision INTEGER,
  source_url TEXT,
  updated_at_utc TEXT,
  updated_by TEXT,
  parent_requirement_ids TEXT,
  hierarchy_level INTEGER,
  notes TEXT,
  PRIMARY KEY (requirement_id),
  FOREIGN KEY (product_id) REFERENCES products(product_id),
  CHECK (revision IS NULL OR revision >= 1)
);

CREATE TABLE IF NOT EXISTS requirement_revisions (
  requirement_id TEXT NOT NULL,
  revision INTEGER NOT NULL,
  requirement_snapshot TEXT,
  acceptance_criteria_snapshot TEXT,
  changed_at_utc TEXT,
  changed_by TEXT,
  reason TEXT,
  PRIMARY KEY (requirement_id, revision),
  FOREIGN KEY (requirement_id) REFERENCES requirements(requirement_id)
);

CREATE TABLE IF NOT EXISTS applicability (
  requirement_id TEXT NOT NULL,
  product_id TEXT NOT NULL,
  notes TEXT,
  PRIMARY KEY (requirement_id, product_id),
  FOREIGN KEY (requirement_id) REFERENCES requirements(requirement_id),
  FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS traceability (
  from_type TEXT,
  from_id TEXT,
  relation TEXT,
  to_type TEXT,
  to_id TEXT,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS verification (
  verification_id TEXT NOT NULL,
  requirement_id TEXT,
  requirement_revision INTEGER,
  product_id TEXT,
  stage TEXT,
  method TEXT,
  result TEXT,
  evidence_url TEXT,
  evidence_summary TEXT,
  provenance TEXT,
  verified_at_utc TEXT,
  verified_by TEXT,
  notes TEXT,
  PRIMARY KEY (verification_id),
  FOREIGN KEY (requirement_id) REFERENCES requirements(requirement_id)
);

CREATE TABLE IF NOT EXISTS baselines (
  baseline_id TEXT NOT NULL,
  product_id TEXT,
  product_version TEXT,
  status TEXT,
  frozen_at_utc TEXT,
  approved_by TEXT,
  snapshot_url TEXT,
  notes TEXT,
  PRIMARY KEY (baseline_id),
  FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS baseline_items (
  baseline_id TEXT NOT NULL,
  requirement_id TEXT NOT NULL,
  requirement_revision INTEGER,
  requirement_snapshot TEXT,
  acceptance_criteria_snapshot TEXT,
  notes TEXT,
  PRIMARY KEY (baseline_id, requirement_id),
  FOREIGN KEY (baseline_id) REFERENCES baselines(baseline_id),
  FOREIGN KEY (requirement_id) REFERENCES requirements(requirement_id)
);

CREATE TABLE IF NOT EXISTS verification_runs (
  execution_id TEXT NOT NULL,
  verification_id TEXT,
  requirement_id TEXT,
  requirement_revision INTEGER,
  product_id TEXT,
  maturity_level TEXT,
  maturity_name TEXT,
  result TEXT,
  coverage TEXT,
  evidence_url TEXT,
  evidence_summary TEXT,
  setup_tools TEXT,
  tested_at_utc TEXT,
  tested_by TEXT,
  notes TEXT,
  PRIMARY KEY (execution_id),
  FOREIGN KEY (requirement_id) REFERENCES requirements(requirement_id),
  FOREIGN KEY (verification_id) REFERENCES verification(verification_id)
);

CREATE TABLE IF NOT EXISTS test_cases (
  test_case_id TEXT NOT NULL,
  verification_id TEXT,
  requirement_id TEXT,
  requirement_revision INTEGER,
  product_id TEXT,
  title TEXT,
  method TEXT,
  min_level TEXT,
  target_level TEXT,
  applicable_levels TEXT,
  mandatory INTEGER,
  procedure TEXT,
  status TEXT,
  baseline_id TEXT,
  notes TEXT,
  PRIMARY KEY (test_case_id),
  FOREIGN KEY (requirement_id) REFERENCES requirements(requirement_id),
  FOREIGN KEY (baseline_id) REFERENCES baselines(baseline_id)
);

CREATE TABLE IF NOT EXISTS test_executions (
  execution_id TEXT NOT NULL,
  test_case_id TEXT,
  requirement_id TEXT,
  requirement_revision INTEGER,
  product_id TEXT,
  maturity_level TEXT,
  maturity_name TEXT,
  result TEXT,
  coverage TEXT,
  evidence_url TEXT,
  evidence_summary TEXT,
  setup_tools TEXT,
  tested_at_utc TEXT,
  tested_by TEXT,
  build_commit TEXT,
  notes TEXT,
  PRIMARY KEY (execution_id),
  FOREIGN KEY (requirement_id) REFERENCES requirements(requirement_id),
  FOREIGN KEY (test_case_id) REFERENCES test_cases(test_case_id)
);

CREATE TABLE IF NOT EXISTS tasks (
  task_id TEXT NOT NULL,
  project_id TEXT,
  goal TEXT,
  lead_agent TEXT,
  session_run_id TEXT,
  status TEXT,
  deliverable_url TEXT,
  blocker TEXT,
  created_at_utc TEXT,
  updated_at_utc TEXT,
  completed_at_utc TEXT,
  requirement_ids TEXT,
  PRIMARY KEY (task_id)
);

CREATE TABLE IF NOT EXISTS audit_log (
  timestamp_utc TEXT,
  event_id TEXT NOT NULL,
  actor_type TEXT,
  actor_id TEXT,
  model TEXT,
  entity TEXT,
  record_id TEXT,
  action TEXT,
  field TEXT,
  old_value TEXT,
  new_value TEXT,
  reason_evidence_url TEXT,
  PRIMARY KEY (event_id)
);

CREATE TABLE IF NOT EXISTS decisions (
  decision_id TEXT NOT NULL,
  product_id TEXT,
  topic TEXT,
  decision TEXT,
  status TEXT,
  rationale TEXT,
  source_url TEXT,
  decided_by TEXT,
  decided_at_utc TEXT,
  notes TEXT,
  PRIMARY KEY (decision_id),
  FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TRIGGER IF NOT EXISTS frozen_baseline_immutable_update
BEFORE UPDATE ON baselines WHEN OLD.status = 'Frozen'
BEGIN SELECT RAISE(ABORT, 'frozen baseline is immutable'); END;

CREATE TRIGGER IF NOT EXISTS frozen_baseline_immutable_delete
BEFORE DELETE ON baselines WHEN OLD.status = 'Frozen'
BEGIN SELECT RAISE(ABORT, 'frozen baseline is immutable'); END;

CREATE TRIGGER IF NOT EXISTS no_add_to_frozen_baseline
BEFORE INSERT ON baseline_items WHEN (SELECT status FROM baselines WHERE baseline_id=NEW.baseline_id)='Frozen'
BEGIN SELECT RAISE(ABORT, 'cannot add to frozen baseline'); END;

CREATE TRIGGER IF NOT EXISTS no_change_frozen_baseline_items
BEFORE UPDATE ON baseline_items WHEN (SELECT status FROM baselines WHERE baseline_id=OLD.baseline_id)='Frozen' OR (SELECT status FROM baselines WHERE baseline_id=NEW.baseline_id)='Frozen'
BEGIN SELECT RAISE(ABORT, 'cannot change frozen baseline items'); END;

CREATE TRIGGER IF NOT EXISTS no_delete_frozen_baseline_items
BEFORE DELETE ON baseline_items WHEN (SELECT status FROM baselines WHERE baseline_id=OLD.baseline_id)='Frozen'
BEGIN SELECT RAISE(ABORT, 'cannot delete frozen baseline items'); END;


-- Continuous Engineering records: workspace-owned, never prepopulated.
CREATE TABLE IF NOT EXISTS change_requests (
  change_id TEXT NOT NULL PRIMARY KEY,
  product_id TEXT REFERENCES products(product_id),
  title TEXT, reason TEXT, source_url TEXT, requester TEXT,
  baseline_id TEXT REFERENCES baselines(baseline_id),
  impact_summary TEXT, safety_impact TEXT, verification_impact TEXT,
  proposed_change TEXT, status TEXT, owner TEXT, decision TEXT, decision_by TEXT,
  decided_at_utc TEXT, created_at_utc TEXT, updated_at_utc TEXT,
  implemented_at_utc TEXT, closed_at_utc TEXT, evidence_url TEXT
);
CREATE TABLE IF NOT EXISTS standards_profiles (
  profile_id TEXT NOT NULL PRIMARY KEY,
  product_id TEXT REFERENCES products(product_id),
  standard TEXT NOT NULL, edition TEXT, scope TEXT, tailoring TEXT,
  reference_url TEXT, status TEXT, reviewer TEXT, reviewed_at_utc TEXT, notes TEXT
);
CREATE TABLE IF NOT EXISTS review_findings (
  finding_id TEXT NOT NULL PRIMARY KEY,
  product_id TEXT REFERENCES products(product_id),
  record_type TEXT, record_id TEXT, record_revision TEXT, check_id TEXT,
  title TEXT, description TEXT, evidence_url TEXT, severity TEXT, confidence TEXT,
  recommendation TEXT, standard_profile_id TEXT REFERENCES standards_profiles(profile_id),
  status TEXT, owner TEXT, change_request_id TEXT REFERENCES change_requests(change_id),
  created_at_utc TEXT, updated_at_utc TEXT, closed_at_utc TEXT, resolution_notes TEXT
);
CREATE TABLE IF NOT EXISTS change_impacts (
  impact_id TEXT NOT NULL PRIMARY KEY,
  change_id TEXT NOT NULL REFERENCES change_requests(change_id),
  target_type TEXT, target_id TEXT, target_revision TEXT, impact_kind TEXT,
  rationale TEXT, evidence_url TEXT, disposition TEXT, owner TEXT, updated_at_utc TEXT
);
CREATE INDEX IF NOT EXISTS idx_findings_record ON review_findings(record_type,record_id,record_revision);
CREATE INDEX IF NOT EXISTS idx_findings_change ON review_findings(change_request_id);
CREATE INDEX IF NOT EXISTS idx_changes_product ON change_requests(product_id);
CREATE INDEX IF NOT EXISTS idx_impacts_change ON change_impacts(change_id);
CREATE INDEX IF NOT EXISTS idx_impacts_target ON change_impacts(target_type,target_id,target_revision);

-- Review and change closure must retain written disposition.
CREATE TRIGGER IF NOT EXISTS closed_finding_requires_resolution_insert
BEFORE INSERT ON review_findings WHEN NEW.status='Closed' AND TRIM(COALESCE(NEW.resolution_notes,''))=''
BEGIN SELECT RAISE(ABORT,'closed finding requires resolution'); END;
CREATE TRIGGER IF NOT EXISTS closed_finding_requires_resolution_update
BEFORE UPDATE ON review_findings WHEN NEW.status='Closed' AND TRIM(COALESCE(NEW.resolution_notes,''))=''
BEGIN SELECT RAISE(ABORT,'closed finding requires resolution'); END;
CREATE TRIGGER IF NOT EXISTS closed_change_requires_decision_insert
BEFORE INSERT ON change_requests WHEN NEW.status='Closed' AND TRIM(COALESCE(NEW.decision,''))=''
BEGIN SELECT RAISE(ABORT,'closed change requires decision'); END;
CREATE TRIGGER IF NOT EXISTS closed_change_requires_decision_update
BEFORE UPDATE ON change_requests WHEN NEW.status='Closed' AND TRIM(COALESCE(NEW.decision,''))=''
BEGIN SELECT RAISE(ABORT,'closed change requires decision'); END;

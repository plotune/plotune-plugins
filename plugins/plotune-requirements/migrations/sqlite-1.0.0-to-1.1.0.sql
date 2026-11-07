-- Run ONLY on a backed-up 1.0.0 SQLite workspace after explicit user authorization.
-- Do not attempt this against user-owned existing managed ALM schemas.
PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;

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

UPDATE workspace_meta SET schema_version = '1.1.0' WHERE schema_version = '1.0.0';
COMMIT;

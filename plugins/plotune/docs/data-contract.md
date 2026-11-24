# Plotune Requirements — Portable Data Contract v1.1.0

This contract is backend-independent. It is **not** a database dump or copy of any maintained customer workspace. The normative inventory is `schema/data-model.json` and the manifest format is `schema/workspace.schema.json`. Each packaged CSV is a blank, header-only implementation. SQLite schema and blank Google Sheets workbook implement the same entity/column names.

## Identity and provenance

- All IDs are durable strings assigned in the *user's* workspace; never reuse or infer IDs from another workspace. Record timestamps in UTC using actual known time. `model`, `actor`, `source_url`, and `evidence_url` may be blank when unknown, never invented.
- A `requirements` row represents the current revision. `requirement_revisions` stores the exact historical normative text and acceptance snapshots, at minimum for every revision authored after adopting this schema. An importer must label unavailable legacy history as unavailable, not reconstruct it from guesses.
- `parent_requirement_ids` is a comma-separated list of zero or more existing requirement IDs. The hierarchy must be a DAG (no missing parent, self-parent, or indirect cycle). `hierarchy_level` is a **derived depth** (`0` for root, max(parent depths)+1 otherwise); do not confuse it with verification maturity. Parent links only express actual normative refinement; dependencies and associations belong to `traceability`.
- `traceability`: `from_type`, `from_id`, `relation`, `to_type`, `to_id`, `notes`. Types name a record table or an explicitly marked `external` artifact with verifiable URI. Typical links: Actor → Use Case (`Participates In`), Use Case → Requirement (`Motivates`), Need → Requirement (`Derives Into`), Requirement → Test Case (`Verified By`), Requirement → Requirement (`Depends On`). Typed links do not automatically establish hierarchy.
- `applicability` adds cross-product application without duplicating normative requirements.

## Lifecycles, baselines and evidence

- Requirement lifecycle: `Draft`, `In Review`, `Approved`, `Rejected`, `Superseded`, `Retired`; add/migrate workspace-specific values explicitly. Baseline status: `Draft`, `Frozen`, `Superseded`. Verification result: `PASS`, `FAIL`, `NOT VERIFIED`, `BLOCKED`. Task statuses are independent.
- Approvals require actual delegated owner action. Each `baseline_items` row preserves the requirement ID, exact revision, normative text and criteria. Frozen snapshots cannot be edited; changed requirements belong in a successor baseline.
- `verification` and `verification_runs` retain verifiable results; `test_cases` are definitions and `test_executions` are real observations. A linked PR, model output, code review or baseline alone is not PASS; complete applicable acceptance and actual cited evidence are required. Historical evidence retains its provenance and scope limits; do not silently degrade substantiated results during migration.
- `maturity_level` / `maturity_name` have **no built-in universal scale**. Use documented definitions supplied in the user's own workspace, or leave them open. Do not confuse discovery Level 1/2, hierarchy depth, requirement revision and maturity stage.
- Audit events retain timestamp, record ID, field, old/new value, actor/model when known and reason. For requirements, record revision changes atomically with changes to current text and `requirement_revisions`.
- `Tasks` rows identify independently trackable goals, **not unique conversations**: one session may have multiple active task IDs. The responsible lead integrates results and owns canonical task updates; optional delegated sub-work has distinct IDs/links when supported. Use verified task ID + product/goal/owner to resume, not session ID alone. These rows do not create background workers.

## Table inventory

| Group | Portable table | Role |
| --- | --- | --- |
| Scope | `products` | Products/families and explicit ownership |
| Discovery | `stakeholder_needs`, `actors`, `use_cases` | Needs, system actors, operational scenarios |
| Requirement | `requirements`, `requirement_revisions`, `applicability` | Normative current and historical revisions, scope |
| Relationship | `traceability` | Typed, non-parent references |
| Governance | `decisions`, `audit_log`, `baselines`, `baseline_items` | Authority, history and immutable snapshots |
| Verification | `verification`, `verification_runs`, `test_cases`, `test_executions` | Test definition, real execution and evidence |
| Execution | `tasks` | Agent leadership/checkpoints |
| Continuous review | `review_findings` | Evidence-backed quality findings with actual target ID/revision, reviewer, status and resolution |
| Controlled change | `change_requests`, `change_impacts` | Owner decisions and typed per-target/revision impact records; no approval inferred |
| Standards | `standards_profiles` | Project-selected standard edition/scope/tailoring, no pre-activated profile |

Computed dashboards such as verification summaries, readiness or maturity aggregation are **views**, not new authoritative records. Regenerate rather than overwriting raw evidence.

## Review, change, standard profiles and evidence

- `review_findings` references an existing engineering record and exact revision (if revisioned). A model-generated finding is a candidate, not an automatic nonconformance. Keep sources, check ID, severity and review disposition. Closure requires documented resolution, never a fabricated PASS.
- `change_requests` captures user-owned proposal, owner decision and lifecycle; `change_impacts` stores each impacted target independently, including exact requirement revision and evidence/disposition. A change can be authorized while re-verification remains open. Track changed scope against baseline snapshots without rewriting Frozen members. Use normal audit entries for state and decision changes.
- `standards_profiles` records user-selected standard/edition, actual product scope and tailoring. The package contains no customer-standard approval, default ASIL, copied normative standard text, certification claim or automated ASPICE assessment.
- Read-only `scripts/review.py` checks structure/typed links, shows exact-revision verification coverage and traverses candidate change impacts for local SQLite/CSV. Its diagnostic output **never creates findings or approval/evidence rows**; responsible reviewers make semantic and safety judgments.
- Existing 1.0.0 databases remain authoritative. The 1.1.0 extension is additive; `docs/schema-upgrade.md` governs explicit backup, dry-run and verified adoption. Existing RMS/Sheets may map their own objects without physically adding these tables.

## Implementations

- **Plotune RMS**: Resolve actual authenticated project and available API; map fields to native schema, do not invent an endpoint.
- **Google Sheets**: Import/copy `templates/google-sheets/Plotune-Requirements-Blank.xlsx` as a *new* user-owned workbook. Confirm no existing workspace should be retained before creating. Read back tab names/headers and store its actual URL in the user's workspace manifest.
- **SQLite**: Apply `templates/sqlite/schema.sql` to a new DB; enable foreign keys on each connection. Use transactions. SQLite triggers protect frozen baselines; the caller must still enforce requirement revision and hierarchy validations.
- **CSV**: Use `templates/csv/*.csv` in a dedicated path. Atomic per-file replace and audit append with backup; no cross-file transaction guarantee. Validate before and after writes. Promote to SQLite for many agents and concurrent writes.

Schema evolution: bump `schema_version` and provide explicit migration for breaking changes; no silent truncation of columns, status names, historical snapshots or sources. Export destination = secondary copy, not a new co-authoritative writer.

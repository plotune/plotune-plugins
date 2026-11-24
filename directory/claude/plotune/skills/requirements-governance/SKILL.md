---
name: requirements-governance
description: Review, author, revise, approve, baseline or verify requirements in the user's connected canonical RMS, Google Sheets, SQLite or CSV workspace with audit and evidence integrity.
---

# Portable requirements governance

## Resolve owner and live data

Invoke `workspace-management` first. **Only the user-selected or already-bound workspace is canonical**. Inspect actual backend, current schema version, IDs, headers/fields, read/write permissions, applicable local Guide, requirement revisions, baseline and verification evidence. Do not reference any maintainer workbook, product ID or repository as a default. Never create a parallel authority. The bundled template applies only to a *new* empty workspace; an existing user's schema must be understood and migrated deliberately, not silently replaced.

## Continuous review records

Where the selected user-owned backend supports schema 1.1.0 or an equivalent mapped ALM model, maintain `review_findings`, `change_requests`, `change_impacts` and optional `standards_profiles` as distinct auditable records. A finding points to the actual observed record/revision and remains open until documented disposition; a proposed change is not accepted merely because an agent wrote a draft. Change impacts retain explicit target revision, responsible owner, evidence and disposition. Changes become normative requirement revisions only after the relevant owner authority and controlled audit. Use the relevant review/change/coverage profile skills; do not auto-migrate an older user workspace just to save these records.

## Proactive Drafts are different from approvals

During explicitly authorized active engineering on a writable project, the writer/lead may create necessary lower-level requirements as `Draft` and audit them, without asking for owner approval **per Draft**. Use `requirement-decomposition` for deduplication, parent hierarchy (zero/multiple valid parents, DAG), atomic verification granularity and source/acceptance checks. An expressly read-only review or subagent without write permission remains read-only. Never confuse permission to draft with permission to approve. A writer **cannot approve their own authored/revised requirement**. `In Review → Approved` requires a separate eligible reviewer and the actual project approver or documented bounded approval delegation, with specific actor, exact revision and decision evidence. A supervising lead is not implicitly an approver; delegated authority is never inferred from a task assignment. A new Draft child does not change an Approved parent or frozen baseline.

## Normative controls

1. Stable requirement IDs; revision begins at 1 and advances for normative text/acceptance changes. Record before/after, reason, actor and actual UTC timestamp in append-only audit; retain revision snapshot or immutable version history. Informational parent/traceability edits can be independently audited without automatically changing requirement wording revision.
2. Each requirement has a product owner record, with optional `applicability` to other products. A child requirement may have **multiple valid direct parents**, with derived depth and no missing IDs or cycles. Use `traceability` for other typed relationships (`Depends On`, `Related To`, `Actor Participates In Use Case`, etc.); these never imply parenthood.
3. Separate lifecycle statuses Draft, In Review, Approved, Rejected, Superseded, Retired from verification results PASS/FAIL/NOT VERIFIED/BLOCKED. Do not imply Approved means implemented, or PASS means current release qualified.
4. Frozen baselines contain exact authorized requirement ID + revision + normative wording + criteria snapshots. Freeze only after explicit Product Owner authorization, verifying actual approval and integrity; never edit Frozen snapshots, even when a storage backend is weak. Create a successor baseline for changes. Do not rewrite other baselines/statuses as a side effect.
5. `Test Cases` describe reproducible setup/procedure and expected outcome, separate from concise acceptance criteria. A test execution or verification run records actual configuration/build, result, coverage, maturity stage (if defined by workspace), dated evidence and provenance. PASS requires real evidence; missing or partial scope is NOT VERIFIED/BLOCKED or explicitly partial, never fabricated PASS.
6. Use definitions of any engineering maturity level only if the workspace supplies them. Discovery Level 1/2 and requirement hierarchy depth are unrelated. Do not invent numerical acceptance thresholds, certification, regulatory compliance, tested hardware or authorized decisions.
7. Compare deployed products against existing implementation first; propose only real gaps or missing evidence. Respect a user's own policy if more restrictive, without weakening evidence or frozen-history protections.

## Transactions / review / reporting

For writes: identify exact affected IDs/revisions and data constraints; obtain the necessary authority for the normative/approval action; write record, revision snapshot, links and audit consistently; read back and validate unrelated frozen sentinels. SQLite uses transactions, Sheets uses bounded atomic batch updates where possible, CSV uses staged checked replacements and backup. If the write cannot be performed safely, show a draft instead of claiming it was saved.

For audits: join requirement IDs and exact revisions to `baseline_items`, `test_cases`, `test_executions`, `verification` and typed links. Report what is approved vs implemented vs actually verified, scope limitations, changes saved and only owner decisions still needed.

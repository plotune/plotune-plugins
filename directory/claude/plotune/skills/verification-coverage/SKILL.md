---
name: verification-coverage
description: Analyze coverage of existing requirements and exact revisions through test-case definitions, test executions, verification runs, maturity evidence and release baselines; identify legitimate gaps without inventing PASS.
---

# Verification coverage and evidence validity

Coverage analysis is **read-only by default** and can run alongside requirements review or implementation. Join the user's actual canonical records; report the reviewed scope, revision set, selected baseline and mapping rules so totals can be reproduced.

## Distinct layers

1. Requirement in scope: exact ID and revision from live record or selected Frozen `baseline_items` snapshot; preserve statuses and historical revisions. A baseline inclusion does not prove implementation.
2. Test design coverage: does a real `test_case` or equivalent traceability edge address this ID/revision and its acceptance outcomes? Separate `No linked case`, `Cases linked`, and `Cases incomplete/unknown`.
3. Execution evidence: actual `test_executions`, `verification_runs`, or `verification` with exact revision, tested configuration, method, result, coverage, dated artifacts and provenance; a test case definition or PR is not a run.
4. Applicability of PASS: verify evidence exists, stated acceptance was completely covered (or scope is explicitly partial), test environment/maturity is suitable for the claimed decision and required cases actually passed. A historical PASS remains historical fact even if no longer sufficient for the current revision.
5. Qualification claim: component/model/integration/representative system/operational/release maturity are distinct and must match the **user's actual documented model**. Do not invent L1–L6 definitions, transpose ASPICE capability levels or silently treat higher-level PASS as covering every lower-level criterion.

For each requirement report `No case / Defined, not exercised / Partial evidence / FAIL or BLOCKED / Evidence-supported at stated scope / Unknown`. Provide counts by exact denominator and links to missing artifacts, target levels and reviewers. A read-only heuristic can flag possible evidence gaps but must not write `FAIL`, `NOT VERIFIED` or overwrite previous PASS without authorized record review. When acceptance changed, investigate reuse vs re-verification rather than blanket clearing legacy evidence.

Run the packaged `scripts/review.py` for deterministic **structural** analysis on accessible local SQLite/CSV if helpful; its output is advisory and not a standards assessment. With RMS/Sheets use available connector reads and the same conceptual joins. Persist authorized findings and test corrections through `requirements-governance` with audit. Do not fabricate tests, coverage ratios, tools, executed dates or certificate status.

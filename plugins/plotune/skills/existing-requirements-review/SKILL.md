---
name: existing-requirements-review
description: Audit an existing user-owned requirement set against evidence-based requirements quality, consistency, source/traceability integrity and relevant project Guide. Return review findings with real IDs/revisions; persist only when authorized.
---

# Existing requirements: review and improvement

Use whenever an engineer asks to improve, assess, refactor, compare or review inherited requirements, including frozen baselines, rather than starting discovery again. Compose `workspace-management`, `requirements-governance`, `change-impact` and `verification-coverage` as relevant. The authoritative requirement texts, review policies and applicable engineering standard editions come from the **user's** project, not bundled demo content.

## Start from the existing truth

1. Read active user's accessible workspace and local Guide, baseline membership, source evidence, revision history, system boundary, product applicability and meaningful Actor/Use Case records. Inventory actual IDs/revisions, including unapproved items. If unavailable, review supplied documents as unsaved drafts; don't pretend imported data or persistence exists.
2. Review **without editing** by default. Sample or analyze as many real items as useful; include coverage (all or exact subset) and limitations. Preserve existing IDs and revision text. Do not rewrite frozen snapshots or demote substantiated historical PASS.
3. Use ISO/IEC/IEEE 29148 principles and the user's actual Guide. Assess each requirement for a clear obligation, unambiguous subject, feasible and verifiable outcome, boundaries/conditions, trace to stakeholder need or authoritative design/constraint, consistent acceptance criteria, and potential overlaps/conflicts. A single sentence is a helpful default, **not an automatic rejection**; structured acceptance criteria and domain-specific conventions may be legitimate.
4. Compare across requirements: contradictory limits, duplicate obligations, scope/applicability conflicts, parent-refinement quality, wrong/invalid parent links, missing but material Actor/Use Case scenarios, missing interfaces and orphan trace links. Run system-level coverage and trace analysis before asserting a record is truly missing.
5. For safety-related candidates, use `automotive-profiles` when the standard is in the project's approved profile; do not infer ASIL or demand HARA for every non-safety requirement.

## Review result: evidence, not a guessed quality score

Each actionable finding must identify original `record_type`, `record_id`, exact revision if available, check ID, specific quoted/paraphrased problem, evidence/source, practical risk, proposed improvement, severity and confidence (grounded; don't fabricate) and suggested owner/decision. Distinguish `Defect` (supported contradiction or broken link), `Review candidate` (plausible ambiguity or missing coverage), and `Unknown` (insufficient source). A semantic check by LLM is a **review suggestion**, not certification or a measured conformity pass. No generic bulk rejection or automatic numeric “compliance %” without declared denominator and rules.

A finding remains reviewable through `Open → Under Review → Accepted/Rejected → Resolved → Closed` or the user's mapped lifecycle. Don't open duplicate findings for same record/revision/check without comparing existing ones; recheck when the requirement revision or related evidence changes. If a proposed remedy changes normative text or tests, route it via `change-impact` and owner decision; never auto-revise a Frozen baseline.

`review_findings` and `change_requests` are independently auditable. `review_findings.change_request_id` connects an accepted concern to a controlled change; `change_impacts` retains the revision-specific effect network. If the user's backend cannot store these records yet, deliver a portable review package and explain the required explicit migration rather than silently creating a competing database.

When an inherited requirement is too broad to verify or leaves an actual necessary lower-level obligation undefined, use `requirement-decomposition` to propose child candidates. A read-only audit reports unsaved proposals; authorized writable engineering may persist `Draft` children without individual approval, but may not approve them or mutate Frozen snapshots.

## Work with real subagents

For large existing sets delegate bounded independent partitions (quality, interfaces, traceability, safety gaps, verification coverage) through `work-orchestration` only if real host delegation exists. Supply correct skill instructions, workspace scope, exact source snapshot and record ownership. Reconcile duplicates and conflicts centrally; no subagent may self-approve a requirement or assessment.

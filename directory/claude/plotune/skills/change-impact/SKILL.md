---
name: change-impact
description: Analyze, record and track controlled change requests across existing requirement revisions, Actors, Use Cases, tests, verification evidence, design artifacts and baselines; recommend impacts without unauthorized approvals or rewrites.
---

# Controlled changes and impact analysis

A request to “change this requirement” first means understand the current authoritative record and its effect. Work against the user's chosen canonical store and Guide; preserve existing decision rights, immutable evidence and Frozen baselines. A user can request read-only analysis, draft a change request or authorize a precise edit independently.

## Impact discovery

1. Capture change driver and exact affected requirement IDs/revisions, current lifecycle, approval, release/baseline context, source and requested outcome. If the request starts from a finding, link that actual finding ID. If specific revision is missing, resolve it from live records, never guess.
2. Traverse requirement parent/child DAG **both directions**, relevant typed traceability edges, Actors and Use Cases, interfaces, external architecture/safety artifacts, tests, implemented components/PRs and exact `baseline_items`. Identify upstream obligations, dependent requirements, applicable products, and downstream acceptance/test impacts. Inspect both direct and plausible transitive effects, labeling each as confirmed, candidate or unknown.
3. Check normative text change, acceptance criteria, target revisions, re-approval, baseline successor/release needs, existing verification evidence's applicability, safety impact and potential ASPICE process work products. A changed requirement revision does **not** automatically invalidate every historical PASS; mark evidence against its original revision, and assess whether it covers the new revision.
4. Return a reviewable diff/alternative with effort/risk tradeoff, precise change impacts, evidence gaps, affected owner decisions and safe implementation order. Distinguish reversible draft proposals from approved obligations.

## Durable records

- `change_requests` records who asked, why, current status, proposed alteration, summarized verification/safety impacts, owner, evidence and explicit decision. Typical lifecycle: Proposed → Under Analysis → Awaiting Decision → Approved or Rejected; when Approved, Implementing → Verification Pending → Closed. Cancellation can happen with reason. Mapping to customer's own lifecycle is valid.
- `change_impacts` records one impacted target per row with exact revision when a requirement is involved, impact kind, specific reason, evidence, disposition, owner. Do not flatten many impacts into a comma-separated string or reinterpret non-hierarchical links as parents.
- `review_findings` can link to a `change_request` via exact ID; `traceability` can connect change records to other supported artifacts. Audit substantive state/decision edits with actual actors and timestamps.
- Approval means the **appropriate delegated owner actually authorized a specific decision**; it is not inferred from a task completion, agent suggestion, status label alone or the word “continue.” Safety, budget, scope and release authorities remain distinct when the project's policy assigns them.

## Apply and reconcile

Only after explicit authorized scope: update the correct requirement revision, append immutable prior revision and audit, modify necessary typed links/tests, and read back. Freeze a successor baseline only with separate explicit baseline authorization. If a delivery agent works on an earlier frozen snapshot while newer Drafts exist, leave the ongoing approved work untouched unless the impact analysis proves a blocking interface/safety conflict; propagate scoped changes through `work-orchestration` with real tools.

Do not close a change merely because the requirement text was edited. Identify required work and re-verification, retain `Verification Pending` until real evidence is accepted; `Closed` requires documented disposition for all material impacts and required owner sign-offs. Without writable authority, return a proposed change record (not “saved”).

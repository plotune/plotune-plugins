# Continuous Requirements Engineering: review/impact/coverage acceptance tests

These checks are our original review heuristics based on systems engineering practice, **not copyrighted clauses or an assessor's determination**. Read the project's own Guide, selected standards editions and approved tailoring first. Automated structure checks below should be supplemented by semantic engineer review.

## Review checks

- RQ-01: Requirement and acceptance statement exist and have a reproducible interpretation. Empty/placeholder is a structural gap; subjective words alone are a *candidate* ambiguity to inspect in context.
- RQ-02: Exact source need, design decision or operating constraint is found or the source is explicitly unknown; don't invent a stakeholder.
- RQ-03: Wording and acceptance do not contain unreviewed contradictory limits, conditions or implied obligations; inspect neighboring requirements and baseline scope.
- RQ-04: Parent IDs exist, DAG has no cycle, and child actually refines a parent obligation; dependency stays typed non-hierarchical link.
- RQ-05: Relevant Actors and Use Cases explain significant operational outcomes and failure/recovery behavior; never insist on an Actor for every single requirement.
- RQ-06: Type/direction of links and referenced IDs are valid; preserve existing hierarchy and traceability when imported.
- RQ-07: Duplicate-like obligations and conflicting product applicability are flagged as candidates with evidence, not silently merged.
- RQ-08: Safety-related review checks apply only after real safety scope and project-specific ISO 26262 tailoring are established.

## Change and coverage checks

- CH-01: Target original ID and revision, proposed change, originating finding, source, owner and decision history are distinguishable.
- CH-02: Impact record covers upstream/downstream requirement graph, target revisions, product scope, design, tests, external safety artifacts and relevant frozen baselines.
- CH-03: Owner decision is separate from change implementation, test result and baseline freeze; closure retains material impact dispositions.
- VC-01: Coverage denominator is the chosen live revision or exact Frozen baseline; show unknowns and exemptions explicitly.
- VC-02: Test definition is not execution; PASS has real evidence and appropriate coverage/maturity for the claimed outcome; failure and partial are not hidden.
- VC-03: Historical PASS persists on its original revision; applicability to changed revision must be reviewed and may trigger retest.

## Workflow regression examples

1. **Inherited OBC requirement set:** connect a populated user-owned workspace, read actual ID/revision/Guide, surface actionable 29148-quality findings with evidence, no automatic writes.
2. **Changed AC input behavior:** impact traversal identifies multiple parent/child and typed links, existing baseline snapshots, affected test case revision(s), and unresolved review ownership; proposal not automatically approved.
3. **Existing evidence:** a historical PASS on req rev 1 with substantiated evidence remains available; req rev 2 without matching evidence cannot be labeled verified.
4. **Mixed agent work:** ongoing implementation against an approved Frozen baseline does not stop concurrent Draft/impact reviews, and stale revisions are flagged when results return.
5. **Automotive:** the project's verified ASPICE/ISO 26262 editions and tailoring are used; neither ASIL nor ASPICE capability scores are inferred. Safety work products may stay linked in external ALM systems.
6. **Legacy migration:** 1.0.0 to 1.1.0 is additive, explicit, backed up, and does not modify historical requirement records. No private maintainer Sheet URL or proprietary project model leaks into templates or skills.

## Draft decomposition and separation checks

- RD-01: An authorized writer may add a necessary previously absent child as `Draft rev 1`, with checked parent IDs, rationale/criteria, revision history and audit. No per-Draft owner gate for the writing action. Read-only access stays read-only.
- RD-02: Follow a requirement hierarchy only while obligations need independent, observable and verifiable refinement. A leaf may already be atomic; no fixed maximum/minimum depth and no coding/test-step clutter.
- RD-03: Creating Draft children does not modify an Approved parent, change current Frozen baseline items or implicitly authorize expanded implementation scope.
- RD-04: Draft author and its independent reviewer/approver are distinct; project-approved delegated authority must be explicit and auditable for the exact revision. The lead/subagent relationship alone grants no approval.
- RD-05: `Superseded` means a different successor obligation, while a normative edit of the same ID creates a new Draft revision. `Rejected` and `Retired` are controlled distinct dispositions.
- RD-06: Parent DAG permits multi-parent genuine refinement, while non-hierarchical dependencies belong in typed links; no automatic Parent Approved ⇒ Child Approved, or Child PASS ⇒ Parent PASS.

## Additional deterministic guards (offline regression)

- VC-04: Never report an unknown product or baseline as an empty but successfully reviewed coverage set. The local analyzer raises an explicit error.
- VC-05: `PASS` with only a narrative and no linked evidence artifact remains a recorded historical claim, not a completed verification verdict; no default `Verified` assertion is generated.
- BL-01: Frozen baseline items remain immutable. When a frozen snapshot and the live requirement share **the same revision**, any mismatched wording or criteria indicates a broken revision invariant and is reported by the validator. An older frozen revision differing from the current newer revision is normal.
- OR-01: Delegated packet preflight checks workspace identity, task ownership, scoped exact revision and optional frozen baseline membership; distinct tasks can share one session ID. It never provides runtime delegation or authorization on its own.
- BX-01: Synthetic SQLite/CSV OBC record sets yield the same quality, coverage, graph impact and handoff preflight outputs; blank Google Sheets/SQLite/CSV column layouts match the current data contract.

Re-run `python -m unittest discover -s tests -v` after package/schema changes. These are **structural integration tests**, not live Google Sheets/RMS/DOORS/Polarion/Jama connectivity, hosted subagent execution or an ISO 26262/Automotive SPICE conformity assessment.

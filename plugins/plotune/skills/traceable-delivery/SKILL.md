---
name: traceable-delivery
description: Ensure authorized engineering tasks, PRs and test activities are tied to exact user-owned requirement IDs/revisions, with truthful verification evidence and handoff records.
---

# Portable traceable delivery contract

Use `workspace-management` before governed work. The **selected user's** bound workspace is authoritative; repository Markdown may contain generated read-only snapshots, summaries or links but does not become a competing writeable source by default. Never assume a particular Sheet, GitHub organization or product.

- Every actual lead task, issue and PR should identify the scoped requirement **ID and exact revision** from the live store or frozen snapshot. A link expresses intended trace/coverage, not PASS.
- Keep each top-level agent session's task distinct. Subagents report to the lead; they do not create duplicate ownership rows. Claim/reconcile using actual supported integrations and identifiable session state; do not invent agents, tests, dates or tool actions.
- Record work progress truthfully. `Review` means an artifact awaits review, not qualified. `Done` means the authorized goal is complete, evidence/checkpoints saved, no required work pending.
- Before accepting delegated work, inspect relevant open Change Requests and unresolved Review Findings against the task’s exact requirement revisions. Keep test case, execution/run and verification evidence distinct. For each actually executed test, persist requirement ID+revision, tested configuration/build, method, result, scope/coverage, stage/maturity definition if configured, date, actor and immutable or retrievable artifact link. Physical/operational tests are not substitutes for code tests, nor vice versa.
- If something was not exercised, record NOT VERIFIED or BLOCKED, not PASS. A PR review, merge or simulation cannot independently qualify physical system behavior; a Frozen baseline is not test evidence.
- Preserve Frozen baseline snapshots, accepted normative text and version history; create successor Draft baseline for changed scope. Keep product version, requirement revision and baseline ID separate.
- Use exact mappings such as `Verifies: <requirement-id> rev <n>` at the end of an applicable board/PR report (actual IDs only). Their presence does not imply test PASS.

## Concurrent discovery and engineering

An implementation task may consume an explicitly authorized frozen baseline or exact requirement revision snapshot while the same conversation continues newer draft/discovery work. Keep those contexts distinct. On delegated output/PR review, re-read live revisions and baseline state before integration; changed requirements are an impact-analysis trigger, not permission to rewrite history or assert tests still apply. Coordinate file/record ownership and capabilities using `work-orchestration`. Multiple tasks may belong to one parent session; statuses and evidence are tracked by task, not by chat.

On discovering a genuine missing lower-level requirement needed for delivery, compose `requirement-decomposition` and save an auditable `Draft` child when your actual project/delegation permits Draft writing; do not wait for a separate user decision on the act of drafting. Keep implementation authorized scope, acceptance evidence, parent ID+revision, and child Draft separated. The author cannot approve their own revision, and the new Draft does not retroactively alter the Frozen baseline or automatically authorize extra implementation. Lead and reviewer reconcile before including children in future approved scope.

Workflow: resolve authorized scope → identify or claim the **correct scoped task** → audit implementation → execute bounded work and tests → persist trace links and real evidence → reconcile potential newer requirement revisions → read back → report deliverables, unresolved gaps, decisions and verification limitations. Do not merge/release without appropriate user policy/permission.

When receiving delegated work, load the bounded rules named in the task packet and re-check the exact authorized revision/baseline before editing. Where available, use the local read-only `scripts/handoff.py` preflight or equivalent connected RMS/Sheet checks. If it reports `CONFLICT`, stop affected writes and return the conflict to the lead; a previous PASS or an inherited packet is not authorization to merge.

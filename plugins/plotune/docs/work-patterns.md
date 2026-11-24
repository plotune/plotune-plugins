# Multi-workstream orchestration and acceptance scenarios

These are behavioral examples, not mandatory workflow stages or customer workspaces. The selected canonical store and governing project Guide always override example names and statuses. Native agents, background workers and integrations must exist before claiming they run.

## OBC: one conversation, several simultaneous outcomes

1. User: "I want an OBC for a target vehicle segment." Agent explores an opportunity without insisting on requirements tables or creating Tasks automatically.
2. User: "Develop Actors, Use Cases and system requirements; save the Drafts in my existing workspace." Agent resolves the user's canonical backend, reads its Guide and schema, drafts and persists authorized records with trace links and actual audit. User-selected product decisions remain explicit.
3. User: "Delegate the already-approved charging-status interface to an implementation agent. Meanwhile we keep refining the AC fault-recovery requirements." Agent checks whether native agents are supported. The delivery task is scoped to the exact approved requirement revision/baseline and owned files, with a reviewable task brief and evidence expectations. The fault-recovery Draft evolves independently in the same conversation.
4. While delegated work is underway (if host supports it), new requirement insights and review findings enter the workspace as Draft/review proposals, not silent edits to Frozen snapshots. Task status is per deliverable, not per conversation.
5. When the delegated artifact returns, parent checks current requirement revision, test evidence, conflict status and owner approval; it does not assert PASS based on a PR or model response.

## Existing OBC project and changed requirements

A requirement engineer connects a populated user-owned workspace, asks for a quality audit and impact analysis. Agent first reviews actual IDs, source, Actors/Use Cases, baseline and test records; produces evidence-tied findings without overwriting anything. It may separate quality review and traceability analysis for independent native workers. A suggested change affecting existing implementation triggers a separately tracked change/approval decision and scoped re-verification, not immediate destructive update.

## Derive Draft children while engineering continues

A lead works on an approved requirement while an assignee implements an earlier frozen revision. A design review uncovers two distinct unrepresented interface/fault obligations. With authorized Draft-write rights, the writer saves each as new `Draft rev 1` with parent ID/revision context, real rationale, acceptance candidates and audit; the assignee continues approved scope independently. A separate reviewer checks consistency and testability; a higher agent may approve only if the user has explicitly delegated that specific scope and the higher agent did not write/revise the candidate. Otherwise the owner decides in the next batch. Neither child becomes part of the existing frozen baseline automatically. Continue decomposition recursively only if another necessary independently verifiable obligation exists.

## Regression expectations

- **Several goals in one session:** Agent retains independent task identities and progress; does not force a new chat or reuse a single task row for unrelated outcomes.
- **Subagent with no inherited context:** Delegation packet includes relevant plugin skill/Guide scope, requirement IDs/revisions, baseline snapshot, decisions, permissions, artifacts and expected return. Missing host subagent capability is disclosed and never faked.
- **Parallel requirement revision:** Draft revision updates do not alter a frozen delivery baseline. A stale delegated revision is flagged and impact-reviewed at integration.
- **One blocked task:** A deferred test or procurement blocks dependent tasks only; independent quality analysis continues.
- **Out-of-scope authority:** No inferred freeze/approval/merge/physical verification from user saying "continue" or from a subagent report.
- **Cross-backend:** All references resolve to the **user's** RMS/Sheet/SQLite/CSV; no maintainer URLs, product IDs, secrets or prebound private project are embedded.
- **Session handoff:** Lead can resume task IDs and current authorized scope from a durable record when supported; otherwise reports non-persistence honestly.
- **No background host support:** Agent completes bounded analysis now and returns task packets, not imaginary ongoing work.

## Continuous Engineering: multiple living decisions

If a field test of an existing OBC req rev 2 reveals an under-voltage issue, the engineer can request a review finding, a change proposal and parallel verification-gap assessment while another agent implements the frozen rev 1 scope. Each workstream retains its own record ID, exact source revision, owner and delegated write permission. The parent checks the proposed change's safety/requirements/test/baseline impacts before accepting it; the old PASS remains historical rev 1 evidence, never automatically rev 2 qualification.

Use `docs/continuous-checks.md` for testable RQ/CH/VC review expectations and `docs/schema-upgrade.md` for safe persistence activation.

## Structured, bounded delegation packet (optional interoperability aid)

Use `schema/delegation-packet.schema.json` with a user-owned packet created for the actual task. `examples/sample-handoff.json` contains invented demo identifiers and is not an authorization. It conveys exact requirement revisions and optional Frozen baseline IDs, relevant skill paths and Guide, permissions limited to the actual owner authorization, record/file ownership and expected evidence. The packet is **not** an agent launcher or an approval token.

A user can ask for a firmware implementation against Frozen rev 1 and simultaneously continue drafting rev 2 in the same conversation. Create two separate task IDs, potentially sharing one session ID. For local workspaces, the read-only preflight reports `FROZEN_SNAPSHOT_ONLY` for the first and `LIVE_MATCH` for the second. If the frozen revision cannot be verified, or a task ID belongs to another session, do not send the assignment or merge results blindly.

Never claim a long-running task continues after the response unless the host actually exposes persistent worker/scheduler controls. With only sequential execution, do the work that fits now or prepare a task packet and report the limitation.

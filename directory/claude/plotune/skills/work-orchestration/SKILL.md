---
name: work-orchestration
description: Coordinate several requirements, discovery, change, review, verification and authorized engineering goals within one conversation or project. Delegate scoped work to real native subagents where supported, preserve authoritative revisions and owner decisions, and integrate results without stopping unrelated work.
---

# Continuous requirements and multi-workstream orchestration

Use for a user asking for multiple outcomes, continuing requirements while implementation/review occurs, handing work to subagents, or revisiting earlier work later in a long session. This skill **composes** `idea-to-requirements`, `workspace-management`, `requirements-governance`, `lead-task-tracking`, `traceable-delivery`, `existing-requirements-review`, `change-impact`, `verification-coverage`, `automotive-profiles` and any available project-specific methods; it does not replace them or impose a new approval bureaucracy.

## Mental model (not mandatory UI)

- **Workspace/product** = user-owned authoritative project and engineering records. One canonical write store for a workspace, even if the product spans several repositories.
- **Conversation/session** = coordination context; may include several products, workstreams and deliverables. Do not mistake the chat for durable task history.
- **Workstream** = ongoing intent such as OBC discovery, evolving requirements, review of an inherited baseline, or implementation of an authorized subset. More than one may be active in one session.
- **Task/work item** = independently trackable finite outcome, with its own owner, scope, authorization, dependencies, evidence and status. A session/run ID is **not** a unique task key. Use multiple task IDs for multiple concurrent goals, even when initiated in one session. Do not create one task per chat message or every subagent micro-step.
- **Subagent** = execution resource, not a new requirement authority. Its own tool/runtime decides whether spawning, parallelism and persistent background work are actually possible.

## Interpret mixed requests naturally

When a user says, for example, "develop the idea, turn it into requirements, delegate authorized implementation while we keep refining the requirements":
1. Resolve the current decisions and user-owned workspace without forgetting previously agreed options. Classify each requested outcome by permissions and current available evidence, not as exclusive session modes.
2. Run **independent workstreams** as far as tool capabilities permit: explore/draft new revisions and use cases while checking, implementing or testing an already-authorized baseline subset. Do not require discovery to finish or every requirement to freeze before other approved scoped work proceeds.
3. Bound what is safe to work on now. Exploration and read-only reviews can normally proceed; creation of records requires permitted durable storage; normative approval, Frozen baseline, safety/funding decisions, hazardous test, merge/release or other owner-controlled actions need the appropriate explicit authority. An authorized limited prototype is not a claim that all product requirements are Approved.
4. If the user changes scope midstream, identify dependent work only, notify/stop affected delegated work through actual host controls where possible, and leave independent tasks running. Do not silently restart a paused project or fabricate a cancellation.
5. Keep conversation with the user focused on the next useful design/requirement question rather than repeating the full task board. Summarize active work and actual outputs briefly at meaningful checkpoints.

## Concurrent Draft refinement and delegated approval

Whenever a lead or assignee discovers a missing lower-level obligation needed to deliver a parent requirement, compose `requirement-decomposition`. If the assignee has bounded Draft-write authority, create the child `Draft` without waiting for a user gate. Keep parent/child exact revisions distinct from the frozen delivery scope. The author cannot approve their own Draft; the parent/lead agent may conduct an independent review and approve **only** with explicitly documented delegated authority, and only if it did not author/revise the same candidate. Otherwise escalate the decisions in a compact batch to the authorized owner. A new child does not automatically expand an already authorized implementation task or Frozen baseline.

## Capability-aware delegation

- Check the host's **real** subagent/delegation capability and available tools before claiming any work was delegated. If unavailable, perform the bounded tasks directly/sequentially, provide copyable task briefs, or state the limitation. Never invent a worker, queue, callback, poll result, persistent process, remote edit, schedule or parallel execution.
- Delegate on independent bounded outcomes and file/record ownership, not one agent per requirement. Useful partitions: requirement quality audit, interface analysis, safety-gap review, traceability/verification coverage, change-impact mapping, firmware/software implementation, independent tests. Assign write authority and target finding/change IDs as well as exact source revisions; avoid several agents accepting or closing the same finding simultaneously. Avoid overlapping unsynchronized writers.
- Provide the assignee **the relevant plugin method and workspace policies**, not just the user's raw text. Since a subagent may not inherit parent skill text, include actual skill names/paths or copied bounded rules it can access; instruct it to load those skills if supported. Do not rely on an implicit context inheritance.
- A delegated task packet must identify: (a) work/task ID and parent context; (b) product/system boundary; (c) exact canonical workspace and access limitations, without leaking credentials; (d) precise requirement IDs+revisions, approved/frozen snapshot if applicable, source links and last checked state; (e) objective, deliverables and exclusions; (f) recorded owner decisions/assumptions and decision limits; (g) allowed tools, edit ownership, branch/files/records, verification/evidence expectations; (h) dependencies, checkpoints and result/return format.
- For a repeatable handoff, follow `schema/delegation-packet.schema.json`; `examples/sample-handoff.json` is **synthetic** and must never be sent unchanged to a real assignee. For accessible local SQLite/CSV workspaces, run `python scripts/handoff.py --packet <authorized-task.json> --backend sqlite|csv --path <workspace>` as a read-only preflight. For RMS/Sheets, re-check the same fields using actual connected tools. The packet is a **brief, not a permission grant**. A `valid` preflight does not prove a subagent exists or that owner authorization was granted. Do not include access tokens or private credentials.
- A packet can name a **Frozen** requirement revision even when the current live requirement has advanced. The preflight distinguishes `LIVE_MATCH`, `FROZEN_SNAPSHOT_ONLY`, and `CONFLICT`; only the authorized frozen scope may continue without reinterpreting newer requirements. At return, repeat live revision and baseline checks before integration.
- Assign no broader permission than the user gave. The lead retains integration and approval accountability. Subagents must return actual changes, source evidence, affected IDs/revisions, tests attempted and observed, unresolved issues, and stale-base/conflict warnings. They do not self-approve, freeze, invent compliance, report PASS without evidence or silently merge/release.

## Parallelism and safe integration

- Work against a **specific frozen baseline or exact requirement revision snapshot** for delivery, while permitting separate Draft/next-revision work. Never mutate Frozen baseline items when new drafts appear.
- Prefer disjoint records/files, independent branches/worktrees where the host supports them, and one responsible writer for each shared normative record. Do not let two agents independently advance the same requirement revision or write competing canonical stores. When concurrency controls exist, use version checks/transactions; otherwise serialize writes and read back.
- At handoff or merge, re-read the live requirement ID+revision, task state and baseline. If they changed since delegation, treat results as potentially stale: perform impact analysis, reconcile and get required decisions before accepting the result. A matching ID with a different revision is not sufficient.
- Engineering results can expose a new requirement need or conflict. Register it as a finding/change proposal with source, scope and rationale, then route it to the appropriate owner review. Do not quietly rewrite the original approved requirement to make a test pass.
- Record task/delegation links in the user's supported canonical system when authorized. With the portable data contract, `tasks` can hold **multiple distinct task IDs per session**; `traceability` may record typed task-to-requirement or task-to-task links where the workspace supports that endpoint type. Keep more detailed handoff briefs in authorized artifacts and record their links. No new mandatory field or table is required merely to support multiple tracks.
- On interruption/resumption, recover active task IDs, decisions, exact revisions, artifact links, permission limits, blockers and branch ownership from the user-owned store. If checkpoints are unavailable, explain the gap instead of asserting work continues in the background.

## Output contract

Provide real deliverables first. When multiple tasks are active, a compact "working on / delivered / blocked / needs owner" summary with task IDs and links is enough; don't produce a huge status ceremony. Distinguish proposed vs saved vs approved vs implemented vs verified vs released. A host may only execute during the current turn: without genuine persistent workers or scheduling, don't promise activity after the reply.

See `docs/work-patterns.md` for example mixed-session flows and regression scenarios.

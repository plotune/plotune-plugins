---
name: lead-task-tracking
description: Track multiple independently scoped workstreams and authorized engineering tasks in a single conversation or across sessions, with real ownership, handoff checkpoints, requirement revisions and evidence.
---

# Multiple work items, one authoritative workspace

Use the user's canonical `tasks` records or mapped existing task board as resolved through `workspace-management`. Never hardcode a workbook, URL, agent identity or task ID. This is a **work-item** register, not a 1:1 index of chats.

## Identity and ownership

- One task ID per **independently trackable goal/deliverable**, not one task ID per session/run or chat turn. A single session may own several active tasks (e.g. evolve OBC requirements, audit an existing baseline, implement an authorized isolated component). Multiple sessions can also own different tasks for the same project.
- Resume by verified task ID and objective/product/owner, not by session ID alone; the same session may have multiple matches. Find existing scoped tasks before creating; don't duplicate or hijack work belonging to another lead.
- Keep real session/run identity when available, otherwise leave it unknown. Each task includes exact requirement IDs **and revisions** in linked details or a referenced handoff artifact; a bare IDs-only column is insufficient for governed delivery. Record actual UTC timestamps; don't invent model/session identity.
- Parent lead owns integration and authoritative task state. For native subagents, use host-specific child task machinery if available; optionally represent material delegated outcomes as separate owned tasks with distinct IDs and explicit parent/dependency links, but **never** create an independent competing lead owner or a row per micro-step. The canonical lead writes task status after validating handoff; subagents return results and evidence.

## Task state

Statuses: Backlog, Running, Blocked, Review, Done, Cancelled, or explicitly mapped equivalents. Track meaningful progress, evidence and links; no routine heartbeat noise. `Blocked` names the precise dependency; do not block unrelated tasks. `Review` means real review-ready output, not evidence PASS. `Done` requires the scoped definition of done, actual evidence/checkpoint and integration completed; opening a PR or saying a subagent worked is not Done. Reopen clears completed timestamp when supported.

For each meaningful handoff, retain: task ID, product, scope and revision snapshot, objective/exclusions, allowed authority, owner/assignee, dependencies, artifacts/branch, evidence/test observations, open decisions, next action, last actual update. Store details in the canonical task system if available, otherwise an authorized durable linked artifact; do not stuff sensitive context into plugin code. A task row without a link must still contain enough information to resume honestly.

## Session continuity

At every requested switch (idea → requirements → delivery → requirements again), keep the **relevant existing task IDs** and decisions. Start another task only for a different trackable outcome. Read back state before concurrent writes or accepting subagent output; reject stale requirement revisions and parallel conflicting edits until reconciled. Never silently approve/rebaseline/merge/release as a side effect of a task status change.

When support for durable task writes or native subagents is missing, continue accessible work directly and clearly distinguish a plan/brief from a running external job. A conversational turn does not itself create background execution.

A single session/run ID can validly own **several different top-level task IDs** for independently scoped work. Keep those IDs and allowed file/record ownership distinct; never use session ID as a primary task key. Persist a scoped handoff artifact link when an actual worker is assigned, and reconcile its return against the latest requirement revision before closing the task.

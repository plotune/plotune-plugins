# Plotune Requirements — Portable Skills and Workspace Templates

## Install

```
/plugin install plotune-requirements --marketplace plotune/plotune-plugins
```

Or see the [marketplace README](../../README.md) for Claude Code, Copilot CLI and Codex.

An open-compatible, standards-informed **continuous** product and requirements engineering workflow with capability-aware multi-workstream orchestration. This plugin is a method and a **blank** workspace starter; it contains no default customer/project authority and makes no claim of standards certification.

## Start

1. Discuss a new product idea naturally (`idea-to-requirements`), or request requirements discovery immediately.
2. Continue in Autopilot or switch to guided questions anytime.
3. For durable Level 2 work, choose/retain your own authoritative backend. If you already have Plotune RMS, a Google Sheet or a local workspace, the agent should discover that **within your authorized environment** rather than creating another.
4. When you need an empty workspace: use `templates/google-sheets/Plotune-Requirements-Blank.xlsx` (import as a new Google Sheet), `templates/sqlite/schema.sql` or `templates/csv/`. A CLI helper `scripts/workspace.py` supports offline SQLite/CSV initialization, validation and opt-in additive upgrades.
5. Store the selected backend location privately in `requirements-workspace.json`, using `templates/workspace.example.json` and `schema/workspace.schema.json`.
6. Resolve existing IDs/revisions/relationships before writes, and preserve one canonical backend per workspace. The plugin cannot connect an unconfigured RMS endpoint or provision Google access on its own.

Portable schema: `schema/data-model.json`. Semantics: `docs/data-contract.md`. Migration guide: `docs/migration.md` and `docs/schema-upgrade.md`. Continuous review rules: `docs/continuous-checks.md`.

CLI example:

```bash
python scripts/workspace.py init --backend sqlite --path ./requirements.db --workspace-id my-org-project
python scripts/workspace.py validate --backend sqlite --path ./requirements.db
python scripts/workspace.py init --backend csv --path ./requirements-csv --workspace-id my-org-project
python scripts/workspace.py validate --backend csv --path ./requirements-csv
```

A new blank workspace contains no real requirements, approved decisions, tests or evidence. Scripts/skills do not launch background agents or turn Draft into Approved.

## Continuous work and delegation

A single conversation can coordinate new-product discovery, existing-requirement reviews, new Drafts, change proposals, verification audits and separately authorized engineering delivery. Use `skills/work-orchestration/SKILL.md` and `docs/work-patterns.md`: multiple independently trackable tasks may share one session. Native subagents receive scoped requirement revisions and selected rules only when real host delegation is available; no fabricated background workers or approvals.

## Continuous child requirements and approvals

When normal engineering work exposes missing subordinate obligations, compose `skills/requirement-decomposition/SKILL.md`. In an authorized writable workspace, new child requirements are created directly as auditable `Draft rev 1` with parent links, without stopping for per-Draft approval. Use independent reviewer/approver responsibility; a lead may approve only with an explicit bounded owner delegation and never a revision it authored. The hierarchy can deepen naturally until the requirements become individually verifiable; neither frozen scope nor a parent approval passes to the children. Read-only review stays read-only.

## Existing requirements and continuous review

Use the same plugin with an **existing** project: `existing-requirements-review`, `change-impact`, `verification-coverage` and optional `automotive-profiles` can run within one session alongside discovery or delivery. For a new 1.1.0 workspace the blank template contains 21 entity tables. The four new tables track review findings, change requests, revision-scoped impact records and selected standards profiles. The user must authorize normative changes, baseline freezes and persisted review/change edits separately from read-only analysis.

Read-only local CLI examples (no evidence/approval claims):

```bash
python scripts/review.py quality --backend sqlite --path ./requirements.db
python scripts/review.py coverage --backend sqlite --path ./requirements.db --product-id DEMO-PRODUCT
python scripts/review.py impact --backend sqlite --path ./requirements.db --requirement-id DEMO-REQ-001
```

For an **existing** 1.0.0 SQLite or CSV workspace, preview the additive upgrade before obtaining authorization; use `--apply` only with permission. The script creates and retains a timestamped backup. This never edits a pre-existing Google Sheet or RMS on its own:

```bash
python scripts/workspace.py migrate --backend sqlite --path ./requirements.db
python scripts/workspace.py migrate --backend sqlite --path ./requirements.db --apply
```

The bundled automotive profiles are optional original review methods, not a certification, process-capability assessment or redistribution of ISO/VDA copyrighted specifications. Use each project's actual standards editions and tailoring.

## Integration and delegation regression

`python -m unittest discover -s tests -v` exercises a **synthetic** OBC requirement set on local SQLite/CSV, verifies blank Google Sheets workbook headers, historical vs current revision evidence, frozen baseline integrity, graph impact, multi-task session ownership and stale-delegation rejection. No customer/private workspace is modified and these tests do not claim actual hosted subagent execution or remote ALM/API access.

To preflight a scoped **local** task packet, adapt `examples/sample-handoff.json` with real user-owned task/workspace IDs and actual permission boundaries, then run:

```bash
python scripts/handoff.py --packet ./my-task.json --backend sqlite --path ./requirements.db
```

`LIVE_MATCH` means the selected revision matches current requirements; `FROZEN_SNAPSHOT_ONLY` means the current revision advanced but the selected exact frozen item is still valid for the task. `CONFLICT` means the packet must be reconciled. Neither status grants approval or launches a worker. For Google Sheets and RMS, use authenticated connected tools to perform the same checks against the live source; the local script does not impersonate remote access.

---
name: idea-to-requirements
description: Explore a product idea with evidence-based autopilot proposals, then develop traceable needs, Actors, Use Cases and draft requirements when requested. Use guided conversation only if preferred; preserve decisions across modes.
---

# Product opportunity → Requirements discovery

## Level 1 — Opportunity discovery (default)

If the user shares a tentative idea, start with the **problem, broad customers, value, existing alternatives, market signals, feasibility, budget/resource envelope, risk and commercial direction**. Level 1 is intentionally not a detailed operational model. Do not demand Actor roles, technical Use Cases, interfaces, numerical acceptance criteria, test plans, authority matrices or a formal requirement baseline simply because a product idea was mentioned. Use sources for research when available; label Known / Hypothesis / Unknown, avoid fabricated citations or budgets.

**Autopilot is the default.** Independently analyze accessible information and deliver a compact batch of 2–4 coherent strategic propositions, each with grounded rationale, tradeoffs and Supported / Assumed / Unknown markers on material claims. Ask at most 1–3 substantive decisions per batch; often no question is needed. Do not turn the flow into a questionnaire. Do not announce a rigid workflow or insist on an arbitrary approval gate. No funding, safety-critical commitments, commercial promises or engineering execution without owner authority.

The user may switch between Autopilot and Guided Conversation **at any time**, including mid-session. Phrases such as "continue on your own", "autopilot", "sen devam et" or "research and bring a package" activate Autopilot. "Ask me", "birlikte gidelim" or "one at a time" activate Guided Conversation. Preserve accepted/rejected options, sources and assumptions; do not restart discovery or repeat questions already answered. In Guided mode ask at most one high-value unresolved question per turn. Interaction mode does not itself change discovery depth.

When the opportunity is developed enough, provide a short snapshot: problem, customer, value, supporting evidence, uncertainty, rough cost/resources, risks and recommended next investigation. Invite Level 2 when helpful, but do not silently convert ordinary Level 1 examples into normative `shall` requirements or cloud writes.

## Level 2 — Needs, operational model, draft requirements

Move here on a clear user request for requirements, Actor/Use Case analysis, interface or detailed specification; no magic phrase or second permission needed. If the user requested autopilot through requirements discovery, keep it active.

Build and maintain a **traceable network** (not a forced questionnaire) of stakeholder needs, human/non-human Actors, system boundary, operational Use Cases, goals, triggers, preconditions, main/alternate/failure flows where material, requirements, context/constraints, decision sources and verification proposals. Distinguish stakeholder, actor, role and owner authority; use functional names grounded in the system rather than generic "Human" placeholders. Capture `Actor Participates In Use Case`, `Use Case Motivates Requirement`, `Requirement Derives From Need` or other meaningful typed links in the user's workspace when authorized; don't invent them when unsupported. Requirement hierarchy refines normative obligations and may have multiple direct parents; use other link types for non-hierarchical dependencies.

Before formal normative authoring show a concise `Ready / Conditional / Blocked` view of source/needs, actors/use cases, boundary/constraints, feasibility and key unowned decisions. In the first Level 2 response provide a reviewable package of candidate needs/Actors/Use Cases, candidate requirements with rationale and indicative verification methods, and concrete evidence gaps. Work on unblocked portions rather than stopping at a plan. Unknown numerical limits/protocol decisions remain provisional, tagged with evidence and rationale, never silently authoritative.

An agent may research, estimate and propose technical numbers when justified by known constraints or external references. Owner decisions are for product scope, risk, safety, money and normative approval; reversible assumptions are acceptable for drafting. Approvals and verification PASS are never assumed. Defer only an activity actually blocked by a postponed purchase/test; continue independent design and research.

For ongoing Level 2 work or explicit save requests invoke `workspace-management`. Use the **current user's** already-selected store or initialize a permitted new one from packaged blank templates; never assume a maintainer's private Sheet. If no durable connected writable store exists, clearly distinguish the chat draft from saved records. One canonical store only; preserve exact IDs/revisions across later batches.

Use relevant **principles** of ISO/IEC/IEEE 29148:2018 for requirements quality and ISO/IEC/IEEE 15288:2023 for lifecycle/system context. ISO 56007:2023 can inform innovation opportunity validation. These are methodological references, not a claim of certification or a substitute for project-specific sources. Never invent clause texts, mandatory numbers or custom maturity scales.

For an **existing approved parent** discovered during ongoing design, test or implementation, use `requirement-decomposition` instead of restarting discovery: refine as needed into auditable lower-level `Draft` requirements; do not let writing Drafts imply approval. Recursion stops at independently verifiable obligations, not an arbitrary hierarchy depth.

## Coexistence with other ongoing work

A new idea, evolving draft requirements, reviews of inherited specifications and authorized delivery may coexist in one conversation. Do not force a reset when the user returns to discovery after delegating implementation. Keep accepted and rejected decisions, current requirement IDs and any baseline snapshot used by delivery separate; a new proposed revision is not an automatic rebaseline of existing engineering tasks. When multiple goals or native subagents are involved, compose `work-orchestration` rather than treating the entire conversation as only discovery.

## Continue after initial authoring

Once requirements exist, new ideas and lessons from design/test are handled as controlled review findings and proposed changes where applicable, not by restarting Level 1. Compose `existing-requirements-review`, `change-impact` and `verification-coverage` in the same conversation while ordinary requirements discovery continues; profile checks come from `automotive-profiles` only where pertinent.

## Boundaries

Opportunity ≠ Candidate requirement ≠ Approved ≠ Implemented ≠ Verified. Level 1/2 describes discovery depth, not a verification maturity scale. Autopilot means initiative *inside the active turn*, not an invisible background worker. Delegate only via actual available tools, and never claim remote writes or tests that were not executed.

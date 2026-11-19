---
name: requirements-cycle
description: Run a V-cycle delivery loop for a feature-level or system-level goal on a new or existing system. The main agent becomes the Orchestrator and routes work to Designer, Build and Verify roles until the goal closes or the user stops it. Not for single narrow requests such as verifying or writing one requirement.
---

# Requirements cycle: Orchestrator mode

The V-model is not summarised here. Three roles, **Designer**, **Build** and **Verify**, together hold its full responsibility; adding or removing helper agents never changes who is responsible. The agent the user talks to becomes the **Orchestrator** when this skill starts the loop. There is no separate orchestrator agent, and the user only ever talks to the Orchestrator. Compose `workspace-management`, `requirements-governance`, `requirement-decomposition`, `change-impact`, `verification-coverage` and `work-orchestration`; this skill adds the roles, lines of communication and loop rules and does not replace them.

## When the loop applies

- **Applies:** a feature-level or system-level goal, on a new system or on an existing one ("we are building X", "add support for Y to the existing system").
- **Does not apply:** a narrow single-role request ("verify requirement X", "write this requirement", "fix this bug"). Hand it directly to the one role, or do that role's work inline, and do not start the loop. Spawn a role only when its output changes the next decision; never use an agent for something one read call answers.
- **Capability:** check what the host really offers for subagents. If it offers none, run the roles as separate sequential passes; the rules below still hold. A pass cannot approve what the same pass authored, so such approvals go to the user. Never claim a role ran in the background.

## Phase 0: before the loop

1. **Read first.** Resolve the user's workspace through `workspace-management`. For an existing system read its products, baselines, requirements, Actors, Use Cases, open findings, test and verification state, and the code. Never ask the user what the workspace already says.
2. **Ask only the delta,** using `idea-to-requirements` for new ground. This phase is normal conversation; no loop, no records beyond what the user already authorised.
3. **Start only on the user's go-ahead** ("let's start" or equivalent). Then say once that Orchestrator mode is active, and record the goal, the scope (products and baselines the goal covers), the baseline to build against, and the approval authority the user delegated. Mode ends when the goal closes or the user stops it.

## The Orchestrator

It owns no V step. It authors no requirement text, code or test result. It keeps the loop state, applies lifecycle transitions that fall within the delegation (the author of a revision never approves it), builds delegation packets, relays and batches questions to the user, and reports. Approve happens only inside the delegation the user recorded; **freeze and release are the user's** unless the user delegates them explicitly.

## Roles and V steps (nine-step reference)

| # | Step | Owner | Others |
|---|---|---|---|
| 1 | Need and requirement analysis | Designer | Verify plans the acceptance test (9) |
| 2 | System design | Designer | Verify plans the system test (8) |
| 3 | Architecture design | Designer | Build reports technology and limits; Verify plans the integration test (7) |
| 4 | Module detail design | Build | Designer supplies limits and sub-requirements |
| 5 | Implementation | Build | Independent reviewer examines the result |
| 6 | Unit test | Build | Nothing is delivered until it passes; Build records its own PASS |
| 7 | Integration test | Build (software packages), Verify (hardware, firmware, device) | each records PASS for its own scope |
| 8 | System test | Verify | |
| 9 | Acceptance test | Verify | the user's help is needed most here |

- **Designer** writes sub-requirements, says how each will be verified, and finds the technology and limits that apply to the build. During the loop it inspects the lower levels of existing requirements, refines existing Actors and Use Cases and adds new ones. New obligations are `Draft rev 1` (see `requirement-decomposition`); existing approved text is revised, never edited in place. It has no helper agents.
- **Build** delivers. It decides itself whether to split work into packages and spawn its own helpers. The unit tests must pass before delivery. An **Independent reviewer** then examines the result with fresh context: it receives the exact requirement revisions and the artifact or diff, not the author's reasoning, and reviews in the form the artifact needs (code review for code, CAD review for CAD, and so on). It is read-only, its findings go to Build, Build fixes them, and Verify is told. Build may not mark its own work reviewed.
- **Verify** is the right side of the V. It reviews requirements independently, produces test cases for them and links them to users, Actors and Use Cases, end to end. It runs ready tests per maturity level and runs the Use Cases, including with test equipment, simulators and people. What is built may be firmware, an electronic board, a mechanical part or only a geometry; Verify manages that equipment and interaction. It records, per level, what passed, what failed and what could not be verified. It has no helper agents.
- Do not add other helper agents by default. The Independent reviewer is the only mandatory one.

Maturity levels come from the project's own process definition. This skill invents none.

## Who talks to whom

| Line | Carries |
|---|---|
| User ↔ Orchestrator | the only user channel |
| Orchestrator ↔ Designer | goal, scope, decisions; impact outside scope, goal drift |
| Orchestrator ↔ Verify | blockers, items that need the user (equipment, people) |
| Designer ↔ Build | sub-requirements and limits down; technology limits and requirement gaps up |
| Designer ↔ Verify | acceptance criteria and verification method down; testability findings, test cases for coverage review and failing-requirement packets across |
| Build ↔ Verify | the deliverable, unit evidence and reviewer result |

Build has no direct line to the Orchestrator; its blockers go to Designer or Verify, who forward them. Subagents never ask the user anything. A subagent that is stuck returns a blocker with its question, and the Orchestrator batches questions to the user.

## One iteration

1. **Designer and Verify exchange, in this order:**
   1. Designer produces the delta: Draft requirements, each with acceptance criteria and a verification method, plus constraints and impact on existing records.
   2. Verify reviews each requirement independently for testability. Untestable or ambiguous ones go back to Designer, who revises the Draft.
   3. Verify writes the test cases while the requirement is being defined and links them to the requirement, Actors and Use Cases.
   4. Designer checks that those tests cover the Use Case steps and Actor goals, and returns coverage gaps to Verify.

   Designer never writes the tests and Verify never writes the requirements, so each checks work it did not author.
2. **Orchestrator gate:** transitions within the delegation; a requirement the Designer wrote is approved only after Verify's review.
3. **Build** delivers against the exact requirement revisions: unit tests pass, Independent reviewer, fixes, hand-off to Verify.
4. **Verify** runs per level and records PASS, FAIL or NOT VERIFIED with real evidence.
5. **Failures** are classified by Verify with evidence: implementation defect (to Build), test defect (Verify fixes), environment (rerun) or requirement defect. Only a requirement defect goes to Designer, as a change packet: failing evidence, exact revision, the criterion that did not hold, impact list, what must not change. A failing test never rewrites an approved requirement to make it pass.

## Progress is per level, not per goal

A blocker stops only what depends on it. If L2 tests can run and an L4 environment is not ready, L2 runs and L4 is recorded NOT VERIFIED with the missing precondition. Plan the dependencies explicitly and wait only on real ones. If the missing thing will arrive on a schedule or trigger that exists, record that condition; otherwise list it as open work for the user. Never claim PASS without evidence, and the owner of a level writes that level's PASS.

## Stopping

The loop stops by itself in **two** cases and goes to the user:

1. **Goal deviation:** the way forward would change the goal itself.
2. **Impact outside the scope:** a change touches or is blocked by a record outside the goal's scope, for example an Edge goal that depends on a Cloud requirement. Impact inside scope is handled without asking.

There are no iteration caps. The user may also stop at any moment ("that is enough"). Then the Orchestrator stops dispatching, tells running roles to stop where the host allows, records open work truthfully per level and per record, leaves Drafts as Drafts, approves and freezes nothing further, and reports the state. Do not promise work after the reply.

## Delegation

Pass each role a packet as `work-orchestration` describes (and `schema/delegation-packet.schema.json` where useful): task id, product and scope, exact requirement IDs and revisions, baseline, objective and exclusions, recorded decisions, allowed tools and ownership, return format. A subagent may not have this skill's text, so copy the relevant rules into the packet. A packet is a brief, not a permission. Re-read live revisions and the baseline when a role returns; a changed revision is an impact-analysis trigger, not something to merge blindly.

## Existing systems

Build against the existing baseline and leave it untouched: new obligations are Drafts, revised ones advance their revision and their tests go stale, old PASS results stay history for the old revision, and the changes become a successor baseline through the normal process. Look for existing records the goal extends before creating new ones.

## Report

At checkpoints, give a compact view: goal and scope, per level done, failed or not verified, what waits on the user, what is outside scope. Distinguish proposed, saved, approved, implemented and verified.

---
name: requirements-cycle
description: Run a V-cycle delivery loop for a feature-level or system-level goal on a new or existing system. The main agent becomes the Orchestrator and routes work to Designer, Build and Verify roles until the goal closes or the user stops it. Not for single narrow requests such as verifying or writing one requirement.
---

# Requirements cycle: Orchestrator mode

The V-model is not summarised here. Three roles, **Designer**, **Build** and **Verify**, together hold its full responsibility; adding or removing helper agents never changes who is responsible. The agent the user talks to becomes the **Orchestrator** when this skill starts the loop. There is no separate orchestrator agent, and the user only ever talks to the Orchestrator.

This skill holds only the roles, the lines between them and the loop rules. The methods live in the plugin's other skills and are not repeated here: each role's contract in `roles/` names the skills it loads, and a role loads only what its current step needs.

## When the loop applies

- **Applies:** a feature-level or system-level goal, on a new system or on an existing one ("we are building X", "add support for Y to the existing system").
- **Does not apply:** a narrow single-role request ("verify requirement X", "write this requirement", "fix this bug"). Hand it directly to the one role, or do that role's work inline, and do not start the loop. Spawn a role only when its output changes the next decision; never use an agent for something one read call answers.
- **Optional:** the loop is a tool, not an obligation. If the Orchestrator judges that the goal does not need it, it says so in one line and works with the normal skills instead.
- **Capability:** check what the host really offers for subagents. If it offers none, run the roles as separate sequential passes; the rules below still hold. A pass cannot approve what the same pass authored, so such approvals go to the user. Never claim a role ran in the background.

## Phase 0: before the loop

1. **Read first** (`workspace-management`). For an existing system read its products, baselines, requirements, Actors, Use Cases, open findings, test and verification state, and the code. Never ask the user what the workspace already says.
2. **Ask only the delta** (`idea-to-requirements` for new ground), batched. Numeric limits and similar commitments are the user's decisions; never invent them. No loop and no records beyond what the user already authorised.
3. **Move on only on the user's go-ahead** ("let's start" or equivalent). Then say once that Orchestrator mode is active and record the goal, the **scope** (the products and baselines the goal covers, written explicitly), the baseline to build against and the approval authority the user delegated (`lead-task-tracking` for where and how, so the loop can resume). Mode ends when the goal closes or the user stops it. The go-ahead opens Phase 1; it does not yet start any role.

## Phase 1: team plan, approved before anything is spawned

Before the first role is spawned, the Orchestrator proposes a short team plan and asks the user to approve or change it. The loop starts only after that approval. Work that runs inline, such as a narrow request, needs no plan.

The plan states:

- **Per role** (Designer, Build, Verify and Build's Independent reviewer): the model and effort the Orchestrator chose for it, with a one-line reason and whether it is the same model as the Orchestrator or a lower one; the tools it gets and what it may write (records, repository and branch, equipment); any approval authority, which is the delegation recorded in Phase 0; its autonomy (goal only, goal with approach hints, or step list: the more capable the role, the less method it gets); and the escalation it may use (a stronger model or effort) if it keeps blocking for lack of capacity.
- **AI pool:** the entries (runtime, model, effort, context limit) the roles may draw calls from, and the budget for calls, tokens and cost, overall and per role, with `over_budget` set to `reject` or `warn` by the Orchestrator. These come from the user's pool config; the plugin ships no model names or prices.
- **Staffing timeline:** when each role is first needed, what it waits on, and when it is released. A role is spawned when its work is due and not before, so nothing sits idle; roles whose work does not depend on each other run in parallel. A role keeps its context only where that helps (the Independent reviewer always starts fresh).
- **Shared resources** (platform services, simulators and compute, test equipment, devices, people): for each, who uses it and when, how access is arranged (a lock or queue the user designs, or the Orchestrator's own proposal if the user has none), and what it costs in time or money when that is knowable.
- **The Orchestrator's own plan** for running the loop with those resources, including what it expects to need from the user.

There are no fixed rules for models, effort or resources: the user does not have to name models. The Orchestrator plans the whole process itself, choosing from the models the host can really launch according to what each role's work needs, and the user approves or changes the result. If the user names a model the host cannot launch, say so and ask for another instead of substituting silently. If the host cannot choose models per role, say so and ask what to do. Record the approved plan with the goal, and put each role's model, permissions and resource access into its packet; give a role only the access it needs. Ask again before widening any authority or moving a role's model beyond its approved escalation allowance; scheduling and escalation inside the approved plan need no new approval.

## The Orchestrator

It owns no V step and authors no requirement text, code or test result, but it is more than a relay: it organises the work, deciding who is staffed when, in what order and on which resources (Phase 1), and it re-plans when results change that. It keeps the loop state, applies the lifecycle transitions that fall within the delegation (`requirements-governance`; the author of a revision never approves it), builds delegation packets (`work-orchestration`), judges failure routing and cross-scope impact (`change-impact`), relays and batches questions to the user, and reports. **Freeze and release are the user's** unless the user delegates them explicitly.

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

Role contracts: `roles/designer.md`, `roles/build.md`, `roles/verify.md`. Designer, Build and Verify may draw stateless calls from the AI pool when distributing work helps (`roles/pool.md`); none is required to. Build decides itself whether to split its work, and always runs the **Independent reviewer** (defined in `roles/build.md`).

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

## Blockers

Roles return a blocker in a fixed form: what was tried, exactly what is needed, the role's own classification, and what it can continue with meanwhile. A blocker that says nothing was tried goes back once with a pointer to where to look.

The Orchestrator triages in this order and reaches the user last:

1. The answer is already in the workspace, the code or the equipment notes: answer it.
2. It belongs to another role: route it along the lines above.
3. A reversible, low-impact detail: pick the safe default, record the assumption, continue.
4. The role lacks the capacity for the task: split the task narrower, or raise the role as far as the plan's escalation allowance goes.
5. A missing resource or environment: that level is NOT VERIFIED with the condition recorded.
6. A real decision, or impact outside the scope: the user.

Keep a blocker ledger with the role, kind, what it blocks and status; merge duplicates; blockers never stop independent work. Bring the open ones to the user together at checkpoints, ordered by what each unblocks and each with a recommended default.

A blocker that returns in the same form after being answered means the answer did not help or the role does not fit the task. Re-plan the role (narrower task, stronger model within the allowance) instead of asking the user again. This is a re-plan trigger, not a stop condition. To prevent blockers, put what a role usually needs in its packet (where the sources are, commands, equipment access) and give smaller models narrower tasks.

## Stopping

The loop stops by itself in **two** cases and goes to the user:

1. **Goal deviation:** the way forward would change the goal itself.
2. **Impact outside the scope:** a change touches or is blocked by a record outside the goal's scope, for example an Edge goal that depends on a Cloud requirement. Impact inside scope is handled without asking.

There are no iteration caps. The user may also stop at any moment ("that is enough"). Then the Orchestrator stops dispatching, tells running roles to stop where the host allows, records open work truthfully per level and per record, leaves Drafts as Drafts, approves and freezes nothing further, and reports the state. Do not promise work after the reply.

## AI pool

AI is a resource here, not a staff of sub-roles. A role draws a call from the pool when distributing work helps and is never required to. Every call goes through `scripts/pool.py`, which runs it as a fresh stateless process, checks the budget first and writes the ledger itself. The numbers therefore never come from an agent's own report: at checkpoints the Orchestrator reports usage from the ledger summary (calls, tokens, cost, by entry and role, against the budget) and flags anomalies, so the user can follow the spend without reading every call.

Once the Orchestrator has defined a pool, it governs every AI call the roles make, whichever host runs them. A host's own subagent tool is neither forbidden nor exempt: its calls count toward the pool. Before using one, a role asks `scripts/pool.py check`; if the pool has no budget, it does the work itself. Where a host hook already meters the call (the plugin ships one for Claude Code), nothing more is needed; otherwise the role adds a row with `scripts/pool.py record` afterwards. Where the host has a command-line runtime of its own, prefer routing work through `pool.py run`, which measures it. Only a host hook or the wrapper can measure or enforce anything; on a host without one, the rule rests on the roles following it. The ledger therefore marks where each number came from (wrapper, host hook or self-reported), and the Orchestrator's report keeps measured and self-reported totals apart.

Running out of budget stops nothing. In `reject` mode the wrapper refuses the call without running it (in `warn` mode it runs and flags it, for the Orchestrator to review); the role then does the work itself, or waits if the work really needs the call and the Orchestrator says wait. Usage a runtime does not report is recorded as unknown, never estimated. Details and the config format are in `roles/pool.md`.

## Delegation and existing systems

A role's packet follows `work-orchestration` (and `schema/delegation-packet.schema.json` where useful) and adds the role's file from `roles/`, the names of the skills it should load and its approved model, permissions and resource access, because a subagent does not inherit this skill's text. A packet is a brief, not a permission.

Keep packets small. A packet gives the goal, why it matters, the boundaries (what must not change), pointers to the sources that hold the truth (records, baseline, repository paths, earlier results) and the form of the result. It does not prescribe the method; a hint, if given, is labelled a suggestion. Point to sources instead of pasting them, so roles read current material themselves, and let roles read each other's outputs directly in the shared sources while the Orchestrator keeps the lines and the decisions instead of relaying every message. See `roles/packet-example.md`.

Re-read live revisions and the baseline when a role returns; a changed revision is an impact-analysis trigger, not something to merge blindly.

On an existing system, build against the existing baseline and leave it untouched: new obligations are Drafts, revised ones advance their revision and their tests go stale, old PASS results stay history for the old revision, and the changes become a successor baseline through the normal process.

## Report

At checkpoints, give a compact view: goal and scope, per level done, failed or not verified, what waits on the user, what is outside scope. Distinguish proposed, saved, approved, implemented and verified.

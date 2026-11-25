# Changelog

## 0.8.2 — initial marketplace import

## 0.8.3 — display name "Plotune Requirements" (metadata only)

## 0.9.0 — listing metadata (license, homepage, logo, Codex prompts within limits), Cursor manifest, OpenCode entry point, eval suite

## 0.9.1 — Cursor manifest displayName (matches Cursor's own plugin format)

## 0.10.0 — Add requirements-cycle skill: Orchestrator mode with Designer, Build and Verify roles, communication lines, per-level progress and two stop conditions

## 0.10.1 — Release marker for the requirements-cycle skill, AI pool and Claude Code pool hook; no functional change since 0.10.0

## 0.11.0 — requirements-cycle: roles on other runtimes (brief by path, file-handoff format and schema, Orchestrator runs the Independent reviewer for an external Build), team plan asks for runtime, cost ceiling, progress visibility and iteration size, grouped owner decisions, declared parameters, privileged runs, gates stay with Verify, instrument self-check before gating runs, standing roles outside the AI pool (issue #13). Progress counts only what the checking role accepted or a status lookup shows, never a role's own report; long-running work is bounded in the team plan and no agent waits idle; plan limits are countable units and the user reads actual usage at checkpoints; roles report what exists and where to check it, and may stop as a valid result.

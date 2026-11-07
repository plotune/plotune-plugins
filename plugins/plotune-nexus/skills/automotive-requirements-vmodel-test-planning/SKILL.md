---
name: automotive-requirements-vmodel-test-planning
description: Use when turning automotive product intent into requirements, acceptance criteria, V-model traceability, ASPICE-style workproducts, SIL HIL or bench test plans, coverage matrices, regression plans, or evidence packages.
---

# Automotive Requirements V-Model And Test Planning

Use this skill for offline requirements and verification planning. It works without Nexus hardware.

Read:

- `../../references/automotive-domain/requirements-testing.md`
- `../../references/automotive-domain/safety-security.md`
- `../../references/automotive-domain/nexus-adoption-map.md`
- `../../references/automotive-domain/script-catalog.md`

Run script examples from the plugin package root, the directory containing `skills/`, `references/`, and `scripts/`. If script execution is restricted, do a manual best-effort review and state which script checks were not run.

## Workflow

1. Normalize user intent into testable requirements with units, timing, modes, and failure behavior.
2. When requirements or tests are supplied as CSV, JSON, or Markdown tables, run the trace linter first:

   ```bash
   python3 scripts/automotive/requirements_trace_lint.py --requirements path/to/requirements.md --tests path/to/tests.csv --format json
   ```

3. Build evidence manifests for generated reports or supplied evidence files:

   ```bash
   python3 scripts/automotive/evidence_pack.py --inputs path/to/report.json path/to/trace.log --classification offline --format json
   ```

4. Use `automotive_triage.py` when the user provides mixed artifacts and wants a first-pass workflow map:

   ```bash
   python3 scripts/automotive/automotive_triage.py --inputs path/to/requirements.md path/to/tests.csv path/to/trace.log --format json
   ```

5. Build or review traceability from source intent to design, implementation, verification, and evidence.
6. Separate SIL, HIL, bench, vehicle, and manual review evidence.
7. Define test preconditions, expected outputs, stop conditions, and artifact formats.
8. Use `plotune-test-sequences-reporting` when test plans need managed Nexus execution.

## Output

**Requirements tables**: ID, description, acceptance criterion, and test link columns. Flag vague entries by ID: "REQ-003 (EngineStartTime) has no measurable threshold — 'fast start' is not testable."

**Traceability gaps**: name the specific requirement or test ID that's unlinked. Don't just say "5 requirements have no test."

**Evidence manifests**: list artifact name, type, and classification — one line per artifact.

**Test plans**: for each test, state preconditions, stimulus, expected output, and pass/fail criterion. Separate SIL, HIL, bench, vehicle, and manual review evidence.

State explicitly what cannot be validated without hardware, a physical test bench, or qualified safety review.

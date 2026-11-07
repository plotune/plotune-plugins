---
name: automotive-functional-safety-workproducts
description: Use when drafting or reviewing automotive functional safety workproducts, including item definitions, HARA, ASIL rationale, safety goals, FMEA, FTA, safety cases, safety requirements, validation evidence, or ISO 26262 traceability.
---

# Automotive Functional Safety Workproducts

Use this skill for structured safety drafting and review. It is not certification evidence and does not replace qualified safety assessment or licensed standards.

Read:

- `../../references/automotive-domain/safety-security.md`
- `../../references/automotive-domain/requirements-testing.md`
- `../../references/automotive-domain/nexus-adoption-map.md`
- `../../references/automotive-domain/script-catalog.md`

Run script examples from the plugin package root, the directory containing `skills/`, `references/`, and `scripts/`. If script execution is restricted, do a manual best-effort review and state which script checks were not run.

## Workflow

1. Identify the workproduct type: HARA, FMEA, FTA, safety case, requirement, test evidence, or traceability matrix.
2. Generate draft table structures with the bundled safety script when the user asks for a starting worksheet:

   ```bash
   python3 scripts/automotive/safety_workproduct.py template --kind hara --item "Brake Control" --format json
   python3 scripts/automotive/safety_workproduct.py template --kind fmea --item "BMS Controller" --format json
   ```

3. Lint supplied HARA, FMEA, FTA, safety-goal, or safety-case tables before prose review:

   ```bash
   python3 scripts/automotive/safety_workproduct.py lint --kind hara --input path/to/hara.csv --format json
   ```

4. For requirement/test traceability gaps, run:

   ```bash
   python3 scripts/automotive/requirements_trace_lint.py --requirements path/to/requirements.md --tests path/to/tests.csv --format json
   ```

5. Ask for item definition, operating context, assumptions, and safety-relevant interfaces when missing.
6. Draft tables or review findings with explicit open assumptions.
7. Link hazards to safety goals, requirements, design elements, tests, and evidence.
8. Use Nexus only to collect bounded evidence or execute approved tests, never to bypass safety review.

## Output

**Templates**: present as readable markdown tables, not raw JSON rows. Label them "Draft — not reviewed."

**Lint results**: summarize by issue type with named examples. "3 HARA rows missing severity rating: rows Hazard-04, Hazard-07, Hazard-09" is useful. A count without names is not.

**Traceability**: list unlinked requirements by ID and name. "REQ-005 (BrakeResponseTime) has no test link" is useful. Raw counts alone are not.

**Always**:
- Label all outputs as drafts or review aids.
- Avoid compliance claims ("this satisfies ISO 26262 ASIL D").
- Call out missing evidence, unresolved assumptions, and decisions that belong to the safety manager, not the agent.

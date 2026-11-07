# Requirements, V-Model, And Test Planning

Use this reference for turning automotive intent into reviewable requirements and test plans.

## Requirement Quality

Good requirements are:

- singular and testable
- scoped to one system behavior
- tied to operating conditions and modes
- clear about units, timing, tolerances, and failure behavior
- traceable to source intent, safety/security goals, or architecture decisions

Flag ambiguous words such as fast, robust, safe, normal, optimized, and user-friendly unless they are backed by measurable criteria.

## V-Model Traceability

Keep links between:

- stakeholder or customer requirement
- system requirement
- software or hardware requirement
- architecture/design element
- implementation artifact
- verification method
- test result or evidence artifact

## SIL/HIL Planning

- Define plant model assumptions and signals.
- Separate nominal, boundary, fault-injection, and regression tests.
- Declare what cannot be validated without hardware.
- Capture expected evidence format before running tests.
- Keep safety/security preconditions explicit for actuator, diagnostic, flash, and calibration tests.

## Script Helpers

Run from the plugin package root when script execution is allowed:

- `python3 scripts/automotive/requirements_trace_lint.py --requirements requirements.md --tests tests.csv --format json`
- `python3 scripts/automotive/evidence_pack.py --inputs report.json trace.log --classification offline --format json`

If command execution is restricted, do not bypass it. Review snippets manually and state that deterministic script checks were not run.

## Nexus Handoff

Use `plotune-test-sequences-reporting` for managed bench sequence definitions and evidence capture. Use artifacts for reports, traces, logs, and measurement outputs.

---
name: automotive-profiles
description: Tailor existing or new automotive requirements reviews to a project's explicitly selected Automotive SPICE, ISO 26262 and general systems-engineering standards without claiming certification, inventing ASIL or copying proprietary normative text.
---

# Optional automotive standards profiles

The method core remains industry-neutral. Only activate a profile when the user's project has documented the relevant standard **edition, scope, tailoring and responsible reviewers**, or the user explicitly asks for an *advisory* gap analysis. No preconfigured customer or maintainer profile is active by default. Record project choices in `standards_profiles`; never silently amend a user's Guide or claim conformity/certification.

## Standards and changeable editions

As of November 2026, VDA QMC officially lists **Automotive SPICE 4.1 (August 2026)**; ISO lists the published **ISO 26262:2018** series while 2026 DIS revisions remain drafts; ISO/IEC/IEEE **29148:2018** remains published (revision draft pending). The authoritative project's contract/regulator/organization may require a different edition; use **its real selection**. Verify current authoritative sources again when material; do not pretend these defaults govern all customers.

Public references (informational, not copied standard text):
- Automotive SPICE: https://vda-qmc.de/en/automotive-spice/automotive-spice-veroeffentlichungen/
- ISO 26262 2018 series: https://www.iso.org/publication/PUB200262.html
- ISO/IEC/IEEE 29148:2018: https://www.iso.org/standard/72089.html

The plugin distributes **original checklists and review heuristics only**. Never reproduce purchased standard clauses, VDA PAM text or proprietary customer assessments. State a precise clause ID only if verified in an authorized user-provided reference, along with edition and responsible reviewer.

## Automotive SPICE: process/work-product **support**, not assessment result

For process areas selected in the user's project (for example applicable system stakeholder/requirements/architecture/integration/qualification activities, relevant software/hardware requirements, SUP.8 configuration and SUP.10 change management), ask whether each expected project result has traceable evidence: stakeholder need, analyzed consistent system requirement, bidirectional architecture/testing links, baseline/configuration state, controlled change, test result and coverage. Do not treat a database field as automatic Automotive SPICE process achievement. Check project-specific PAM scope and whether each process actually applies before making a gap finding. **ASPICE process capability levels 0–5 are not the project's L1–L6 test maturity scale.** No unsupported assessor score or compliance percentage.

## ISO 26262: safety-conditional analysis

First establish whether an item/function is genuinely in the project's functional-safety scope and whether a validated safety lifecycle artifact exists. For a safety-related OBC item, review traceability as applicable: item definition/operating context, HARA and safety goals, Functional Safety Concept / FSR, Technical Safety Concept / TSR, hardware/software safety requirements, architecture/safety mechanisms, safety analyses, verification and safety-related change impact. Use external references and typed links when a company's safety analysis lives in another qualified system; **never demand duplicated HARA/FMEA/FTA content inside this RMS**.

Never invent ASIL, hazard classification, safety goal, diagnostic coverage, safety mechanism, independence judgment, confirmation review completion or safety acceptance. A safety reviewer retains responsibility. Check when a change requires revisiting safety analyses and corresponding requirements/tests; show open review questions rather than converting them into mandatory design instructions.

ISO 26262 functional safety does not replace all electrical safety / EMC / charging interoperability / cybersecurity or other applicable standards for an OBC. Select other domain standards only from verified project context.

## Output and governance

Each applicable finding includes project profile ID, edition, purpose (quality heuristic / work product trace / actual clause mapping if verified), exact affected record/revision, available supporting artifact, gap, owner and proposed action. Mark: `Supported`, `Needs project evidence`, `Not applicable by tailoring`, or `Unverified applicability`. If no profile exists, prepare a *proposed* profile with boundaries and source URLs for project owner review; don't activate it automatically.

Use `existing-requirements-review`, `change-impact` and `verification-coverage` to produce and track actionable findings rather than writing huge one-off compliance reports. Profile selection itself is auditable change of project governance and does not freeze requirements.

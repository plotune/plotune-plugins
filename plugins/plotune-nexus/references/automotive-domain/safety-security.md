# Safety And Security Workproducts

Use this reference for structured planning and review of safety/security workproducts. It is not certification evidence or legal advice.

## Functional Safety Workproducts

- HARA: item definition, operating situation, hazard, severity, exposure, controllability, safety goal.
- FMEA: item/function, failure mode, effect, cause, controls, action owner, evidence.
- FTA: top event, fault tree logic, basic events, assumptions, evidence links.
- Safety case: claim, argument, evidence, open assumptions, review status.
- Traceability: hazard -> safety goal -> requirement -> design -> test -> evidence.

Avoid claiming compliance from generated text. The output should be a draft or review aid for qualified engineers.

## Cybersecurity Workproducts

- Asset and interface inventory.
- Damage scenarios and impact.
- Threat scenarios and attack paths.
- Attack feasibility and risk treatment.
- Cybersecurity goals, requirements, mitigations, and verification evidence.

Keep diagnostics, flashing, seed/key, certificates, OTA, and debug access in the attack surface when relevant.

## Script Helpers

Run from the plugin package root when script execution is allowed:

- `python3 scripts/automotive/safety_workproduct.py template --kind hara --item "Item Name" --format json`
- `python3 scripts/automotive/safety_workproduct.py lint --kind hara --input hara.csv --format json`
- `python3 scripts/automotive/tara_workproduct.py template --kind threat-scenario --asset "Asset Name" --format json`
- `python3 scripts/automotive/tara_workproduct.py lint --kind threat-scenario --input tara.csv --format json`

If command execution is restricted, do not bypass it. Review snippets manually and state that deterministic script checks were not run.

## Nexus Handoff

Use Nexus workflows to collect bounded evidence, not to bypass safety/security review. Active tests that can change ECU state need explicit operator confirmation, exact payloads, and stop conditions.

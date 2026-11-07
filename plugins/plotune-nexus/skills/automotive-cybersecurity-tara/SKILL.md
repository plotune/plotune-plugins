---
name: automotive-cybersecurity-tara
description: Use when drafting or reviewing automotive cybersecurity workproducts without live attacks, including TARA, ISO SAE 21434 style asset analysis, attack surfaces, damage scenarios, threat scenarios, feasibility, risk treatment, secure diagnostics, OTA, keys, certificates, or UN R155 preparation.
---

# Automotive Cybersecurity TARA

Use this skill for offline cybersecurity analysis and planning. It does not run penetration tests or active scans.

Read:

- `../../references/automotive-domain/safety-security.md`
- `../../references/automotive-domain/diagnostics.md`
- `../../references/automotive-domain/nexus-adoption-map.md`
- `../../references/automotive-domain/script-catalog.md`

Run script examples from the plugin package root, the directory containing `skills/`, `references/`, and `scripts/`. If script execution is restricted, do a manual best-effort review and state which script checks were not run.

## Workflow

1. Build an asset and interface inventory.
2. Generate draft TARA tables when the user needs a starting structure:

   ```bash
   python3 scripts/automotive/tara_workproduct.py template --kind threat-scenario --asset "Diagnostic Service" --format json
   python3 scripts/automotive/tara_workproduct.py template --kind attack-surface --asset "OTA Service" --format json
   ```

3. Lint supplied TARA workproducts before prose review:

   ```bash
   python3 scripts/automotive/tara_workproduct.py lint --kind threat-scenario --input path/to/tara.csv --format json
   ```

4. Use read-only tool inventory only when local tool availability matters:

   ```bash
   python3 scripts/automotive/tool_inventory.py --format json
   ```

5. Identify damage scenarios, threat scenarios, attack paths, impact, feasibility, and mitigations.
6. Include diagnostics, flashing, seed/key, certificates, OTA, debug, cloud, and logging interfaces when relevant.
7. Keep risk treatment decisions separate from technical observations.
8. Use Nexus only for bounded evidence collection or approved bench validation.

## Output

**Tables**: present attack-surface, damage-scenario, and threat-scenario tables as readable markdown, labeled as drafts. Each row should name the asset, threat, feasibility, and proposed mitigation — not just IDs.

**Lint results**: name the specific row or field with the issue. "Threat-03 (OTA injection) is missing feasibility rating" is useful. Raw counts are not.

**Risk treatment**: keep treatment decisions (accept/transfer/mitigate) separate from technical observations about the attack path.

Mark unknown exposure, credential handling, key management, and update paths as open questions, not as conclusions.

Do not provide instructions that enable unauthorized access to production ECUs.

# Continuous Engineering schema upgrade: 1.0.0 → 1.1.0

This is an **additive** opt-in change. Existing workspace state remains authoritative; the bundle's version is not a mandate to upgrade. New tables: `review_findings`, `change_requests`, `change_impacts`, `standards_profiles`. No change to existing requirement IDs, revision semantics, baseline snapshots, Actors or Use Cases. The workbook package is always blank; never use it to overwrite an existing populated workbook.

**Preflight:** Identify the user's canonical backend, real schema version, existing custom review/change objects and write permissions. Preserve current Guide and project-specific process definitions, including nonstandard status values. Dry-run expected new tables/field mappings, test stored reference integrity and make a backup/restore plan. Ask for explicit workspace migration authorization before applying. Read back after migration. Never auto-enable automotive compliance profiles or create fake assessment evidence.

**SQLite:** Run `python scripts/workspace.py migrate --backend sqlite --path FILE` to preview. After authorization, run with `--apply`: makes timestamped online SQLite backup, runs `migrations/sqlite-1.0.0-to-1.1.0.sql` inside an immediate transaction, validates column order, FK, cross-record references and schema version. It refuses unsupported versions and won't edit any frozen baseline record.

**CSV:** Dry-run is analogous. With `--apply`, back up existing directory, add four header-only files, update only schema version in `workspace.json`, and validate. Writes remain non-transactional across files; use SQLite for concurrent writers.

**Google Sheets:** Review current tab names, headers, validation, formulas and Guide. After explicit permission, add only four blank tabs with portable headers or map to equivalent existing review/change sheets. Preserve existing rows, styling, formulas and owner permissions. Record the canonical workbook URL in *user-owned* manifest; read back all affected tabs. No automatic public cloud write.

**RMS / external ALM:** Map to existing native review/change/standards objects where possible; do not create a separate authority. Use live supported connector/API, real approval permissions and audit; if unavailable, provide unsaved structured records. Import/export only after explicit reconciliation/cutover.

**Reversibility:** Data backed up before changes. New records should not be discarded silently if rolling back; export them and restore a validated backup under owner control. Do not change an established project's safety or ASPICE process just because a bundled example exists.

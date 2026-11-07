---
name: automotive-ehb-reader
description: Use when analyzing automotive EHB documentation archives to extract engineering meaning about signal roles, module ownership, port access modes, and component relationships — not just searching for symbol occurrences.
---

# Automotive EHB Reader

## What This Skill Does

An EHB file is a ZIP archive of software architecture documentation — DITA topics, AUTOSAR KAOM component model files, SVG diagrams, and HTML. Use this skill to extract engineering meaning from EHB content, not just to confirm a symbol exists.

The goal is answers to engineering questions: Which module owns this signal? Is it imported or exported? What does the documentation say it represents? Which other modules depend on it?

---

## Evidence Collection

```bash
# List archive contents to understand structure
python3 scripts/automotive/inspect_ehb.py --ehb file.ehb --list-entries | head -60

# Search for one or more symbols
python3 scripts/automotive/inspect_ehb.py \
  --ehb file.ehb \
  --symbol MY_SIGNAL \
  --symbol CANDIDATE_INPUT
```

Search output gives you: `file`, `entry` (archive path), `symbol`, and `snippet` (500-char excerpt). The interpretation work begins here.

---

## EHB Entry Type Interpretation

Different file types inside an EHB archive answer different questions:

### `.dita` and `.html` — Structured Documentation
These are the primary information sources. The snippet will contain:

- **`<longname>`** — human-readable description of the signal or variable.
- **`<mode>`** — `import` (read from another module) or `export` (provided to other modules).
- **`<access>`** — `READ-ONLY` means the variable is consumed by this module, not modified here. `READ-WRITE` means this module owns the value.
- **`<entry>` text** — often a plain-language description: *"static idle speed for combustion engine"*, *"diameter of the fuel tank leakage"*.

**What to extract:** Signal description in plain English, access mode, direction (import/export), and which DITA module the entry belongs to (first segment of the entry path after `documentation/`).

### `.kaom` — AUTOSAR Component Model
KAOM files describe software component port connections. Snippets contain:
- Port delegation patterns (which component provides what to which consumer).
- Annotation values like `delegateId` that link to component instance IDs.

**What to extract:** Confirm that the signal's port exists in this component, and whether it is delegated outward (consumed by another component) or delegated inward (provided by a sub-component). This confirms cross-module dependency.

### `.svg` — Architecture Diagrams
SVG files are rendered model diagrams. Snippets may contain text labels or coordinates. By themselves they confirm the symbol appears in a visual architecture diagram for that module, which corroborates documentation.

**What to extract:** Confirm the symbol is part of the documented architecture for that module. Do not try to parse coordinates or SVG structure.

### `.ditamap` — Topic Map
Lists the DITA topics that belong to a documentation unit. Useful for understanding module scope, but rarely contains signal-level detail directly.

---

## Module Identification

The `entry` path structure is: `documentation/<ModuleName>/<file>`. The `<ModuleName>` segment identifies the software module. Examples:

| Module name | Engineering meaning |
|-------------|-------------------|
| `SpdIdlEng` | Idle speed control for combustion engine |
| `BsgStop` | Belt-starter-generator stop coordination |
| `ATLD_SctIf` | Active tank leak detection, section interface |
| `CESys_DrvSitGlbGsl` | Drive situation global for gasoline engine |
| `CEPfilGsl_SwAdpOut` | Gasoline particulate filter adaptation output |
| `CoEng` | Engine coordination |

When a signal appears in multiple modules, list them all — multiple module mentions indicate the signal crosses module boundaries and is architecturally significant.

---

## Analysis Steps

### 1. Identify which modules mention each symbol
Group matches by module name (first path segment after `documentation/`). Signals that appear in many modules are interface-critical.

### 2. Extract the access mode and direction
From DITA snippets, determine: is this signal READ-ONLY in this module (consumed, not produced here)? Or READ-WRITE (owned by this module)?

### 3. Extract the human-readable description
Find the `<entry>` text or `<longname>` content in the snippet. This is the most valuable piece — it tells you what the signal physically represents.

### 4. Check for KAOM port connections
If KAOM entries appear, they confirm the signal has an explicit port in the component model. This is stronger evidence than a text mention.

### 5. Synthesize into an access pattern statement

Write one paragraph per signal:
> `EngDa_tEng_VW` appears in the `ATLD_SctIf`, `BsgStop`, and `CESys_DrvSitGlbGsl` modules as a READ-ONLY import. DITA documentation describes it as *"engine temperature for the corresponding module function"*. KAOM entries confirm it has an explicit port in all three components. This signal is a widely consumed engine temperature aggregate used by emissions, stop-start, and drive situation functions.

---

## What NOT to Do

- Do not paste raw snippet text into reports. Snippets are XML fragments — extract meaning from them.
- Do not treat SVG or KAOM matches as signal definitions. They are corroborating evidence, not primary sources.
- Do not report "N matches found" as a finding. Report what the matches mean.
- Do not skip the module name analysis. A signal in 8 modules is architecturally different from a signal in 1.
- Do not quote entry path hashes (e.g., `eHCb440a2d0a165db20e116a11d8a36f0a1e.dita`). Use the module name instead.

---

## Output Format

For each searched symbol, produce:

**Signal: `SYMBOL_NAME`**
- **Plain-English meaning:** (from DITA description text)
- **Module presence:** List of modules it appears in, with access mode per module.
- **Direction:** Imported (READ-ONLY) / Exported (READ-WRITE) / Mixed.
- **KAOM confirmation:** Yes/No — whether a component port connection was found.
- **Engineering interpretation:** One sentence on what this means for understanding the signal's architectural role.

If a symbol produces **no matches**, state that clearly and explain what to check next (try a shorter prefix, try a related signal, or note that this function may not be documented in this EHB version).

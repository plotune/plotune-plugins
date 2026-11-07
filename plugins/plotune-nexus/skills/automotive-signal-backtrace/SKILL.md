---
name: automotive-signal-backtrace
description: Use when tracing an automotive software signal backward through A2L, Intel HEX, and EHB artifacts to understand its dependencies, calibration gates, and software architecture — and when the goal is an engineering analysis report, not just script output.
---

# Automotive Signal Backtrace

## What This Skill Does

Trace a signal backward to understand **where it comes from, what conditions gate it, and what that means for ECU behavior**. The end product is an engineering analysis a calibration engineer or software integrator can act on — not a raw data dump.

Scripts in `scripts/automotive/` are inspection tools. This skill is the analysis methodology that turns their output into insight.

## Required Inputs

- `signal`: exact signal name (A2L MEASUREMENT name or DISPLAY_IDENTIFIER).
- `max_depth`: required integer — ask before starting if not provided.
- `a2l`, `hex`, `ehb`: paths to the calibration file, HEX file, and EHB archive(s).
- Optional `groups`: `FID`, `MIL`, a subsystem prefix, or a signal list.

---

## Workflow

### Step 1 — Collect raw evidence

Run the scripts to gather structured data. These commands are evidence collectors, not the analysis.

```bash
# A2L symbol lookup
python3 scripts/automotive/inspect_a2l.py --a2l file.a2l --symbol MY_SIGNAL

# EHB documentation search
python3 scripts/automotive/inspect_ehb.py --ehb file.ehb --symbol MY_SIGNAL

# Full backtrace JSON
python3 scripts/automotive/signal_backtrace.py \
  --signal MY_SIGNAL --a2l file.a2l --hex file.hex \
  --ehb file.ehb --max-depth 2 --output out/trace.json
```

### Step 2 — Understand the start signal

Before expanding dependencies, characterize the signal itself:

**A2L MEASUREMENT block tells you:**
- ECU_ADDRESS: where the value lives in memory.
- DISPLAY_IDENTIFIER: alternate name used in calibration tools.
- Description text: what the signal represents in the ECU model.

**Which FUNCTION blocks contain it tells you:**
- IN_MEASUREMENT → this signal is an input to that function.
- OUT_MEASUREMENT or LOC_MEASUREMENT → this function computes or uses it.
- DEF_CHARACTERISTIC → calibration maps that govern that function.

State clearly: *"Signal X is a LOC_MEASUREMENT in function Y, which means function Y computes it from these inputs: ..."*

### Step 3 — Analyze signal naming conventions

Automotive signal names encode their role. Decode them before drawing conclusions:

| Pattern | Meaning |
|---------|---------|
| `_VW` suffix | OEM-specific variant for this project |
| `_C_VW` | Constant calibration parameter |
| `_M_VW` | Map/table calibration (multi-dimensional lookup) |
| `_T_VW` | Temperature-dependent table lookup |
| `_A_VW` | Array calibration |
| `DATA_X.Y_C_VW` | Calibration Y in namespace X, constant |
| `Prefix_` first segment | Software module or function block (e.g., `SpdIdlEng_` = idle speed engine, `CoEng_` = engine coordination, `ESS_` = engine state supervisor) |
| `_n` in name | Speed quantity (RPM) |
| `_t` in name | Temperature quantity |
| `_p` in name | Pressure quantity |
| `_flg` / `_b` | Boolean flag |
| `_st` | State machine value |
| `_tq` | Torque quantity |

Apply this to every signal in the graph. Group signals by module prefix to identify which subsystems are involved.

### Step 4 — Analyze direct inputs (depth 1)

For each signal in the followed edges at depth 1:

1. **Name what the input is** — translate the signal name into plain English using naming conventions.
2. **State why it's plausible** — does a coolant temperature input make sense for an idle speed setpoint? Yes — cold start warmup.
3. **Group by subsystem prefix** — signals sharing a prefix (`CoEng_`, `Eng_`, `IntkAirT_`) tell you which function blocks contribute.
4. **Identify the dominant contributor families** — if `ATLD_` contributes 34 edges at depth 2, that is the evaporative emission module. Note what that implies architecturally.

Do NOT just list all 19 direct inputs. Synthesize: *"Direct inputs are dominated by engine temperature signals (4), engine state flags (3), idle speed sub-targets (4), and ambient condition signals (2). This is consistent with a classical multi-condition idle speed arbitration function."*

### Step 5 — Analyze calibration gates (DEF_CHARACTERISTIC)

For each `unresolved_calibration` in the skipped-route table:

1. **Name the calibration** — decode the suffix: `_C_VW` = constant, `_M_VW` = map, `_st_C_VW` = state/mode constant.
2. **Report the raw HEX value** if resolved — even without condition semantics, a value of `0x00` on a boolean gate is likely "disabled," `0x01` or `0xFF` may mean "enabled." State this as an observation, not a conclusion.
3. **State what metadata is missing** — which of the five gating requirements are absent: calibration symbol, ECU_ADDRESS, HEX bytes, byte order, or condition semantics.
4. **Group calibrations by their function** — all `DATA_SpdIdlEng.*` calibrations govern the same function block. Report them together: *"40 calibration gates in the `DATA_SpdIdlEng` namespace were not followed because condition semantics are unavailable. These likely represent ramp rates, speed targets, and mode selection tables."*

### Step 6 — Interpret depth-limited stops

A large number of depth-limited skips (e.g., 1390) is an architectural signal, not just a limit artifact. Interpret it:

- High depth-limited count → the signal sits inside a heavily connected function; increasing depth will expand into most of the ECU.
- Which targets have the most depth-limited candidates → these are the most complex intermediate nodes. Name them.
- Recommend a targeted follow-up: *"To understand the `ChaDiag_stPrfVarPtAct_VW` sub-graph, run a separate backtrace at depth 2 starting from that signal."*

### Step 7 — Interpret EHB evidence

The EHB entries tell you where documentation exists. Interpret them:

| Entry type | What it tells you |
|------------|------------------|
| `.dita` | Structured documentation topic — read the snippet for access mode (READ-ONLY, WRITE), long description, and module membership |
| `.kaom` | AUTOSAR component model — confirms port connections and delegation patterns between software components |
| `.svg` | Diagram — confirms the signal appears in visual model documentation for that module |
| `.html` | Rendered DITA — same as .dita but in human-readable form |

From the evidence entries, extract:
- Which EHB modules mention the signal and its dependencies.
- Access mode: READ-ONLY inputs come from other ECU modules (cross-module dependency); WRITE means this function owns the signal.
- What the documentation says about the signal's role (long description from the snippet).

State: *"EHB evidence confirms `SpdIdlEng` appears in the `CESys_DrvSitGlbGsl` module as a READ-ONLY import — it is consumed by the drive situation global module, not produced there."*

### Step 8 — Interpret group filter results

If a FID or MIL filter returned zero followed edges:

- **This is a meaningful finding, not a failure.** State it explicitly: *"Zero FID-related signals feed directly into this target at depth 1. The signal has no direct FID gate dependency in the current calibration."*
- Report the count of filtered skips: these are the candidates that existed but were outside the filter.
- Distinguish between "no FID dependency" (filter removes everything) vs "FID dependency gated by unresolved calibration" (filtered skips include calibration names that contain FID patterns).

---

## Report Template

Produce these sections in order. Do not paste raw JSON, script stdout, or raw Mermaid edge lists into the report.

### 1. Signal Summary
One paragraph: what the signal is, what it represents in ECU behavior, which function owns it, and its A2L type (MEASUREMENT vs CHARACTERISTIC). Use the decoded signal name and EHB description.

### 2. Trace Parameters
- Signal, depth, group filter, artifact files (names only, not full paths).
- Counts: followed edges, skipped routes, calibrations encountered, EHB evidence entries.

### 3. Direct Input Analysis
Grouped by subsystem prefix. For each group:
- Module name (decoded from prefix).
- Count of inputs from that module.
- One-line engineering interpretation (what that module's contribution means).

Example:
> **Engine State and Mode (`Eng_`, `CoEng_`)** — 7 inputs. Engine state machine flags and coordination signals gate idle speed selection for start, run, and catalyst-heating phases.

### 4. Calibration Gate Summary
Group all calibrations by their DEF_CHARACTERISTIC namespace (e.g., `DATA_SpdIdlEng`). For each group:
- Total count.
- Suffix breakdown: how many constants (`_C_VW`), maps (`_M_VW`), tables (`_T_VW`).
- Whether raw HEX bytes were resolved (even if semantics are unavailable).
- Engineering interpretation of what these calibrations likely govern.
- Which ones require domain review to determine if they are active.

### 5. Architecture Observations
What does the shape of the graph tell you?
- Number of direct vs second-level inputs.
- Which second-level modules dominate (top 5 source families and what they represent).
- Whether depth-limited stops suggest a deeply integrated function.
- Any cross-module dependencies visible from EHB access modes.

### 6. Group Filter Finding
If a group filter was applied: what does the result tell you about FID/MIL dependency? State the engineering conclusion.

### 7. Open Questions and Next Steps
List specific things an engineer should do next. Not generic "review calibrations" — name them:
- Which calibration gates need semantics confirmed (name the DATA namespace).
- Which intermediate nodes warrant their own backtrace.
- Whether EHB documentation should be checked for specific port connections.
- Any raw HEX values that look like non-default settings requiring explanation.

### 8. Mermaid Diagram
Include a compact summary diagram showing only direct inputs (depth 1) and calibration gates — not the full 450-edge raw graph. The diagram's purpose is visual orientation, not completeness.

---

## What NOT to Do

- Do not paste the full followed-routes table (450 rows is not a deliverable).
- Do not copy raw script JSON into the report.
- Do not list raw ECU addresses as findings — they belong in the calibration table, not the narrative.
- Do not describe `unresolved` calibrations as "errors" — they are open questions awaiting domain input.
- Do not state that a route is "disabled" unless calibration semantics are fully resolved.
- Do not stop at depth 1 if depth 2 was requested — each level adds subsystem understanding.

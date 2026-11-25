# File handoff

For a role that cannot reach the requirements workspace, for example a role on another agent runtime. The role reads context the Orchestrator exported for it and returns its drafts as one JSON file. The schema is `schema/handoff-records.schema.json` (format `plotune-handoff-records/1`).

## The role

- Writes Drafts only. A handoff file proposes records; it never approves, freezes, attests or records a test result.
- Uses local `key`s for new records (`R1`, `TC1`); the workspace allocates real ids on import. A test case points at a requirement by `key` (in this file) or by `id` and `revision` (an existing record).
- Revising an existing requirement means a new Draft with `revises` (id and revision), never an in-place edit.
- Writes criteria against declared parameters (`P-01`, ...) listed in `parameters`, with `value: null` where the user has not set one.
- Lists open decisions in `decisions`, each with a group (`think`, `safe_default`, `confirm_later`, `governance`) and, except for `think`, a proposed default.
- Says in `author` which role it is and where it ran.

## The Orchestrator

1. Validates the file against the schema and refuses one that does not validate, with the errors, back to the role.
2. Checks that `scope.products` is inside the goal's scope and that every `revises` and existing `requirement.id` names a live record at that revision. A stale revision is an impact-analysis trigger, not a merge.
3. Imports requirements as Drafts, then test cases, in the largest batches the workspace offers, one by one where it has none. Every reason names the authoring role and runtime and the file (`Drafted by Designer on <runtime>, handoff <file name> sha256 <first 12 hex>`). Where the workspace records the reported model, pass `author.model` as reported, never a guess.
4. Keeps the map from each `key` to the id the workspace allocated, and gives it to the next role that needs it.
5. Reports what was imported and what was not, with the reason. Records not imported are open work, never dropped silently.
6. Puts `decisions` into the blocker ledger and `parameters` with `value: null` into the open decisions, as their groups say.

Approval follows the normal process afterwards: a Draft imported from Designer's file is reviewed by Verify like any other.

## Example

Synthetic; ids, products and numbers are invented.

```json
{
  "format": "plotune-handoff-records/1",
  "author": { "role": "designer", "runtime": "external-cli", "model": "model-a", "packet": "T-12" },
  "producedAt": "2026-11-25T09:30:00Z",
  "scope": { "products": ["EDGE"], "baseline": "BL-4" },
  "requirements": [
    {
      "key": "R1",
      "productId": "EDGE",
      "state": "Draft",
      "statement": "The Edge shall forward only CAN frames whose identifier matches the session's filter list.",
      "criteria": "With a filter list of P-01 identifiers and P-02 frames/s of mixed traffic for P-03 s, every forwarded frame matches the list and no matching frame is dropped.",
      "verificationMethod": "Test",
      "rationale": "Bench traffic exceeds what the cloud session needs.",
      "parents": ["EDGE-014"]
    }
  ],
  "testCases": [
    {
      "key": "TC1",
      "requirement": { "key": "R1" },
      "name": "Filtered forwarding under mixed load",
      "objective": "Show that only matching frames are forwarded and none are lost.",
      "method": "Test",
      "procedure": "Replay the recorded mixed-traffic file at P-02 frames/s for P-03 s with a P-01-identifier filter; compare forwarded frames with the expected set.",
      "mandatory": true,
      "levels": ["L2", "L3"]
    }
  ],
  "parameters": [
    { "id": "P-01", "name": "Filter list size", "unit": "identifiers", "value": null, "meaning": "Largest filter list a session may set." },
    { "id": "P-02", "name": "Offered load", "unit": "frames/s", "value": null },
    { "id": "P-03", "name": "Test duration", "unit": "s", "value": 60 }
  ],
  "decisions": [
    { "id": "D-01", "question": "What is the largest filter list a session may set?", "group": "confirm_later", "default": "Leave P-01 open; design for up to 64.", "blocks": ["R1"] }
  ]
}
```

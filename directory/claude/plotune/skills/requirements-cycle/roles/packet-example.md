# Example packet

Synthetic. IDs and names are invented. A packet states the goal, the boundaries and where the truth lives, and leaves the method to the role.

```
Role:        Designer (role file: roles/designer.md; skills: requirement-decomposition,
             change-impact, existing-requirements-review)
Autonomy:    goal with approach hints
Model/effort: as approved in the team plan

Goal:        The reported charge level of the battery pack must stay stable when the
             pack temperature changes and must not jump on short load spikes.
Why:         Drivers see unexplained jumps; downstream consumers use the value.

Boundaries:  Do not change approved text in place. Do not touch records outside the
             recorded scope (products P1 and P2). Numeric limits are the user's
             decisions: mark them open, do not fill them.

Sources:     Requirements REQ-120 and REQ-121 at rev 4 in baseline BL-3; Actors and
             Use Cases linked from them; the estimation module under src/estimation/;
             Verify's open testability findings.

Return:      The Draft requirements you wrote (IDs and revisions), the existing
             records they affect, the consumers of the changed behaviour, and what
             you left open.

Hint (suggestion only): the display value and the value used for limits may need
             different behaviour.
```

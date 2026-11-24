---
type: llm
---

PASS if the reply lays out a plan that starts by choosing the project and discovering which events and properties exist
before querying, uses a bounded time range, and does not claim that tool calls cost credits.
FAIL if it jumps straight to an unbounded query, or claims it already ran queries and reports results.

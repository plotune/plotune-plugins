# AI pool

AI as a resource that Designer, Build and Verify can call when distributing work helps. It is not a set of sub-roles and no role is required to use it.

- **Stateless.** Each call is a fresh process that sees only the prompt file it is given and the sources the prompt points to. No earlier context carries over, which also makes a pool call a natural fit for the Independent reviewer.
- **Metered by the wrapper, not by the agent.** Calls go through `scripts/pool.py`. It checks the budget, runs the call, and appends the call to the ledger itself: role, task, runtime, model, effort, tokens, cost, time and status. Prompts are not stored, only their hash.
- **Honest about gaps.** If a runtime does not report tokens or cost, the ledger says `unknown`; nothing is estimated. Token and cost budgets only count what was reported, so for a runtime that reports nothing, the call budget is the only one that applies.
- **Over budget is not a stop.** The wrapper refuses the call without running it and returns `no_budget`. The role then does the work itself. If the work really needs the call and the Orchestrator says wait, the role waits.

## Config

A JSON file the user owns (kept outside the plugin). No model names or prices ship with the plugin; the user writes their own entries.

```json
{
  "ledger": "ai-pool-ledger.jsonl",
  "budget": {"calls": 40, "tokens": 2000000},
  "role_budget": {"verify": {"calls": 15}},
  "entries": [
    {
      "id": "fast",
      "runtime": "my-cli",
      "model": "model-a",
      "effort": "low",
      "context_limit": 100000,
      "command": ["my-cli", "run", "--model", "{model}", "--effort", "{effort}", "--prompt-file", "{prompt_file}"],
      "usage": {"tokens_in": "usage.input", "tokens_out": "usage.output", "cost": "cost"}
    }
  ]
}
```

`command` is an argument list, never a shell string. `{prompt_file}`, `{model}` and `{effort}` are filled in; a literal brace in an argument is written `{{` or `}}`. `usage` maps tokens and cost to dotted paths in the JSON the runtime prints; leave it out for a runtime that prints none. All limits are optional.

## Use

```
python scripts/pool.py run --config ai-pool.json --entry fast --role designer --task T1 --prompt-file prompt.md
python scripts/pool.py summary --config ai-pool.json
```

`run` exits 0 on success, 1 if the call failed, 2 on bad input, 3 when refused for budget. `summary` totals the ledger by entry and role against the budget; the Orchestrator reports from it.

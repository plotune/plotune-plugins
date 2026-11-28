# AI pool

AI as a resource that Designer, Build and Verify can call when distributing work helps. It is not a set of sub-roles and no role is required to use it.

- **Stateless.** Each call is a fresh process that sees only the prompt file it is given and the sources the prompt points to. No earlier context carries over, which also makes a pool call a natural fit for the Independent reviewer.
- **Metered by the wrapper, not by the agent.** Calls go through `scripts/pool.py`. It checks the budget, runs the call, and appends the call to the ledger itself: role, task, runtime, model, effort, tokens, cost, time and status. Prompts are not stored, only their hash.
- **Honest about gaps.** If a runtime does not report tokens or cost, the ledger says `unknown`; nothing is estimated. Token and cost budgets only count what was reported, so for a runtime that reports nothing, the call budget is the only one that applies.
- **Covers a host's own subagents too, on any host.** Once a pool is defined, a role does not call the host's subagent tool unnoticed: it asks `pool.py check` first (no budget means it does the work itself) and, unless a host hook meters the call, adds a `pool.py record` row afterwards. Using the tool is allowed; it just counts.
- **Provenance is labelled.** Each row has a `source`: `wrapper` (measured by `pool.py run`), a host-hook name (measured by that host), or `self_reported` (written by an agent, unverifiable). `summary` keeps them apart. A host without hooks cannot enforce `check` and `record`; for such a host they rest on the roles following the rule, so prefer `pool.py run` there.
- **Over budget is not a stop, and the Orchestrator picks the mode.** When it sets up the pool it writes `over_budget` in the config. `reject` (the default) refuses the call without running it and returns `no_budget`; the role then does the work itself, or waits if the work really needs the call and the Orchestrator says wait. `warn` lets the call run, flags the row and the result, and leaves the Orchestrator to decide at the next checkpoint.
- **Claude Code hook.** In Claude Code, the full plugin ships `hooks/hooks.json` (editions without hooks have neither it nor its script), which runs `scripts/pool_hook.py` around Claude Code's own subagent tool. Before a call it applies the budget (deny in `reject` mode); after it, it records the call with what Claude Code reports. It does nothing unless a pool config exists (`PLOTUNE_POOL_CONFIG`, else `ai-pool.json` in the working directory), and it never blocks a session except by an explicit deny. Its rows have role `unattributed`, source `claude-code-hook` and tokens labelled `reported_final_request_only`: Claude Code reports usage of the final request, not the whole run, and a background launch reports none (`unknown`). Numbers are recorded as reported, not dug out of transcripts. Hosts without hooks, as far as verified, rely on the roles following the rule.

## Config

A JSON file the user owns (kept outside the plugin). No model names or prices ship with the plugin; the user writes their own entries.

```json
{
  "ledger": "ai-pool-ledger.jsonl",
  "over_budget": "reject",
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

`command` is an argument list, never a shell string. `{prompt_file}`, `{model}` and `{effort}` are filled in; a literal brace in an argument is written `{{` or `}}`. `usage` maps tokens and cost to dotted paths in the JSON the runtime prints; leave it out for a runtime that prints none. All limits are optional. `over_budget` is `reject` or `warn`.

## Use

```
python scripts/pool.py run --config ai-pool.json --entry fast --role designer --task T1 --prompt-file prompt.md
python scripts/pool.py check --config ai-pool.json --role designer
python scripts/pool.py record --config ai-pool.json --role designer --task T1 --model model-a --tokens-in 1200 --tokens-out 300
python scripts/pool.py summary --config ai-pool.json
```

`run` and `check` exit 0 on success, 3 when over budget in `reject` mode (in `warn` mode they exit 0 and report the warning) (`run` also 1 if the call failed, 2 on bad input). `record` adds a self-reported row for a call the wrapper did not run; its numbers are optional and unlabelled numbers are never invented. `summary` totals the ledger by entry, role and source against the budget; the Orchestrator reports from it.

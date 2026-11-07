## What and why

<!-- What does this change, and why? Link an issue if there is one. -->

## Checklist

- [ ] If a plugin's files changed: bumped its version with `python tools/bump_version.py <plugin> <version> --note "..."` (updates every manifest, the README table and the changelog)
- [ ] `python tools/check_manifests.py`, `check_skills.py`, `check_evals.py` and `sync_opencode.py --check` pass
- [ ] Tests pass (`python -I -m unittest discover -s tools/tests`, `node --test tools/tests/opencode-adapter.test.mjs`, and the plugin's own tests)
- [ ] Skill or MCP behaviour changed: ran the plugin's evals (`claude plugin eval .` in the plugin folder) and noted the result
- [ ] No secrets, tokens or personal URLs in the diff

# Contributing

Thanks for helping. Plugin changes are small and mechanical; the tooling in `tools/` does most of the bookkeeping and CI on pull requests checks the rest.

## Set up

You need Python 3.12+ and Node 22+. Nothing to install: the tooling uses only the standard library.

```bash
git clone https://github.com/plotune/plotune-plugins && cd plotune-plugins
python -I -m unittest discover -s tools/tests     # tool tests
node --test tools/tests/opencode-adapter.test.mjs                          # OpenCode adapter test
```

## Changing a plugin

1. Edit files under `plugins/<name>/`.
2. **Bump the version** (Claude Code users only receive a change when the version goes up):
   ```bash
   python tools/bump_version.py <name> <new-version> --note "what changed"
   ```
   Use a patch bump for fixes, minor for new skills or behaviour, major for breaking changes. This updates every manifest, the README table and `CHANGELOG.md` together.
3. Run the checks listed in [AGENTS.md](AGENTS.md). CI runs the same ones.
4. Open a pull request. Merging to `main` is the release: the `release` workflow tags `<plugin>--v<version>` and publishes a GitHub Release from the changelog.

Changes that only touch a plugin's `README.md`, `CHANGELOG.md`, `tests/` or `evals/` need no bump (users do not receive those as behaviour).

## Adding a plugin

See [docs/adding-a-plugin.md](docs/adding-a-plugin.md).

## Skills

Each skill is `skills/<name>/SKILL.md`. The frontmatter `name` must equal the folder name and the `description` (≤ 1024 characters) should say *when to use it*. `python tools/check_skills.py` enforces both.

## Evals

`plugins/<name>/evals/<case>/` holds behaviour tests for `claude plugin eval`: a `prompt.md` written the way a user would type it, and graders in `graders/` (prefer the free `regex`, `tool_used` and `tool_order` graders; use `llm` for short answers). `python tools/check_evals.py` catches the mistakes that would make a case silently meaningless, including invalid YAML quoting.

Run a suite by hand before a release or after changing a skill. It calls a model and costs money, so cap it:

```bash
cd plugins/<name>
claude plugin eval . --runs 1 --ablation none --max-cost-usd 2 --no-publish
```

Results land in `evals/results/`, which is git-ignored.

You can also run them in CI: Actions → **evals** → *Run workflow* (needs an `ANTHROPIC_API_KEY` repository secret; without one the job exits after printing a notice). It is manual and cost-capped, never automatic.

## Security and conduct

Report vulnerabilities privately (see [SECURITY.md](SECURITY.md)). Everyone is expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

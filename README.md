# Plotune Plugins

Plugin marketplace for [Plotune](https://github.com/plotune), usable from **Claude Code**, **GitHub Copilot CLI** and **OpenAI Codex**. One repository, one shared plugin body per plugin, thin per-platform manifests.

## Plugins

| Plugin | Version | What it does |
|---|---|---|
| [`plotune-requirements`](plugins/plotune-requirements) | 0.8.2 | Portable continuous requirements engineering: Draft decomposition, independent approval governance, review, change impact and multi-agent delivery. |

## Install

### Claude Code

```
/plugin marketplace add plotune/plotune-plugins
/plugin install plotune-requirements@plotune-plugins
```

Update with `/plugin marketplace update plotune-plugins`. Background auto-update is off by default; turn it on under **Marketplaces** in `/plugin`.

### GitHub Copilot CLI

```
copilot plugin marketplace add plotune/plotune-plugins
copilot plugin install plotune-requirements@plotune-plugins
```

Update with `copilot plugin marketplace update plotune-plugins`.

### Codex

```
codex plugin marketplace add plotune/plotune-plugins
```

Then install `plotune-requirements` from the Plotune Plugins marketplace in Codex. Refresh with `codex plugin marketplace upgrade plotune-plugins`.

## Repository layout

```
.claude-plugin/marketplace.json     Claude Code + Copilot CLI catalog
.agents/plugins/marketplace.json    Codex catalog
plugins/<name>/
  .claude-plugin/plugin.json        Claude Code + Copilot CLI manifest (source of truth for name/version)
  .codex-plugin/plugin.json         Codex manifest (same name/version)
  skills/ ...                       shared content
tools/check_manifests.py            drift check, run in CI
```

## Releasing a plugin update

1. Change the plugin files.
2. Bump `version` in **both** manifests of that plugin and add a `CHANGELOG.md` entry. Never set `version` in a catalog entry.
3. Run `python tools/check_manifests.py` and `claude plugin validate .`.
4. Merge to `main`. Users get the update on their next marketplace update.
5. Optionally tag `plotune-requirements--v<version>`.

Claude Code only delivers an update when `version` changes, so always bump it.

## Adding a plugin

See [docs/adding-a-plugin.md](docs/adding-a-plugin.md).

## License

Apache-2.0, see [LICENSE](LICENSE).

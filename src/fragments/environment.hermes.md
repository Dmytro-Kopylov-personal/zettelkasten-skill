## Environment (Hermes)

**Resolve the vault path before calling file tools.** They do not expand shell variables — never
pass a path containing `$ZETTELKASTEN_VAULT_PATH` to `read_file`, `write_file`, `patch` or
`search_files`. Resolve it first with `terminal`, then pass a concrete absolute path. Vault paths
frequently contain spaces, which is a second reason to prefer file tools over shell commands.

**Prefer** `search_files` over `grep`/`find`/`ls`, and `read_file` over `cat` — it paginates and
returns line numbers.

**Deterministic checks.** Run the bundled linter with `terminal`:

```bash
python3 "${HERMES_HOME:-$HOME/.hermes}/skills/research/zettelkasten/scripts/zettel_lint.py" "<vault>" --json
```

If `terminal` or Python is unavailable, follow `references/tool-free-fallback.md`.

**This session will not see the skill after you install or edit it.** The skill loader is
initialised at session start; a freshly written skill is invisible until a new session.
`/reload-skills` re-scans without restarting.

**Pin it against the curator.** A background curator acts on agent-created skills and can archive
them. `hermes curator pin zettelkasten` exempts this one.

## Environment (Copilot)

**Resolve the vault path before touching anything** — from the request, from the
`ZETTELKASTEN_VAULT_PATH` environment variable, or by looking upward from the working directory for
a folder holding both `SCHEMA.md` and `permanent/`. If none of those resolves it, ask. Do not guess
and do not write into a folder you have not confirmed is a vault.

**Deterministic checks may be unavailable.** On a locked-down machine you may not be able to run the
bundled Python linter. Run it when you can:

```bash
python3 scripts/zettel_lint.py "<vault>" --json
```

When you cannot, follow `references/tool-free-fallback.md` exactly. That path is not a lesser one:
it is the same checks performed by hand, and you must report which checks you were unable to
perform rather than reporting a clean result.

**Reference files load only when referenced.** Use relative paths from this file, with forward
slashes. Nothing in `references/` or `templates/` reaches you otherwise.

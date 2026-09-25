## Environment (Claude Code)

**Resolve the vault path before calling file tools**, and pass a concrete absolute path. Vault paths
may contain spaces, so prefer Read/Glob/Grep over shell commands for anything inside the vault.

**Search before writing.** Glob and Grep across `permanent/` for the entities and ideas in play
before proposing a new note — this is what stops duplicate notes under different slugs.

**Deterministic checks.** Run the bundled linter with Bash:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/zettel_lint.py" "<vault>" --json
```

If Bash is unavailable or Python is missing, follow `references/tool-free-fallback.md`.

**Reference files load on demand** — read one only when the task needs it, and by relative path
from this file.

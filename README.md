# zettelkasten-skill

A portable agent skill that turns an agent into a **Zettelkasten maintainer**: raw sources
compile into atomic, densely-linked, provenance-carrying permanent notes.

One capability, three platforms — [Hermes](https://github.com/) (primary),
Claude Code, and GitHub Copilot — assembled from a shared body plus a thin
per-platform seam, so the same skill behaves the same way wherever it runs.

## What it does

| Operation | Contract |
|---|---|
| **init** | Scaffold a vault: `raw/`, `permanent/`, `structure/`, `inbox/`, `SCHEMA.md`, `log.md` |
| **ingest** | Capture a source with a `sha256`, discuss it, search first, **propose a plan**, then write |
| **query** | Search, read notes in full, answer with note IDs, and file only genuine synthesis |
| **lint** | Report, never auto-fix. Structural errors first, then orphans, decay, advisory |

The difference from a wiki is atomicity: a wiki has a page per *thing*, a Zettelkasten has
a note per *idea*, and the value lives in the links. The skill's central rule is that an
ingest **proposes before it writes** — the user approves, the agent compiles.

## Layout

```
src/          render sources, never shipped
  SKILL.template.md      the shared body, with {{FRONTMATTER}} and {{ENVIRONMENT}} seams
  render.py              stdlib-only renderer + fail-closed per-platform validator
  fragments/             frontmatter.<platform>.yaml, environment.<platform>.md
skill/        the shipped payload: references/, templates/, scripts/
tests/        golden renders, invariants, fixtures, real-validator adapters
docs/         design notes, the plan, and measured results
```

`skill/SKILL.md` is deliberately **not** in git: the committed render lives in
`tests/golden/<platform>.SKILL.md`, which is both the reviewable artifact and the
byte-exact oracle `--check` diffs against. One copy, two jobs, no drift.

## Use

```bash
make check     # render all three platforms and diff against tests/golden/
make test      # the full suite (uv run --with pytest --with pyyaml)
make render    # write renders to dist/
```

No virtualenv, no `pip install`, no third-party imports: `render.py` and the bundled
linter are stdlib-only single files, so they run wherever a Python 3 exists. The test
suite is the only part that wants `uv`, and it uses it to fetch its own dependencies.

## Why it is built this way

Four findings came from running the platforms' own code rather than trusting the spec.
Each one changed the design, and each is pinned by a test:

- **`platforms:` in Hermes is an OS gate, not an agent gate.** `platforms: [copilot, hermes]`
  reads perfectly reasonably and makes the skill invisibly absent on every machine. The
  Hermes fragment declares `[linux, macos, windows]`, and a test refuses anything else.
- **Hermes shows roughly the first 53 characters of the description** in its catalog. That
  truncated string is the entire discovery surface, so the trigger verbs are front-loaded,
  and a test fails if they stop being visible.
- **Three platforms, three different frontmatter contracts.** Anthropic's own
  `quick_validate.py` rejects Hermes house style (`version`, `author`, `platforms`), so
  the per-platform seam is a requirement, not a preference.
- **No tool names in the shared body.** The body is written in capability language
  ("read the note", never `` `read_file` ``), and a denylist enforces it over the
  template and every shipped reference file — with a positive and a negative control, so
  neither a check that flags everything nor one that flags nothing can pass.

The same reasoning drives the linter: it is verified against hand-labelled fixtures whose
`MANIFEST.md` is written before the code runs, and a check that cannot run says so in
`skipped_checks` rather than reporting a clean result.

## Status

Early. The render layer and its tests are complete and green; the linter, installer and
platform acceptance runs are in progress. `docs/plan.md` carries the phase gates, and
`docs/results.md` records what has actually been measured.

## Licence

MIT — see `LICENSE`.

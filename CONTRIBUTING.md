# Contributing

The repo layout, how to build and test it, and the standard a change has to meet before it lands.
The user-facing material is in the [README](README.md).

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

`tests/golden/<platform>.SKILL.md` is the committed render: both the reviewable artifact and the
byte-exact oracle `--check` diffs against. `skill/SKILL.md` is committed too, because this repo
doubles as a Claude Code plugin and a plugin must ship a loadable `SKILL.md` — a gitignored one
installs as zero skills. A test asserts the two are byte-identical, so the golden stays the source
of truth rather than becoming one of two.

`docs/architecture.md` draws the shape: one body assembled into three renders, and exactly where
the three contracts pull apart.

## Build and test

```bash
make check     # render all three platforms and diff against tests/golden/
make test      # the full suite (uv run --with pytest --with pyyaml)
make render    # write renders to dist/
make goldens   # adopt the current renders as the oracle — then read the diff
```

`make test` is the only target that wants `uv`, and it uses it to fetch its own dependencies.
Everything shipped is stdlib-only: `render.py` and `zettel_lint.py` are single files that run
wherever a Python 3 exists.

The platform acceptance run is not part of the suite, because it calls a model:

```bash
python3 tests/acceptance/run_ingest.py --runs 3 --json /tmp/ingest.json
python3 tests/acceptance/run_ingest.py --rescore /tmp/ingest.json   # no model calls
```

It builds a throwaway vault by performing Init literally, hands a real agent a source from outside
it, and scores the result with the shipped linter plus four protocol markers read out of the session
record. `--rescore` recomputes the transcript markers from stored sessions, so a correction to how
the transcript is read costs nothing to apply.

`make eval-claude` runs the Claude Code eval instead, and it also costs money. Read the comment
above it in the `Makefile` before changing a flag: the recorded run cost $7.54, and
`--max-cost-usd` is the only thing bounding the bill.

## Version declarations

Six files carry the version and **nothing cross-checks them**, so a bump means editing two and
regenerating the rest:

| Edit by hand | Regenerated from the fragment |
|---|---|
| `src/fragments/frontmatter.hermes.yaml` | `tests/golden/hermes.SKILL.md` |
| `src/fragments/frontmatter.claude.yaml` | `tests/golden/claude.SKILL.md` |
| `.claude-plugin/plugin.json` | `skill/SKILL.md` |

Then `make goldens`, rebuild `skill/SKILL.md` (`make skill/SKILL.md`), and `make check`. Copilot's
fragment declares no version, so its render is untouched by a bump. The whole diff should be version
lines and nothing else — if it is not, something else moved.

## Why it is built this way

`docs/design.md` records the findings that changed the design, each with what established it — a
line in a platform's own source, an executed validator, or a run that went wrong. These are the ones
that shape daily work.

- **`platforms:` in Hermes is an OS gate, not an agent gate.** `platforms: [copilot, hermes]` reads
  perfectly reasonably and makes the skill invisibly absent on every machine. The Hermes fragment
  declares `[linux, macos, windows]`, and a test refuses anything else.
- **Hermes truncates the description to 57 characters in its catalog**, appending an ellipsis. That
  truncated string is the entire discovery surface, so the trigger verbs are front-loaded and a test
  fails if they stop landing inside the first 53.
- **Three platforms, three different frontmatter contracts.** Anthropic's own `quick_validate.py`
  rejects Hermes house style (`version`, `author`, `platforms`), so the per-platform seam is a
  requirement rather than a preference.
- **No tool names in the shared body.** The body is written in capability language ("read the note",
  never `` `read_file` ``), and a denylist enforces it over the template and every shipped reference
  file — with a positive and a negative control, so neither a check that flags everything nor one
  that flags nothing can pass.
- **Naive wikilink scanning false-positives on contact.** `[[500, 375]]` from a NumPy expression
  inside a code fence is the top match in a real vault, and `[[wikilinks]]` in prose *describing*
  wikilinks is the second. Code fences and inline code are stripped before extraction, and a fixture
  of four such traps asserts they stay silent.
- **Hermes' frontmatter parser has a degraded path that hides the skill.** When PyYAML is missing —
  or any single line raises — it splits every line on its first colon, so
  `platforms: [linux, macos, windows]` parses as the *string* `"[linux, macos, windows]"`, which no
  OS name starts with. The gate wraps it in a one-element list, nothing matches, and the skill is
  silently absent: the first failure through a second door. This one did **not** change the design —
  every other OS-gated skill in a Hermes tree declares it the same way, so the degraded parser hides
  all of them and the remedy is upstream. It changed the tests instead: one asserts the shipped
  render parses under the installed parser to a real list, and a control forces the fallback and
  asserts it really does hide the skill.
- **A note one directory deep was invisible.** `permanent/` was scanned with a flat `glob("*.md")`
  while `raw/` and `inbox/` used `rglob`, so a note filed in a subdirectory was not collected — and
  the run then reported *0 notes, no findings*, exit 0, which reads exactly like a clean vault. That
  is the failure this whole repository is built to catch, and it was in the repository. `permanent/`
  now walks the tree; links resolve by note rather than by string, so `[[note]]`, `[[sub/note]]` and
  `[[note.md]]` all credit the same note and cannot produce a phantom orphan. `structure/` stays flat
  on purpose — its files have fixed names and roles, so a nested `index.md` is a sub-list, not the
  index.

## Adding a check means adding a way for it to fail

The linter is verified against hand-labelled fixtures whose `MANIFEST.md` is written before the code
runs, and a check that cannot run says so in `skipped_checks` rather than reporting a clean result.
Matching a manifest is not enough on its own — it shows the right findings appeared, not that the
right *check* produced them — so each expected finding is attributed by silencing its check in the
registry and requiring exactly that check's findings to disappear.

Every instrument here carries a control in the opposite direction, so a check that flags everything
and one that flags nothing cannot both pass. `docs/design.md` says why, at length, and
`docs/results.md` records what each control caught. **That is the standard this repo holds itself to,
and it is the most useful thing to read before changing `zettel_lint.py`.**

Two rules that are not negotiable in the linter:

- **No write path, and no `--fix`.** A test reads every shipped script looking for a write call and
  fails if it finds one, and a second test hashes the whole fixture tree before and after a full lint
  run. `raw/` is never written; `hash` computes over bytes so a decode/re-encode round trip cannot
  change a digest.
- **A parse failure never resolves to an empty dict.** That is the other vacuous-pass failure mode:
  Hermes' own parser falls back to splitting on `:`, which makes every frontmatter check pass
  silently. Ours returns `(data, error, line)`, excludes the file from dependent checks, and emits
  `ZK002`.

## The commit hook

**`.githooks/commit-msg` rejects any `Co-authored-by:` trailer.** It is tracked in the repo but not
active by default, because `core.hooksPath` is local configuration rather than something a clone
inherits. Turn it on if you want your commits checked before they land:

```bash
git config core.hooksPath .githooks
```

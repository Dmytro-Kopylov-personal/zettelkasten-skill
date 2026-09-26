# zettelkasten-skill

A portable agent skill that turns an agent into a **Zettelkasten maintainer**: raw sources
compile into atomic, densely-linked, provenance-carrying permanent notes.

One capability, three platforms — Hermes, Claude Code, and GitHub Copilot — assembled from a
shared body plus a thin per-platform seam, so the same skill behaves the same way wherever it
runs.

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

A vault is also a **folder of its own**. `init` creates `zettelkasten/` rather than adopting
the directory it runs in, and the vault root is the only place the skill writes. Ingest is
designed to *update* existing notes, so a vault sharing a directory with other work would
edit files it never created; keeping the vault self-contained makes that impossible rather
than merely discouraged.

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

## Install

```bash
./install.sh --platform hermes          # detect the root if you leave --platform out
./install.sh --platform copilot --project-root /path/to/repo
./install.sh --platform claude --dry-run
```

It renders, validates, then copies `SKILL.md`, `references/`, `templates/` and `scripts/`
into the platform's skills tree. Re-running it is a no-op; a file it did not write is
**refused** (exit 4) rather than overwritten, and a file it did write is backed up to
`.bak.<utc>` before being replaced. Ownership is recorded as a digest manifest in
`${XDG_STATE_HOME:-$HOME/.local/state}/zettelkasten-skill/` — outside every skills tree, so
an OS-level backup cannot carry it into a vault.

Exit codes: 0 ok · 1 render failure · 2 usage · 3 platform not detected · 4 unmanaged file.

A skills root that does not exist yet needs `--force`, which creates it. That is the only
thing `--force` does — it never overrides a refusal, because the remedy for an unmanaged file
is a person moving it, not a flag.

Copilot has two locations, and they are different scopes:

```bash
./install.sh --platform copilot --force                    # personal: ~/.copilot/skills/
./install.sh --platform copilot --project-root /path/repo  # project: /path/repo/.github/skills/
```

Install **one** personal copy per machine. Copilot's own help text also lists a project's
`.claude/skills/` among the sources it reads, so a repo already carrying the Claude render
might not need a second copy — untested here, and `copilot skill list` answers it before you
install twice.

Copilot CLI can also take a URL — `copilot skill add <https://…/SKILL.md>` — and **that path
gives you a broken install.** It fetches a single `SKILL.md` and materialises nothing else, so
the skill would load with its `references/`, `scripts/` and `templates/` all missing: a body
that tells the agent to read files that are not there, and a linter that does not exist. Use
`install.sh`, or clone the repo and point `copilot skill add` at the directory instead.

Verified after installing: `copilot skill list` prints the skill under *Personal skills* with
its description untruncated, discovered from `~/.copilot/skills/`. **Unverified:** the VS Code
extension and the Copilot cloud agent were never exercised here. The CLI listing is the only
discovery claim this repo makes.

## Use

```bash
make check     # render all three platforms and diff against tests/golden/
make test      # the full suite (uv run --with pytest --with pyyaml)
make render    # write renders to dist/
make goldens   # adopt the current renders as the oracle — then read the diff
```

The platform acceptance run is not part of the suite, because it calls a model:

```bash
python3 tests/acceptance/run_ingest.py --runs 3 --json /tmp/ingest.json
python3 tests/acceptance/run_ingest.py --rescore /tmp/ingest.json   # no model calls
```

It builds a throwaway vault by performing Init literally, hands a real agent a source from
outside it, and scores the result with the shipped linter plus four protocol markers read out
of the session record. `--rescore` recomputes the transcript markers from stored sessions, so
a correction to how the transcript is read costs nothing to apply.

The linter runs against a vault directly, with no install step at all:

```bash
python3 -I skill/scripts/zettel_lint.py /path/to/vault --json
```

No virtualenv, no `pip install`, no third-party imports: `render.py` and the bundled
linter are stdlib-only single files, so they run wherever a Python 3 exists. The test
suite is the only part that wants `uv`, and it uses it to fetch its own dependencies.

## Why it is built this way

Six findings came from running the platforms' own code rather than trusting the spec. Five
changed the design; the sixth changed what the tests check instead. Each is pinned:

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
- **Naive wikilink scanning false-positives on contact.** `[[500, 375]]` from a NumPy
  expression inside a code fence is the top match in a real vault, and `[[wikilinks]]` in
  prose *describing* wikilinks is the second. Code fences and inline code are stripped
  before extraction, and a fixture of four such traps asserts they stay silent.
- **Hermes' frontmatter parser has a degraded path that hides the skill.** When PyYAML is
  missing — or any single line raises — it splits every line on its first colon, so
  `platforms: [linux, macos, windows]` parses as the *string* `"[linux, macos, windows]"`,
  which no OS name starts with. The gate wraps it in a one-element list, nothing matches, and
  the skill is silently absent: the V1 failure through a second door. This one did **not**
  change the design — all 85 OS-gated skills in a Hermes tree declare it the same way, so the
  degraded parser hides every one of them and the remedy is upstream. It changed the tests
  instead: one asserts the shipped render parses under the installed parser to a real list,
  and a control forces the fallback and asserts it really does hide the skill.

The same reasoning drives the linter: it is verified against hand-labelled fixtures whose
`MANIFEST.md` is written before the code runs, and a check that cannot run says so in
`skipped_checks` rather than reporting a clean result. Matching a manifest is not enough
on its own — it shows the right findings appeared, not that the right *check* produced
them — so each expected finding is attributed by silencing its check in the registry and
requiring exactly that check's findings to disappear.

## Status

The render layer, the linter and the installer are complete and green (**518 tests**), and the
skill is installed and discovered on all three platforms:

| Platform | Installed to | Discovery verified by | Ingest acceptance |
|---|---|---|---|
| Hermes | `~/.hermes/skills/research/zettelkasten/` | `hermes skills list`, and a live session's system prompt | **3/3** runs, zero findings |
| Claude Code | `~/.claude/skills/zettelkasten/` | `Loaded N unique skills` moving 1 → 0 → 1, and a headless init event naming it | ablation run — see the caveat |
| Copilot CLI | `~/.copilot/skills/zettelkasten/` | `copilot skill list`, description untruncated | not run |

`docs/results.md` carries the measurements; `docs/plan.md` the phase gates.

**Two caveats, stated rather than buried.** Copilot's VS Code extension and cloud agent were
never exercised — the CLI listing is the only discovery claim made here. And the Claude
ablation's aggregate is misleading read alone: both cases score 1.00 with the skill and below
threshold without, but each delta rests on a single grader that tests a *naming convention*,
so it demonstrates less than "the skill works" (V8, `docs/design.md`). Every run in it
executed as `deepseek-flash`, not Claude.

## Licence

MIT — see `LICENSE`.

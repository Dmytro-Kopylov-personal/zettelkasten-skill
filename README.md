# zettelkasten-skill

A portable agent skill that turns an agent into a **Zettelkasten maintainer**: raw sources
compile into atomic, densely-linked, provenance-carrying permanent notes.

One capability, three platforms — Hermes, Claude Code, and GitHub Copilot — assembled from a
shared body plus a thin per-platform seam, so the same skill behaves the same way wherever it
runs.

**New here? → [Getting started](GETTING-STARTED.md)** — install, your first vault, a worked ingest
with real output, and what a good note looks like.

## Your files

This skill writes into a vault you own, so what it will and will not touch matters more than
anything below.

**Nothing reaches `permanent/` before you approve a plan.** Ingest captures the source, searches
the vault for notes already covering the same ground, then shows you what it intends to create —
titles, one-line theses, and the links between them — and waits. If the plan is wrong, you say so
and it revises.

**No bundled script writes anything at all.** There is no `--fix`, deliberately: the mechanically
fixable findings are exactly where a wrong edit corrupts a vault quietly. The linter reports, the
agent proposes, you approve. This is not a policy statement — a test hashes the whole fixture tree
before and after a full lint run and fails if a single byte moved, and a second test reads every
shipped script looking for a write call and fails if it finds one. Both carry a control in the
opposite direction, so neither a proof that had stopped noticing writes nor a scan that had stopped
recognising them could pass quietly.

**`raw/` is captured once and never edited again.** A source records a `sha256` at capture and the
linter compares the file against its own digest. When they differ it *reports* drift; it never
repairs it in place. A correction belongs in a note, and a source that changed belongs in a
re-ingest.

**A contradiction never overwrites.** Conflicting evidence gets its own note with a `contradicts`
link and dates on both sides, because editing the old claim into agreement destroys the thing the
vault is for.

**The installer backs up what it replaces and refuses what it did not write.** A file it wrote is
copied to `.bak.<utc>` before being replaced. A file it did not write halts the install with exit
4 and a list of the paths; the remedy is a person moving them and there is no flag that overrides
it.

**The vault root is the boundary.** `init` gives a vault its own folder rather than adopting the
directory it runs in, because a vault sharing a directory with other work puts all of it inside the
blast radius — and ingest, which updates existing notes, would then edit files it never created.

One honest limit: that boundary is a rule the body states and a grader checks, not a sandbox. The
agent runs with your permissions, as agents do. If you want a wall rather than a checked contract,
point it at a directory whose only contents are the vault.

## What it does

| Operation | Contract |
|---|---|
| **init** | Scaffold a vault: `raw/`, `permanent/`, `structure/`, `inbox/`, `SCHEMA.md`, `log.md` |
| **ingest** | Capture a source with a `sha256`, discuss it, search first, **propose a plan**, then write |
| **query** | Search, read notes in full, answer with note IDs, and file only genuine synthesis |
| **lint** | Report, never auto-fix. Structural errors first, then orphans, decay, advisory |

The difference from a wiki is atomicity: a wiki has a page per *thing*, a Zettelkasten has a note
per *idea*, and the value lives in the links. A note carries typed link verbs — `extends`,
`supports`, `contradicts`, `source`, `applies`, `supersedes` — because "see also" claims nothing,
and a folder of beautifully written unlinked notes is a pile. Lint will say so.

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
installs as zero skills. A test asserts the two are byte-identical, so the golden stays the
source of truth rather than becoming one of two.

`docs/architecture.md` draws the shape: one body assembled into three renders, and exactly where
the three contracts pull apart.

## Install

### Claude Code

```bash
claude plugin marketplace add Dmytro-Kopylov-personal/zettelkasten-skill
claude plugin install zettelkasten@zettelkasten-skill
```

In a session, the same thing as `/plugin marketplace add` and `/plugin install`. Verified end to
end: after installing, a headless session's own init event lists `zettelkasten:zettelkasten`
among its skills.

### Everywhere else

```bash
git clone https://github.com/Dmytro-Kopylov-personal/zettelkasten-skill.git
cd zettelkasten-skill

./install.sh --platform claude --dry-run --force   # what would change, writing nothing
./install.sh --platform claude --force             # then for real; or copilot, or hermes
```

`--dry-run` names the destination directory, counts what would be written, backed up and left
alone, and writes nothing — not one file, not even its bookkeeping manifest. On a first install it
needs `--force` as well, which there only permits *looking* at a skills directory that does not
exist yet. Omit `--platform` to detect what you have.

It renders, validates, then copies `SKILL.md`, `references/`, `templates/` and `scripts/` into the
platform's skills tree. Re-running it is a no-op; a file it did not write is **refused** (exit 4)
rather than overwritten, and a file it did write is backed up to `.bak.<utc>` before being replaced.
Ownership is recorded as a digest manifest in
`${XDG_STATE_HOME:-$HOME/.local/state}/zettelkasten-skill/` — outside every skills tree, so an
OS-level backup cannot carry it into a vault.

Exit codes: 0 ok · 1 render failure · 2 usage · 3 platform not detected · 4 unmanaged file.

**`--force` is needed on a first install**, because the platform's skills directory usually does not
exist until the agent has run once, and the installer will not invent one — a missing root may mean
the platform is not installed at all. `--force` creates that one directory and nothing else. It
never overrides a refusal: the remedy for an unmanaged file is a person moving it, not a flag.

Copilot has two locations, and they are different scopes:

```bash
./install.sh --platform copilot --force                    # personal: ~/.copilot/skills/
./install.sh --platform copilot --project-root /path/repo  # project: /path/repo/.github/skills/
```

Install **one** personal copy per machine. Copilot's own help text also lists a project's
`.claude/skills/` among the sources it reads, so a repo already carrying the Claude render might not
need a second copy — untested here, and `copilot skill list` answers it before you install twice.

Copilot CLI can also take a URL — `copilot skill add <https://…/SKILL.md>` — and **that path gives
you a broken install.** It fetches a single `SKILL.md` and materialises nothing else, so the skill
would load with its `references/`, `scripts/` and `templates/` all missing: a body that tells the
agent to read files that are not there, and a linter that does not exist. Use `install.sh`, or clone
the repo and point `copilot skill add` at the directory instead.

## Use

```bash
make check     # render all three platforms and diff against tests/golden/
make test      # the full suite (uv run --with pytest --with pyyaml)
make render    # write renders to dist/
make goldens   # adopt the current renders as the oracle — then read the diff
```

The linter runs against a vault directly, with no install step at all:

```bash
python3 -I skill/scripts/zettel_lint.py /path/to/vault --json
```

No virtualenv, no `pip install`, no third-party imports: `render.py` and the bundled linter are
stdlib-only single files, so they run wherever a Python 3 exists. The test suite is the only part
that wants `uv`, and it uses it to fetch its own dependencies.

The platform acceptance run is not part of the suite, because it calls a model:

```bash
python3 tests/acceptance/run_ingest.py --runs 3 --json /tmp/ingest.json
python3 tests/acceptance/run_ingest.py --rescore /tmp/ingest.json   # no model calls
```

It builds a throwaway vault by performing Init literally, hands a real agent a source from outside
it, and scores the result with the shipped linter plus four protocol markers read out of the session
record. `--rescore` recomputes the transcript markers from stored sessions, so a correction to how
the transcript is read costs nothing to apply.

## Obsidian

A vault is plain Markdown — `.md` files, YAML frontmatter, `[[wikilinks]]` — so **open the folder as
an Obsidian vault and it works.** Obsidian's out-of-the-box settings are the ones this skill writes:
wikilinks rather than Markdown links, and the shortest link format, which is exactly
`[[202609251200-slug]]`. Notes may be filed into subdirectories of `permanent/`, and a link resolves
by name alone, so it finds its note wherever it sits. Callouts, `%%comments%%`, dataview fences,
`^block-id` references, `![[embeds]]` and the `.obsidian/` directory are all handled — embeds are
link-checked like any other link, and code fences are stripped before links are read, which is the
same rule Obsidian applies.

Three things to know rather than discover:

- **`^[raw/articles/x.md]` renders as an inline footnote.** Obsidian's lexer reads `^[` as the start
  of one, unconditionally — no setting turns it off. In reading view a provenance marker becomes a
  superscript and the cited paths collect in the footnote block. Nothing breaks: the file is
  untouched and the linter reads the file, not the render. It is arguably a good rendering of
  provenance. The syntax is load-bearing, so it stays.
- **`links:` has no Properties-panel editor.** Obsidian's property types are text, number, checkbox,
  date, datetime, list and tags; there is no list of objects, so the panel shows this one as raw
  YAML. The data is intact and every check reads it — it simply cannot be edited from the panel.
- **Quote the `id`.** Unquoted, `id: 202609261430` infers as `Number` and the panel offers to edit it
  as one. `id: "202609261430"` is `Text`. Both parse and lint identically; the skeleton and the
  format reference use the quoted form.

## Why it is built this way

`docs/design.md` records the findings that changed the design, each with what established it — a line
in a platform's own source, an executed validator, or a run that went wrong. These are the ones that
shape daily use.

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

The same reasoning drives the linter: it is verified against hand-labelled fixtures whose
`MANIFEST.md` is written before the code runs, and a check that cannot run says so in
`skipped_checks` rather than reporting a clean result. Matching a manifest is not enough on its own —
it shows the right findings appeared, not that the right *check* produced them — so each expected
finding is attributed by silencing its check in the registry and requiring exactly that check's
findings to disappear.

## What has not been verified

Stated here rather than left for you to find out.

**Copilot's VS Code extension and cloud agent were never exercised.** Only the CLI was, and the
listing there is the only discovery claim this repo makes.

**Copilot CLI's discovery of a project-local `.claude/skills/` is untested**, which is why the README
suggests checking before installing a second copy.

**The ablation is weaker than it looks.** Both eval cases score 1.00 with the skill and below
threshold without, but each delta rests on a single grader that tests a *naming convention*, so it
demonstrates less than "the skill works" — an agent with no skill loaded still indexed, logged,
linked and contained itself. Every run in it executed as `deepseek-flash`, not Claude. The run trees
showing this are kept, and `docs/results.md` records the measurement.

**The agent can ignore the protocol.** A loaded skill is not a followed skill. Lint makes drift
detectable after the fact — that is the mitigation, not a guarantee.

`docs/results.md` carries the measurements and every unverified marker; `docs/plan.md` the phase
gates.

## A note for contributors

**`.githooks/commit-msg` rejects any `Co-authored-by:` trailer.** It is tracked in the repo but not
active by default, because `core.hooksPath` is local configuration rather than something a clone
inherits. Turn it on if you want your commits checked before they land:

```bash
git config core.hooksPath .githooks
```

**Adding a check means adding a way for it to fail.** Every instrument here carries a control in the
opposite direction, so a check that flags everything and one that flags nothing cannot both pass —
`docs/design.md` says why, at length, and `docs/results.md` records what each control caught. That is
the standard this repo holds itself to, and it is the most useful thing to read before changing
`zettel_lint.py`.

## Licence

MIT — see `LICENSE`.

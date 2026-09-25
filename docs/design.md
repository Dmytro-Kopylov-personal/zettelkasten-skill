# Design

Why this repo looks the way it does. Every claim here is either something a platform's own
code did when run, or a decision taken in response to it.

## The divergence that is the project

The nearest existing skill, `llm-wiki`, is source-compilation shaped: one page per *thing*.
This skill is one note per *atomic idea*, with timestamp-stable IDs, typed link verbs, and
per-claim provenance. A folder of well-written unlinked notes is a pile, and the linter
says so. That is the whole reason the linter exists: the spec's principles are only
enforceable if something other than the agent's judgment checks them.

## Findings that changed the design

| # | Finding | Consequence |
|---|---|---|
| V1 | `platforms:` in Hermes is an **OS gate** (`PLATFORM_MAP = {macos: darwin, linux: linux, windows: win32}`), not an agent gate. The spec's `platforms: [copilot, hermes]` makes the skill invisibly absent — no warning, it simply does not exist. Confirmed by executing the vendored matcher. | The Hermes fragment declares `[linux, macos, windows]`. `render.validate()` fails closed on anything outside that set, and a test re-derives it from the fragment. |
| V2 | Hermes shows `description[:57] + "..."` in its catalog (`skill_utils.py:518-526`). That truncated string *is* the discovery surface. | Trigger verbs are front-loaded; the render is asserted to keep `ingest`, `query`, `lint`, `init`, `zettelkasten` inside the first 53 characters. |
| V3 | Naive `[[...]]` scanning produces false positives on contact: `[[500, 375]]` from NumPy indexing inside a code fence, and `[[wikilinks]]` in prose *describing* wikilinks. | Code-fence and inline-code stripping is a correctness requirement, not a nicety, and it has named counterexamples in `vault_trap`. |
| V4 | Three platforms, three divergent contracts. Anthropic's `quick_validate.py` enforces a strict allowlist `{name, description, license, allowed-tools, metadata, compatibility}`, so Hermes house style (`version`, `author`, `platforms`) **fails** it. Copilot resolves the skill by *directory* name and documents only `name` + `description`. | Per-platform assembly is required. The seams are the frontmatter and a small environment block; everything else is shared. |
| V5 | This machine's `python3` (3.14.6) has neither PyYAML nor pytest; `uv` does. | The bundled linter and the renderer are stdlib-only, single-file, no venv. The test suite fetches its own dependencies through `uv`. |

## Assembly: seams, not forks

`src/SKILL.template.md` is the document minus two seams — `{{FRONTMATTER}}` and
`{{ENVIRONMENT}}` — filled per platform at render time. So the shared body never exists as
an unreviewable concatenation artifact, an unfilled placeholder is a loud render error
rather than a silently truncated file, and the environment block can sit exactly where it
belongs (after the overview, before the operations) instead of being appended.

The rendered `SKILL.md` is **not committed to `skill/`**. The committed copy lives in
`tests/golden/`, where it is both the human-reviewable artifact and the byte-exact oracle
that `--check` diffs against. One copy, two jobs.

`--check` and `install.sh` both call `validate()` and fail closed: an unloadable render is
never deployed.

## No tool names in the shared body

Copilot's docs never enumerate skill-visible tool names, and Microsoft's own guidance is to
describe intent rather than tools. So the shared body is written in capability language —
"read the note", never `` `read_file` `` — and each platform's environment block names its
own tools.

The spec proposed a runtime `references/tool-mapping.md` sidecar; install-time assembly
replaces it, because a mapping table that has to be consulted at runtime is a translation
layer that will drift, and because three small environment blocks are reviewable in a way
that a translation matrix is not.

The rule is enforced, not documented: `tests/test_invariants.py` scans the template and
every shipped reference file for snake_case tool identifiers (flagged bare — they never
occur in English), short common-word tool names (`Read`, `Bash`, `view`, … — flagged only
inside backticks, because "read the file" and "create a note" must survive), Claude-only
substitutions (`${CLAUDE_SKILL_DIR}`, `$ARGUMENTS`, in both bare and braced spellings), and
backtick-`!` dynamic blocks. It ships with a positive control (four violation kinds) and a
negative control (prose that must not trip), so neither a check that flags everything nor
one that flags nothing can pass.

## The linter

Single file, stdlib only, **read-only**. It verifies; the agent writes.

**The YAML parser is hand-rolled**, and that was not the first choice. Requiring PyYAML
fails on this machine (V5). "Graceful degradation" without it would silently delete the
entire frontmatter check surface — the flags-nothing failure this project is built to
avoid. A vendored parser is unreviewable and trips skill security scanners. So the subset
covers exactly what notes use, and gets a **differential oracle**: for every frontmatter
block in every fixture, `parse(text) == yaml.safe_load(text)`, run under `uv run --with
pyyaml` and **skipped with a reason, never faked**, when PyYAML is absent.

**A parse failure never resolves to an empty dict.** Hermes' own parser falls back to a
naive `split(":")` (`skill_utils.py:114-120`), which makes every frontmatter check pass
vacuously. Ours returns `(data, error, line)`, excludes the file from dependent checks, and
emits `ZK002`.

**No `--fix`, and no write path in any bundled script.** A fix mode would be a second write
path bypassing ingest's propose-then-approve contract; the highest-value findings are
semantic (which verb? one idea or two?) and unfixable mechanically; and the mechanically
fixable ones — a date bump, an index insertion — are exactly where a wrong edit corrupts
quietly. Hash drift is never auto-fixed either: `raw/` is immutable, so the remedy is a
re-ingest.

**A report must not overclaim.** `parse_failures[]` and `skipped_checks[]` are mandatory
fields of the JSON contract, so a check that could not run says so instead of disappearing
into a clean result. `ZK011` (orphan) excludes `structure/` from the inbound count —
otherwise `index.md` cures every orphan and the check is provably vacuous.

`ZK024` (provenance gaps) ships as `info` with its false positives stated rather than
discovered later: a synthesis paragraph legitimately drawing on all sources at once,
verbatim quotations, and word counts that under-count unspaced languages. The deterministic
half of provenance — *do the cited files exist* — is `ZK018` at `error`, and that is the
half worth failing CI on.

## Verification

Every instrument gets a known-answer calibration **in both directions**, the lesson from
`fly-arena`: a screen that flags everything and one that flags nothing look identical from
the inside.

- Fixtures ship a `MANIFEST.md` enumerating by hand which defect each file carries, written
  *before* the linter runs, plus `expected.json`. `vault_defects` asserts **set equality**,
  so a file carrying an unlisted defect fails even when the total matches.
- **Set equality does not prove *which* check fired.** So each expected finding is
  attributed: the code is removed from the registry, the report recomputed, and the lost
  findings must equal exactly the ones the manifest credits to it. Without this, a check
  that had quietly become a no-op would be covered by a neighbour firing on the same note.
- `vault_trap` is built from false-positive attractors **and** one genuine orphan whose only
  inbound link comes from `index.md` — it must still be flagged, so the trap cuts both ways.
- `vault_hostile` proves exclusion rather than vacuous passing: one `ZK002` per unsupported
  construct, and nothing else from that file.
- `vault_minimal` names the checks that had no surface to examine, and `vault_monoculture`
  pins the one vault-level statistic — a check whose input is absent is reported as
  not-applicable, never counted as a pass.
- `references/lint-checks.md` is asserted against the *emitter*: each code is run through
  `Finding.as_dict()` and the resulting `doc` string must resolve to a section headed with
  that code, at the severity the registry assigns it.
- Two independent implementations of the platform rules (`src/render.py`,
  `tests/support/platform_rules.py`) run over the same corpus and must agree on every
  document, good and bad. The real validators (Hermes' `_validate_frontmatter`, Anthropic's
  `quick_validate.py`) are loaded from their installed sources and run for real, each with
  its own negative control, and **skipped with a reason — never stubbed — when absent**.
- Determinism (two runs byte-identical), read-only proof (tree hash before/after), and
  install idempotency through `--target-root` so `$HOME` is never touched in tests.

## Open caveats

- **`related_skills: [obsidian, llm-wiki, start-investigation]`** resolve on this machine
  but are user-local, so they dangle in a fresh clone. Shipped as specified, recorded here.
- **Copilot cannot be fully verified here.** Copilot CLI 1.0.88 is installed and its
  `/skills list` is checkable; VS Code and the cloud agent are not, and no claim will be
  made about them beyond what was actually exercised.
- **If this skill is ever pointed at the notes vault**, its root `inbox/` collides
  conceptually with the `obsidian` skill's `investigations/{inbox,active,archived}/`, which
  states the user owns triage transitions. Two inboxes with different rules in one vault is
  a UX hazard. Recommendation: keep the Zettelkasten vault separate — the notes vault is
  project-shaped, not atomic-note-shaped.
- **A loaded skill is not a followed skill.** Mitigations are real but partial: hard gates
  lead the body, the body is ~250 lines rather than the 500 allowed, and lint makes drift
  detectable after the fact. The N=3 scripted-ingest pass rate is the only honest evidence,
  and it is not measured yet.

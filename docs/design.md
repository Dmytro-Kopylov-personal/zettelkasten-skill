# Design

Why this repo looks the way it does. Every claim here is either something a platform's own
code did when run, or a decision taken in response to it.

Decisions are recorded against *the spec* — the design brief this skill was written from,
which is not published. Its content is quoted wherever it matters, so nothing below depends
on reading it.

## The divergence that is the project

The nearest prior art is source-compilation shaped: one page per *thing*.
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
| V6 | Hermes' `parse_frontmatter` falls back to splitting every line on its first colon when PyYAML is missing **or any line raises** (`skill_utils.py:88-120`). In that mode `platforms: [linux, macos, windows]` parses as the *string* `"[linux, macos, windows]"`, the OS gate wraps it in a one-element list, no OS name starts with it, and the skill is silently absent — V1's failure through a second door. Executed the fallback to confirm; the block form fails *open* instead (empty value → "compatible with all"). | The flow form stays: all 85 OS-gated skills in this Hermes tree declare it the same way, so the degraded parser hides every one of them and the remedy is upstream, not in one fragment. Two tests replace the per-skill workaround — one asserts the shipped render parses under the installed parser to a real list, the other forces the fallback and asserts it really does hide the skill, so the guard cannot pass vacuously. |
| V7 | **`claude plugin validate` reads exactly one skill layout, and is blind to format.** Its help promises "the skills, agents, and commands in a directory", but it descends only into the **default `skills/` directory**. A `SKILL.md` at the plugin root, or in a directory named by the `skills` key, is never opened: `contents: []`, exit 0 under `--strict`. Inside the directory it does read, the checks are real but shallow — a missing description, a missing frontmatter block and unparseable YAML each fail `--strict`, while a non-kebab name, angle brackets in the description and an unrecognised `version` key pass identically to a good skill. | P6's gate as originally written — "`claude plugin validate --strict` exits 0" — is struck, because this repo ships the skill in the one layout the validator never opens (`skill/`, declared via the `skills` key), so the gate could not have inspected the thing it was gating. Replaced with two instruments calibrated in both directions: `quick_validate.py`, which fails on the broken skill and names the offending key, and discovery, proven by the `user: N` skill-load count moving 1 → 0 → 1 as the skill is installed, parked and restored. The remedy for the validator is upstream. |
| V8 | **A grader can pass without the skill, and the ablation still looks clean.** Both P6 cases scored 1.00 with and below threshold without — but reading the kept run trees, each delta rests on exactly one grader, and that grader tests a *naming convention*: `vault/permanent/*.md` in one case, `zettelkasten/SCHEMA.md` in the other. With no skill loaded, the agent still indexed, still logged, still linked seven notes, and still contained itself to a single folder. | The flags-nothing failure one layer up: not a check that cannot fail, but a check that cannot *discriminate*. An ablation whose baseline arm scores 0.67–0.75 is mostly measuring the prompt. Cases must carry at least one grader whose answer depends on something only the body supplies — an id↔filename match, a `sha256` on the captured source, a verb from the closed set, a `sources:` field — none of which a plausible-looking unskilled vault has. Recorded in `docs/results.md` with the run trees that show it. |
| V9 | **The loader and the validator disagree in both directions, and a skill with no `description` does not load at all.** Measured from the loader's own init event: a `SKILL.md` at the plugin root loads, with or without a `skills` key, and so does a directory named by `skills` — the two layouts `validate` never inspects. The loader is stricter in exactly one place, holding every other variable constant: the same directory with the same `name` loads when a description is present and vanishes from the `skills` array when it is absent, at the root and in a declared directory alike. | The V2 discovery surface has a second failure mode on a different platform, and a louder one — not a truncated trigger string, but no skill at all. Every render already requires a non-empty description and the frontmatter conformance suite asserts it per platform, so nothing changes; recorded because the reason is now known rather than assumed, and because it is the one loader rule stricter than the validator beside it. |
| V10 | **`permanent/glob("*.md")` was not recursive while `raw/rglob` and `inbox/rglob` were, so a note one directory deep was invisible.** `load_vault` collected it as nothing, `summary.notes` read 0, no check had anything to fire on, and the run exited 0 — "0 notes, no findings", which reads as a clean vault. Obsidian users file notes into subdirectories as a matter of course, and the miss is the one failure mode this repository exists to catch: a report of success that is indistinguishable from the absence of a report. | `permanent/` now recurses, and `structure/` deliberately does not — its files have fixed names and fixed roles, so nesting has no meaning to give one, and recursion there bought nothing while making a nested `index.md` a candidate for *the* index. Link resolution moved from string comparison to `Vault.resolve()`, which accepts every spelling Obsidian writes (`note`, `note.md`, `sub/note`, `permanent/sub/note`) and returns the *note*; the inbound count keys on that note rather than on the string, or a long-form link would have produced a false orphan in both ZK011 and the reported orphan rate. `vault_nested` calibrates all four mutations, one of which found that the `.md` branch had been unexercised in both the old code and the new. |

## Assembly: seams, not forks

`src/SKILL.template.md` is the document minus two seams — `{{FRONTMATTER}}` and
`{{ENVIRONMENT}}` — filled per platform at render time. So the shared body never exists as
an unreviewable concatenation artifact, an unfilled placeholder is a loud render error
rather than a silently truncated file, and the environment block can sit exactly where it
belongs (after the overview, before the operations) instead of being appended.

The rendered `SKILL.md` lives in `tests/golden/`, where it is both the human-reviewable artifact
and the byte-exact oracle that `--check` diffs against.

That was the whole arrangement until this repo became a Claude Code plugin. A plugin must ship a
loadable `SKILL.md`, and one excluded by `.gitignore` installs as **zero skills** — silently,
because the plugin itself registers fine and reports nothing wrong. So `skill/SKILL.md` is
committed after all, as the Claude render. The goal was never "one file on disk" but "no copy
that can drift unnoticed", and that is now held by a test instead of by absence: `test_golden.py`
asserts the committed payload is byte-identical to the golden, so a divergence fails in CI rather
than at a user's install.

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

Every instrument gets a known-answer calibration **in both directions**, the lesson from an
earlier project of mine: a screen that flags everything and one that flags nothing look
identical from the inside.

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

- **`related_skills` was dropped rather than shipped.** The spec's three entries name skills of
  the author's own that exist on one machine and nowhere else, so a public clone would carry
  metadata pointing at nothing. No test asserted the field and Hermes' validator does not
  require it, so it went and the goldens were regenerated without it. Recorded because the spec
  still asks for it.
- **Copilot cannot be fully verified here.** Copilot CLI 1.0.88 is installed and `copilot skill
  list` is checkable; VS Code and the cloud agent are not, and no claim will be made about them
  beyond what was actually exercised.
- **A root `inbox/` can collide with another tool's.** If a vault is also managed by a second
  skill or plugin with its own capture convention, two inboxes with different rules end up in one
  directory tree — and if that other convention hands triage transitions to the user, the two
  disagree about who moves a file. Recommendation: keep a Zettelkasten vault separate from a
  project-shaped one, and give it its own root.
- **A loaded skill is not a followed skill.** Mitigations are real but partial: hard gates
  lead the body, the body is ~250 lines rather than the 500 allowed, and lint makes drift
  detectable after the fact. The only honest evidence is the N=3 scripted ingest, which passed
  3/3 with variance confined to the notes produced (5, 5, 6) rather than to whether the protocol
  was followed — the runs are in `docs/results.md`. Three runs is a small sample, and the
  ablation beside it cannot supply a variance figure at all (finding V8).

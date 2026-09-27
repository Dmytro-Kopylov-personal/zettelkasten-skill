# Verification

What has been measured, and what has not. Each figure carries the date it was taken and the
instrument that took it; a claim that could not be checked is marked **unverified** rather than
left for you to find out. The development journal this page replaces is not shipped — what a
reader needs from it is here, and the story of building it is not.

## The fixture corpus

Every fixture is a vault with a hand-written `MANIFEST.md` enumerating, *before* the linter runs,
the defect each file carries. The suite asserts **set equality**, so a file carrying a defect
nobody predicted fails the test even when the total matches.

Measured 2026-09-27 with `python3 -I skill/scripts/zettel_lint.py --json <fixture>`:

| Fixture | Exit | Findings | Notes | What it asserts |
|---|---:|---:|---:|---|
| `vault_defects` | 1 | 20 (10 error / 7 warn / 3 info) | 27 | the exact finding set, in both directions |
| `vault_hostile` | 1 | 8 (`ZK002`) | 11 | one parse failure per unreadable file, and nothing else from that file |
| `vault_regressions` | 1 | 5 (3 error / 1 warn / 1 info) | 5 | each defect a released version got wrong, plus the control that must stay silent |
| `not_a_vault` | 2 | 3 (`ZK001`) | 0 | the exit code CI needs, with well-formed JSON still on stdout |
| `vault_resolution` | 1 | 1 (`ZK008`) | 3 | an extension-less `sources:` target resolves, and one that is genuinely absent still does not |
| `vault_trap` | 0 | 1 (`ZK010`) | 4 | five false-positive attractors produce nothing; the genuine isolate is still flagged |
| `vault_clean` | 0 | 0 | 8 | a well-formed vault is silent, with every check run |
| `vault_minimal` | 0 | 0 | 3 | 6 graph and decay checks report not-applicable rather than passing |
| `vault_nested` | 0 | 0 | 4 | notes one and two directories deep are collected; only `ZK027` is not applicable |
| `vault_foreign` | 0 | 0 | 3 | a vault that declares no vocabulary is judged on none, with 2 checks not applicable |

Thirty-eight findings across ten fixtures, and all 15 codes fire in at least one of them.

Matching a manifest proves a check *can* fire and says nothing about which check fired. So every
(fixture, code) pair in every expected set is silenced in turn — removed from the registry, the
report recomputed — and the findings that disappear must equal exactly the ones the manifest
credits to it: no more (a neighbour covering for it) and no fewer (it was doing work another check
also does). The cases are collected from the manifests themselves, so the coverage follows the
corpus rather than a list of its own.

## The renders

Measured 2026-09-27 with `src/render.py`:

| Platform | Bytes | Lines | Body lines |
|---|---:|---:|---:|
| claude | 15,034 | 279 | 270 |
| copilot | 15,164 | 277 | 272 |
| hermes | 15,524 | 289 | 276 |

The shared body — the template minus the two platform seams — is **13,924 bytes / 251 lines** and
byte-identical across all three renders, which is the assertion that the body was never forked per
platform.

Budgets, each with wide margin: Hermes' `skill_manager_tool` bounds an agent-written skill at
100,000 characters; Copilot's 500-line body guidance is third-party and VS Code documents no
limit; the renderer caps Claude's description at 1,024 characters.

**Real validators, run for real.** Hermes' `_validate_frontmatter` and `_validate_content_size`,
and Anthropic's `quick_validate.py`, are loaded from their installed sources and run over the
corresponding renders: **no findings, no skips**. Each carries a negative control that fails the
suite if the validator stops rejecting — a missing description, an unexpected `version:` key, and
angle brackets in the description.

## The evaluation

An ablation, recorded 2026-09-26 (`claude plugin eval skill --ablation with-without`, 1151s,
$7.54):

| Case | with | without | Δ | Graders that separated the arms |
|---|---:|---:|---:|---|
| `ingest-follows-the-protocol` | 1.00 | 0.667 | 0.333 | `note-created` — only |
| `stays-inside-the-vault` | 1.00 | 0.750 | 0.250 | `vault-in-its-own-folder` — only |

`meanDelta` 0.292, threshold 1.0 met by both with-arms. **Read it as less than it looks:** each
delta rests on a single grader that tests a *naming convention*, so an agent with no skill loaded
still indexed, still logged, still linked and still contained itself — finding V8 in
`docs/design.md`.

**These are not Claude numbers.** The four runs executed on a non-Claude backend, read from each
run's own trace at the time; the traces are not shipped, so it cannot be re-checked here, and no
row above may be quoted as a Claude result. `make eval-claude` reproduces the run from a plain
terminal.

The other acceptance evidence is the N=3 scripted Hermes ingest: **3/3**, with the variance
confined to the notes produced (5, 5, 6) rather than to whether the protocol was followed. Three
runs is a small sample, and the ablation above cannot supply a variance figure at all.

## Severities, and what is behind them

Three codes ship at `info`: `ZK026`, `ZK027` and `ZK028`. Each reports a state a vault can be in
on purpose — a source kept for the record, a contradiction the other note has not answered yet, a
body section written for a reader rather than a parser — and none of the three breaks something a
later run depends on. Any of them fails a run when the reader asks, with `--fail-on info`.

Nothing else is quiet by design. Every other code reports a fact that is either true or false, so
there is no tier to argue about: a reference that resolves to nothing resolves to nothing at
`warn` and at `error` alike. The severity is asserted against `references/lint-checks.md` in both
directions, so a code cannot ship at a tier its own reference does not state.

One thing is applied by the agent rather than the linter, and can therefore drift silently: the
Page Threshold, in `references/schema-reference.md`. Its observable proxy is notes per source —
the ratio of two numbers the report does carry, `metrics.notes` and `metrics.raw_sources` — and it
is not a metric of its own.

## Unverified

- **Copilot's VS Code extension and cloud agent were never exercised.** Only the CLI was, and the
  listing there is the only discovery claim this repo makes.
- **Copilot CLI's discovery of a project-local `.claude/skills/` is untested**, which is why the
  install section suggests checking before installing a second copy.
- **No Copilot ingest acceptance was run** — there is no Copilot equivalent of the Hermes 3/3.
- **The agent can ignore the protocol.** A loaded skill is not a followed skill; lint makes drift
  detectable after the fact, which is the mitigation rather than a guarantee.

## The suite

`make test` — **505 passed, 0 skipped, 11.7s** (2026-09-27; the time is pytest's own summary line,
which is what `make test` prints), no network and no model call. Besides
the fixtures and the goldens it asserts: the linter is read-only (a recursive tree hash before and
after a full sweep, with a control showing the hash can change), two runs of the same input are
byte-identical, every subprocess runs under `python3 -I` so stdlib-only is enforced rather than
stated, **the date the report was taken on does not change what it found** (one vault linted at
dates a year apart produces identical reports, `now` aside), `--baseline` suppression is counted rather
than hidden (20 keys give 0 findings and exit 0; a partial baseline of 5 leaves 15 and exit 1), the
installer is idempotent across five cases with
every path under `--target-root` so `$HOME` is never read or written, and no tracked file names a
path on one machine — `git ls-files`, every file read as UTF-8, `/Users/<name>` or `/home/<name>`
flagged, with the predicate itself carrying controls in both directions. That guard exists because
a run artifact carrying the author's home directory sat one `.gitignore` line away from being
published, so the `.gitignore` line is asserted too.

`make check` renders all three platforms in memory and diffs them against `tests/golden/` — the
same thing CI runs. `make lint-fixtures` prints the exit code of every fixture.

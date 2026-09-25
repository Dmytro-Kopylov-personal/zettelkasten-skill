# Results

Measurements, appended as phases complete. A phase's gate is met here or it is not met.

## P4 — Install and init (2026-09-26)

**The loop closes: the skill's own linter, run over the vault the skill scaffolds, reports
zero findings and exits 0.** Five templates ship in `skill/templates/`, the Init section of
the body materialises them, and `tests/test_self_consistency.py` performs that section
literally — creates the six directories, copies the five files, fills the domain, appends the
init log entry — then lints the result with the real `lint_vault`. A scaffold the linter
rejects would be the worst possible first impression: a user handed a fresh vault and
immediately told to fix it.

The loop has three sides and all three are asserted, because any two can agree while the
third drifts: the body names five templates, `skill/templates/` holds exactly those five,
and a vault built from them lints clean. No dangling link in either direction.

**The oracle found a real defect in the shipped body on its first run.** Init step 3 read
"materialise `SCHEMA.md` from `templates/SCHEMA.md`, `structure/index.md` from
`templates/index.md`, `structure/concept-table.md`, `structure/overview.md`, and `log.md`
from `templates/log.md`" — naming five destinations and two sources, leaving an agent to
guess where the other two came from. The step now gives a source for every destination.
Three goldens re-rendered, diff reviewed, byte-identical across platforms as the shared-body
invariant requires.

**Two scaffold traps are pinned separately**, because a fresh vault has nothing to lint and
would go green whether or not they work. The index template shows its entry format *inside a
fence*; if the wikilink extractor ever stopped stripping fences, every vault would be born
with a dangling link. The log template shows its entry format in a fence too, and `ZK022`
reads every bullet line whether fenced or not — so the example carries a real date, and a
test asserts it keeps one.

**The installer, through a fake home.** `install.sh` renders, validates, then copies; every
test passes `--target-root`, and the real `$HOME` is never read or written. The five
idempotency cases are exercised end to end:

| Case | Result |
|---|---|
| files identical | no write, no backup, tree hash unchanged |
| managed, differs | `.bak.<utc>` written first, then the render; the backup holds the hand edit |
| present but unmanaged | **refused, exit 4**, nothing written, no manifest left claiming ownership |
| manifest gone, files identical | adopted: manifest re-recorded, tree unchanged |
| manifest gone, a file differs | refused, exit 4 |

`--force` creates a missing skills root (exit 3 without it) and deliberately does **not**
override a refusal — the remedy for an unmanaged file is a person moving it, not a flag.

**The installer test found an installer bug.** Detection ran in a function called through a
command substitution, so `exit 2` on an ambiguous root only terminated the subshell: the user
got *two* contradictory messages and exit 3. Inlined into the main shell, plus a test that
the ambiguous case names both roots and exits 2. This is the same class as the three
report-quality defects in P3 — found by running the thing, not by reading it.

**Three copies of every threshold, now compared.** The linter's `DEFAULT_CONFIG`, the table
in `references/schema-reference.md`, and the commented defaults in `templates/SCHEMA.md` are
parsed and asserted equal — ten keys each, with a control that both parsers found all ten
rather than none. A vault judged by a threshold its own `SCHEMA.md` does not describe is a
vault nobody can argue with.

**The three references the body promised now exist.** `note-format.md`, `schema-reference.md`
and `tool-free-fallback.md` join `lint-checks.md`, and the body is asserted to name only
references that ship — and to leave none unlinked. `tool-free-fallback.md` carries the
requirement that a manual pass reports which checks it could *not* perform: a partial pass
must never read as a clean vault.

**Suite:** 514 passed, 0 skipped, 10.6s. `make check` green. `make goldens` added — the one
path that can make a failing `--check` pass, so it is tested for what it must not do: it
writes the render byte for byte and refuses to adopt one that fails validation.

## P3 — Checks (2026-09-26)

**32 codes, 7 fixtures, 44 expected findings, and every fixture matches its manifest in
both directions.** The registry ships 32 codes — 15 `error`, 7 `warn`, 10 `info` — and
`vault_defects` alone exercises 29 of them; `ZK001`, `ZK002` and `ZK029` need fixtures of
their own, because a vault that is not a vault, a file that will not parse, and a vault-wide
statistic cannot be produced by adding one more note to a good vault.

| Fixture | Findings | Notes | Asserts |
|---|---:|---:|---|
| `vault_clean` | 0 | 8 | a well-formed vault is silent, with 3 checks named as not applicable |
| `vault_defects` | 31 (14/8/9) | 27 | the **exact** finding set — code, file and subject, both directions |
| `vault_minimal` | 0 | 3 | 11 graph and decay checks report not-applicable rather than passing |
| `vault_trap` | 1 (`ZK011`) | 4 | five false-positive attractors produce nothing; the genuine orphan is still flagged |
| `vault_hostile` | 8 (`ZK002`) | 11 | one parse failure per bad file, and nothing else from that file |
| `vault_monoculture` | 1 (`ZK029`) | 4 | the vault-level statistic fires at 8 links of one verb |
| `not_a_vault` | 3 (`ZK001`) | 0 | exit 2 with well-formed JSON on stdout |

Set equality is the assertion in `vault_defects`: an unlisted defect fails the test even at
the right total, and a finding nobody predicted fails it too. **A screen that flags
everything and one that flags nothing must not both look green** — the failure mode this
repo exists to avoid, and the reason each manifest was written by hand before the linter was
run against it.

**Matching the manifest does not prove which check fired.** So `vault_defects`'s 29 codes
are each silenced in turn — deleted from the registry and the report recomputed — and the
lose set must equal exactly the findings the manifest attributes to that code: no more (a
neighbour was covering for it) and no fewer (it was doing work another check also does).
`ZK001`, `ZK002` and `ZK029` get the same treatment in their own fixtures.

**Three report-quality defects were found by using the tool, not by reading it.**

1. `ZK008` reported a broken link twice per note — once from the frontmatter, once from the
   body's Links section, which restates the frontmatter by design. A well-formed-but-wrong
   note said "2 broken links" for one broken target. Now one finding per target.
2. `ZK028` fired on a note with an empty body, stacking a second finding on `ZK015`'s
   report. Two findings for one empty file means fixing the same thing twice.
3. `not_a_vault` printed 22 near-identical `NOT RUN:` lines. Now grouped by reason —
   `ZK003..ZK030 (22 checks; not applicable: no notes)` — which still names every code.

None of the three is a wrong verdict; all three are a report that would waste the reader's
time. That is the class of defect only running the tool on a real input finds, and it is why
the fixtures were built before the checks were declared done.

**The doc anchors resolve.** Every finding carries `references/lint-checks.md#zkNNN`, and the
new reference documents all 32 codes 1:1. The parity test does not compare against a second
copy of the format string: it runs each code through `Finding.as_dict()` — the code path that
really emits the field — and asserts the resulting string lands on a section headed with that
code, with matching severity, and carrying the four parts (severity, predicate, remediation,
manual-scan line). Mutation-tested: a wrong severity on `ZK011`, a deleted `**By hand:**` line
on `ZK025`, and a dropped reason in the "deliberately not checked" table each reddened
exactly one test and nothing else.

**Baseline round trip.** `--baseline-keys` over `vault_defects` yields 31 keys; feeding all
31 back gives 0 findings, exit 0, `baselined: 31`, and the vault is still measured (27 notes).
A partial baseline of 5 leaves 26 findings and exit 1 — suppression is counted, never hidden.
Keys are `code|file|subject` and sorted, so an edit that shifts line numbers does not
resurrect a finding someone already reviewed.

**Read-only and determinism, proven rather than asserted.** A recursive tree hash of
`tests/fixtures/` before and after a full sweep (text, JSON, `--fail-on info`, and
`--baseline-keys` over all seven fixtures) is unchanged; the control shows the hash can
change. Two runs of the same input are byte-identical. Every subprocess runs `sys.executable
-I`, so the stdlib-only claim is mechanically enforced rather than stated.

**Suite:** 463 passed, 0 skipped, 3.4s. `make check` green for all three platforms,
`make lint-fixtures` exits 0/0/1/1/0/0/2 exactly as the manifests claim.

**Honest limits, carried forward to P8.** `ZK023`, `ZK024` and `ZK030` ship at `info`
because their false-positive rates are unmeasured — the plan says promote only where a
measurement supports it, and no measurement exists yet. The `ZK024` limits are written into
the reference rather than left to be discovered: synthesis paragraphs, verbatim quotations,
and unspaced-script word counts will all be flagged. `ZK021` is likewise a proxy —
it catches duplicated *titles*, not duplicated *meanings* — and the reference says so.

## P2 — Linter core (2026-09-26)

**The parser matches PyYAML on the whole corpus.** 26 documents parse to exactly the same
values as `yaml.safe_load`, including types: `id: 202609261430` is an int, `created:
2026-09-26` is a `datetime.date`, `archived: no` is `False`, `count: 1_000` is `1000`, and
a quoted number stays a string. Seven more are deliberately rejected where PyYAML accepts
them (nested mappings, block scalars, anchors, aliases, flow mappings, duplicate keys) —
each asserted to be something PyYAML really does accept, so "stricter" cannot quietly
become "broken anyway". Eight malformed documents are rejected by both, and all fifteen
rejected constructs are pinned to the exact line they report.

**The oracle was mutation-tested, because 45 green tests on the first run are a reason to
distrust the oracle, not to trust the parser.** Three independent mutations — removing
implicit typing, disabling unquoting, allowing duplicate keys — each produce disagreement
on the corpus, so the agreement above is real.

**Extraction.** All four false-positive traps return no links: `[[500, 375]]` inside a
fence, `[[wikilinks]]` in inline code, `[[1](url)]`, and a tilde fence. Line numbers are
preserved through code-stripping, and are **file** lines, not body lines.

**Digest.** `hash` is stable across calls, identical for two files whose bodies match but
whose frontmatter differs (so recording the digest inside the frontmatter cannot change
it), different for CRLF-vs-LF bodies, and equal to the whole file when there is no
frontmatter. A mid-document `---` horizontal rule is not mistaken for a closing fence.
CLI digest == library digest, exit 0/2 correct, run under `python3 -I` to prove no
third-party imports.

**Suite:** 186 passed, 1 skipped (the fixtures sweep, which has nothing to sweep yet).

**Two defects the tests found:**

1. Extraction returned *body*-relative line numbers, so a finding would have sent the
   reader to the wrong line of the file. Fixed with `split_with_lines`, which resolves
   both offsets once; the model now promises file lines.
2. The write-path invariant's `\.(rename|replace)\(` predicate fired on `str.replace` in
   the linter itself — a false positive that would have got the check disabled. The
   unqualified alternates were dropped (the tree-hash test covers what that leaves out),
   and the predicate gained both controls.

## P1 — Render (2026-09-26)

**Renders.** All three validate clean under the local rules and under the independent
second implementation (`tests/support/platform_rules.py`).

| Platform | Bytes | Lines | Body lines |
|---|---|---|---|
| claude | 12,219 | 245 | 236 |
| copilot | 12,333 | 243 | 238 |
| hermes | 12,771 | 256 | 242 |

Shared body after stripping both seams: **11,113 bytes, 217 lines** — byte-identical
across all three renders, which is the assertion that the body was never forked per
platform. Peer skills (`llm-wiki`, `obsidian`, `hermes-agent-skill-authoring`) sit at
8–14k; Hermes' hard cap is 100,000 and Copilot's third-party body guidance is 500 lines,
so both budgets have wide margin.

**Real validators, run for real.** Hermes' `_validate_frontmatter` and
`_validate_content_size`, and Anthropic's `quick_validate.py`, were loaded from their
installed sources via `importlib` and run over the corresponding renders: **no findings,
no skips**. Both carry negative controls that fail the suite if the validator stops
rejecting (missing description; an unexpected `version:` key) — so a validator that had
quietly become a no-op could not pass.

**Controls.** The tool-name denylist passes its positive control (four violation kinds in
one line) and its negative control (`read the file`, `create a note`, `open a terminal`,
`a patch of grass`, `a todo list` — no violations). The shared-body equivalence test is
paired with a control asserting the three renders really do differ, so it cannot pass
vacuously. The differential corpus runs 16 malformed documents plus body-level and
malformed-file cases through both implementations and requires agreement *and* that each
one is flagged.

**Suite:** 93 passed, 0 skipped, 0.1s.

**Two defects the tests found, both fixed:**

1. `render.validate()` never checked angle brackets in the description for Claude, though
   `quick_validate.py` rejects them. Found by the differential corpus — which is the
   point of having a second implementation.
2. The `${CLAUDE_SKILL_DIR}` form — the one actually used — slipped through a denylist
   predicate that only matched the bare `$CLAUDE_`. Found by the negative-side control.

One more, found by using the tool rather than by reading it: `--out` was not counted as a
target by the "no target given" guard, so it exited 2. Fixed, with a regression test.

## P0 — Scaffold (2026-09-26)

Repo created at `~/dev/zettelkasten-skill` with the `commit-msg` hook from the notes vault
(`core.hooksPath=.githooks`). The hook rejects AI co-author trailers; it was exercised
before the first commit to prove it fires.

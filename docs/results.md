# Results

Measurements, appended as phases complete. A phase's gate is met here or it is not met.

## P7 — Copilot acceptance (2026-09-26)

**Installed and discovered.** `./install.sh --platform copilot --force` wrote 11 files into
`~/.copilot/skills/zettelkasten/` — the skills root did not exist, and `--force` creates it,
which is the only thing `--force` does. `copilot skill list` then prints:

```
Personal skills:
  zettelkasten - Maintain an atomic, densely-linked Zettelkasten vault of permanent notes. Use when the user drops a source to ingest, asks a question of their notes, or says lint, audit or health-check.
```

**Discovery did not need an interactive terminal after all.** The plan expected `/skills list`,
which is a slash command and therefore not scriptable; Copilot CLI 1.0.88 also ships
`copilot skill` as a *subcommand* with `list`, `add`, `remove`, `enable`, `disable`. So the
check is scriptable and reproducible, and it is the command recorded rather than a keystroke
sequence someone would have to transcribe.

**The description arrives whole, unlike Hermes.** V2 is Hermes-specific: its catalog shows
`description[:57] + "..."`, which is why the trigger verbs are front-loaded. Copilot's listing
prints the full sentence. The front-loading costs nothing and is asserted for Hermes, so
nothing changes — but the finding is bounded to the platform that caused it, and this is the
evidence for that boundary.

**Copilot's source list, read from its own help.** Personal skills come from `~/.copilot/skills/`
and `~/.agents/skills/`; project skills from `.github/skills/`, `.agents/skills/` or
`.claude/skills/`. That last entry means a repository already carrying the Claude render may
well be discovered without a second copy — it is recorded as an untested overlap, and
`copilot skill list` is the command that settles it, not a claim.

**What this does not show.** No ingest acceptance was run on Copilot, so there is no Copilot
equivalent of the Hermes 3/3. The VS Code extension and the Copilot cloud agent were not
exercised at all, and the README ships that as an explicit **unverified** marker rather than a
footnote. The CLI listing is the whole of the discovery claim.

## P6 — Claude acceptance (2026-09-26)

**Four results, three of them clean.**

**Installed and byte-identical.** `~/.claude/skills/zettelkasten/` holds the Claude render
and its references, templates and scripts, every file equal to `tests/golden/claude.SKILL.md`
and to `dist/claude/`. `skill/evals/` is tracked and reviewed but **never installed** — a
dry-run reports 11 files to write and no `evals/`, `case.yaml` or `stage.sh` among them, and
adding the suite broke no invariant (518 tests, unchanged). An acceptance suite that ships
with the skill would be scaffolding in a user's vault.

**`quick_validate.py` exits 0, calibrated in both directions.** It passes the shipped render
and it fails a deliberately broken one, naming the offending key — so the exit code is
evidence rather than a check that cannot fail. Which is the whole problem with the validator
the gate originally named:

**`claude plugin validate` reads one skill layout and is blind to format (V7), so the P6 gate
struck it.** Its help text promises "the skills, agents, and commands in a directory", but it
descends only into the **default `skills/` directory** — a `SKILL.md` at the plugin root, or in
a directory named by the `skills` key, is never opened, and `contents` came back `[]` with exit
0 under `--strict`. That is this repo's layout exactly (`skill/`, declared via `skills`), so the
gate as written would not have inspected the skill it was gating. Inside the directory it does
read the checks are real but shallow: a missing description, a missing frontmatter block and
unparseable YAML each fail `--strict`, while a non-kebab name, angle brackets in the description
and an unrecognised `version` key pass identically to a good skill. Not a check that cannot fail
— a check that fails on the wrong things, in the wrong directory. Replaced with the two
instruments that move in both directions: `quick_validate.py`, and discovery.

**The loader and the validator disagree in both directions, and a missing description is fatal
(V9).** Read from the loader's own init event (`claude -p --plugin-dir … --output-format
stream-json --verbose`, whose `skills` array is real loader output, not a model's account of
itself): a `SKILL.md` at the plugin root **loads**, with or without a `skills` key, and so does a
directory named by `skills` — both layouts `validate` never opens. The loader is stricter in
exactly one place, isolated by holding every other variable constant: the same directory with the
same `name` loads when a description is present and is absent from the `skills` array when it is
not, at the plugin root and in a declared directory alike. Every render already requires a
non-empty description, so nothing changed here; it is recorded because the reason is now known
rather than assumed.

**The plugin install path, verified end to end (P6b).** The repo now ships
`.claude-plugin/plugin.json` and `marketplace.json`, so Claude Code can install it the idiomatic
way rather than by cloning. Exercised in an isolated `CLAUDE_CONFIG_DIR` so the user's own plugin
state was never touched — confirmed isolated by the real config's `rust-analyzer-lsp` being
absent from the run: `marketplace add` → `install zettelkasten@zettelkasten-skill` →
`plugin details` reporting *Skills (1) zettelkasten* → a headless session's init event listing
`zettelkasten:zettelkasten`. Uninstall and `marketplace remove` then returned clean.

Two things this cost, both recorded rather than glossed. The layout is `"skills": ["./skill"]`
with the repo root as the plugin root, chosen over the canonical `skills/<name>/` to avoid moving
a directory that `install.sh`, the Makefile, the goldens and every eval path all point at — and
verified to load, with the skill id coming from the frontmatter rather than the folder. And
`skill/SKILL.md` had to become a committed file: a plugin with a gitignored `SKILL.md` installs as
**zero skills**, silently, because the plugin itself registers cleanly and reports nothing wrong.
`test_golden.py` now asserts that copy byte-identical to `tests/golden/claude.SKILL.md`, so the
golden stays the oracle and the second copy cannot drift unnoticed — the design goal was never
"one file on disk" but "no copy that drifts".

**Discovered, with a control.** `claude --debug-file` reports
`Loaded N unique skills (… user: N …)`, and the count moves **1 → 0 → 1** as the skill is
installed, parked and restored. A headless `claude -p --output-format stream-json --verbose`
init event carries the named `skills` array, which is what turns the count into a name.
`/skills` is `local-jsx` and interactive-only, so it is not scriptable — a session's own init
trace lists `skill:zettelkasten` among its `slash_commands` instead.

**`allowed-tools` is not declared**, and the reason is recorded in the plan: the body ships
`references/tool-free-fallback.md`, so a machine without a shell degrades rather than breaks,
and a declared list would be a guess about a surface no local validator inspects (V7) — wrong
silently rather than loudly.

### The ablation: the delta is real, and it is not the behaviour the cases are named for

`claude plugin eval skill --trust-plugin --allow-tools Write Edit Read Glob Grep Skill
--scaffold --runs 1 --ablation with-without --max-cost-usd 10 --keep-temp` — 1151s, $7.54,
`claude` 2.1.281.

| Case | with | without | Δ | Graders that separated the arms |
|---|---:|---:|---:|---|
| `ingest-follows-the-protocol` | 1.00 | 0.667 | 0.333 | `note-created` — only |
| `stays-inside-the-vault` | 1.00 | 0.750 | 0.250 | `vault-in-its-own-folder` — only |

`meanDelta` 0.292, `passRateWithout` 0 for both, threshold 1.0 met by both with-arms and
neither without-arm. Read alone, that is a clean acceptance. Read against the kept run trees
(`--keep-temp`, unsealed and inspected), it says something narrower.

**Case 1, without the skill.** The agent was told to ingest one source into "the Zettelkasten
vault at `vault`". With no skill loaded it wrote six atomic notes into `vault/notes/`, a
source copy into `vault/sources/`, an index of **seven wikilinks**, and a log with a dated
bullet and a back-link. So `indexed-the-note` and `logged-the-operation` passed in *both*
arms: a competent agent already indexes, links and logs when a prompt says "Zettelkasten".
The single grader that separated the arms was the glob `vault/permanent/*.md` — a **directory
name**.

**Case 2, without the skill.** Told nothing about containment, the agent still did not adopt
its working directory: it created exactly one folder and wrote inside it. All three
containment graders — the two `exists: false` checks and the untouched-file regex — passed in
both arms. The one that separated them was `zettelkasten/SCHEMA.md`, i.e. **the template**.

So the measured contribution of this skill, on these two cases, is the *schema* it supplies —
`permanent/` rather than `notes/`, a materialised `SCHEMA.md` — not the behaviour each case is
named after. Both cases pass their gate and the direction is consistent, but the discriminating
surface is one grader each. **A grader a competent agent passes without the skill is not
measuring the skill**, which is the flags-nothing failure this repo exists to catch, one layer
up: not a check that cannot fail, but a check that cannot *discriminate*. The cases need a
grader whose answer depends on something only the body supplies — the id↔filename contract, a
`sha256` on the captured source, a link verb from the closed set, a `sources:` field — none of
which the without-arm vaults have, because `vault/notes/spaced-practice-beats-massed-practice.md`
carries no id and its index is a plain bulleted list.

**This is not Claude evidence.** Every one of the four runs executed as **`deepseek-flash`** —
59, 32, 54 and 59 API events per trace, all the same model, read out of the `--keep-temp`
`trace.jsonl` files. `--model` was not passed on this invocation, and the child runs inherit
the enclosing session's model; an earlier run recorded `modelOverride: sonnet` while executing
as `deepseek-flash`, so the field is a record of what was *asked for*. The numbers above are a
real ablation of a real agent, but they are not numbers about Claude, and no row here may be
quoted as if they were. `make eval-claude` is the same command to run from a plain terminal for
those.

**Two things found by running it.**

1. The report echoes `runsPerCase: 2` from `case.yaml` while `--runs 1` on the command line ran
   one per arm. So this is N=1 per arm and there is no variance figure — the P5 gate recorded a
   pass rate over three runs; this one cannot.
2. Claude Code writes its own `.write-probe` and `.probe-nested/deeper.md` into the run's
   working directory, self-labelled *"Temporary write-permission probe … Safe to delete."* They
   are the harness's, not the agent's, and no current grader matches them — but a `file_exists`
   glob of `**/*.md` would. Recorded so that nobody authors one.

**The schema fix is confirmed in the artifact.** The report's `maxTurns` 40 and
`timeoutSeconds` 900 now match `case.yaml`; before the fix it read 10 and 300, because those
keys sat at the top level and `case.yaml` silently ignores what it does not recognise. The same
silence swallowed `scaffold_script` while it was an inline block — it must be a **path** under
`context:`, and the run recorded `source: mixed`. Both facts are now comments in the case files.

**Suite:** 518 passed, 0 skipped, ~10.7s. `make check` green for all three platforms.

## P5 — Hermes acceptance (2026-09-26)

**Installed, visible, pinned.** `./install.sh --platform hermes` wrote 11 files into
`~/.hermes/skills/research/zettelkasten/`, `hermes skills list` shows the row
(`zettelkasten · research · local · enabled`), and `hermes curator pin zettelkasten` reports
*"pinned 'zettelkasten' (will bypass auto-transitions)"* — which matters here because the
curator archives skills it judges stale, and an archived skill is an invisible one.

**The catalog line is verified where the model actually reads it.** Not by re-deriving the
truncation, but by exporting a live session and looking at the system prompt the agent was
given:

```
- zettelkasten: Ingest, query, lint and init a Zettelkasten vault. Use wh...
- tech-job-market-analysis: Research a tech job market for a specific location, skill...
```

All four trigger verbs and the name survive the cut; the neighbouring skill's description is
truncated mid-phrase. That is V2 confirmed end to end rather than modelled.

**A second door to V1, found by running Hermes' parser rather than its validator.** The OS
gate and the catalogue both read `frontmatter["platforms"]`, and `parse_frontmatter` falls
back to splitting every line on its first colon when PyYAML is missing *or any line raises*.
In that mode `platforms: [linux, macos, windows]` becomes the **string**
`"[linux, macos, windows]"`, the gate wraps it in a one-element list, nothing matches, and
the skill is silently absent — V1's failure reached without touching the fragment. Measured
by forcing the fallback, and the block form was measured too: it fails *open* (empty value →
"compatible with all"). The flow form stays, because all 85 OS-gated skills in this tree
declare it that way and a degraded parser hides every one of them; the remedy is upstream.
Two tests carry the finding instead — one asserts the shipped render parses under the
installed parser to a real list, the other forces the fallback and asserts it really does
hide the skill, so the guard cannot pass vacuously. A tab in the frontmatter reddens the
guard, checked by mutation.

**The N=3 ingest: 3/3 passed.** Three one-shot `hermes -z` runs, each into a throwaway vault
built by performing Init literally from the shipped templates, each handed a source written
*outside* the vault so the Capture step is exercised rather than bypassed. Scored by the
shipped linter plus four protocol markers read out of the session record Hermes writes:

| Run | Notes | Links | Orphan rate | Verbs | Lint | Markers |
|---|---:|---:|---:|---|---|---|
| 1 | 5 | 11 | 0.00 | applies 3, extends 8 | exit 0, 0 findings | 4/4 |
| 2 | 5 | 11 | 0.00 | applies 2, extends 9 | exit 0, 0 findings | 4/4 |
| 3 | 6 | 14 | 0.00 | applies 4, extends 10 | exit 0, 0 findings | 4/4 |

Zero findings from all three vaults, confirmed independently through the CLI
(`python3 -I skill/scripts/zettel_lint.py <vault>`) rather than only through the library call
the harness uses. Variance is in the notes produced (5, 5, 6), not in whether the protocol
held: every run proposed before writing, captured with a digest, linked both directions,
registered in the index and logged. 145,615 input / 107,629 output tokens across the three.

**The predicted verb collapse did not happen, in any run, on the unpatched skill.** The plan
names it as a risk: six verbs are too many, and the taxonomy decays to `supports`. Across
three runs `supports` appears **zero** times. Run 1 did this on the canonical skill — before
any lesson about verbs existed — so the behaviour is the skill's, not the harness's. Notes
were also atomic in the intended sense: six note-worthy claims were extracted from a source
with six separable claims, and run 3's log says why the sixth exists.

**The instrument was wrong three times before it was right, and the controls caught it.**
`proposed_first` failed run 1 while run 1 had done nothing wrong. The plan and the first
write calls arrive in **one** assistant message — a detail of the runtime, not of the
protocol — so the marker was reading past it. Corrected, re-scored: run 3 then failed. Run 3
had also done nothing wrong: its plan was an *indented numbered list*, and the marker
recognised only the literal `1.`, reading a five-item plan as one item. Corrected, the
controls caught a third: `patch` — Hermes' most-used mutation tool, and the tool that made
run 3's actual first write — was missing from the write set, so "first write" was being read
from a later message. All three corrections were re-scored **from the stored sessions, with
no model calls re-run**. The final marker passes 7/7 controls, including both directions:
a plan in the same message as the write counts, a write with no prose does not, and a plan
that only appears *after* the write does not.

The lesson is the one this repo keeps re-learning, now about its own acceptance harness:
three green-looking scoring bugs, each of which would have been recorded as an agent failure.
A marker that cannot fail and a marker that always fails are indistinguishable until
something is run against it in both directions.

**An agent edited its own installed skill, and the installer handled it exactly as
designed.** During run 1 the agent used `skill_manage` to append two pitfalls to
`~/.hermes/skills/research/zettelkasten/SKILL.md`. Runs 2–3 therefore ran against a
*patched* skill while run 1 ran against the canonical one — a confound, recorded rather than
smoothed over. It is probably immaterial: run 1, on the unpatched skill, already showed the
verb profile the patch described. Both lessons were afterwards adopted into
`src/SKILL.template.md` as pitfalls 10 and 11 — they record measured behaviour rather than
guess at it, and the second is a direct answer to a named risk. Re-installing backed the
agent's edit up to `SKILL.md.bak.20260925T235155Z` and restored the canonical render, so the
one-way backup trap the plan predicted was exercised by a real event rather than a fixture.

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

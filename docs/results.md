# Results

Measurements, appended as phases complete. A phase's gate is met here or it is not met.

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

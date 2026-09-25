# Results

Measurements, appended as phases complete. A phase's gate is met here or it is not met.

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

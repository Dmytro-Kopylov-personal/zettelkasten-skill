# vault_trap — a screen that flags everything must not look green

Written by hand before the linter was run against it.

**Expected: 1 finding (ZK011 on `202609280904-isolated-claim`), exit 0, 4 notes.**

## The traps

Every one of these appears in a note body and must produce **no link at all**. A scanner
that does not strip code, or that matches `[[` without checking for a closing `]]`, reports
each of them; that is the V3 finding in `docs/design.md`, measured in this vault.

| Trap | Where it lives | Why it is not a link |
|---|---|---|
| `[[500, 375]]` | inside a ```` ```python ```` fence | it is a numpy shape, not a wikilink |
| `[[500, 375]]` | inside a `~~~` fence | tilde fences count too, which is easy to forget |
| `[[wikilinks]]` | inside inline code, in prose *about* wikilinks | the prose that documents the syntax is the most likely false positive of all |
| `[[1](url)]` | a markdown link written with doubled brackets | there is no `]]`; the bracket pair never closes |
| `"Attention: a scarce resource"` | a **quoted** title containing a colon | an unquoted colon is a parse error, a quoted one is a plain string |
| `"The # sign in a quoted scalar"` | a **quoted** title containing a hash | a naive comment stripper truncates the value at the `#` |

If the stripper fails, the traps do not merely go unnoticed — they become broken link
targets, so the fixture would report `ZK008` and `ZK028` instead of the one expected
finding. False positives here are loud, not silent.

## The trap in the other direction

`permanent/202609280904-isolated-claim.md` links *out* to two notes, and **nothing links to
it** — while `structure/index.md` lists it. That is deliberate and it is the whole point of
`ZK011`: structure links are excluded from the inbound count, so a vault whose index lists
every note still has orphans, and the check is not vacuously satisfied by the index that
every vault is required to have.

The first three notes form a cycle, so the only orphan is the one that was meant to be one.
`metrics.orphan_rate` is 0.25 — one in four — and that number is pinned in `expected.json`
so that a change to how orphans are counted cannot pass unnoticed.

## Files

| File | Purpose | Expected findings |
|---|---|---|
| `permanent/202609280901-attention-budget.md` | Carries the fence, inline-code and markdown-link traps; quoted-colon title | None |
| `permanent/202609280902-forgetting-curve.md` | Quoted-hash title; tilde fence | None |
| `permanent/202609280903-spacing-effect.md` | An ordinary note, so the cycle closes | None |
| `permanent/202609280904-isolated-claim.md` | Links out, receives nothing, listed in the index | `ZK011` · its own slug |
| `structure/index.md` | Lists all four, including the orphan | None |
| `SCHEMA.md` | No `tags:` key, so `ZK016` is not applicable | None |
| `log.md` | One dated entry, well under the rotation threshold | None |
| `raw/articles/attention.md` | Cited by all four notes; digest correct | None |

## What this fixture does not test

It does not test that the same trap text becomes a *real* link when the fences and backticks
are removed. That control is in `tests/test_extraction.py`, where each trap has a
neighbouring case that must match — a check that nothing can trip is indistinguishable from
a broken one, and this fixture alone cannot tell the two apart.

# vault_clean — the known-good vault

Written by hand, before the linter is run against it. The test asserts **set equality**:
every file below must produce exactly the finding listed against it, and the linter must
produce no finding that is not listed. "None" is a claim, not an absence of information.

**Expected: 0 findings, exit 0, 8 notes.**

## What this fixture is for

A screen that flags everything and one that flags nothing look identical from the inside.
`vault_defects` proves the linter can find defects; this fixture proves it does not invent
them on a vault that is well-formed by construction. Every check that *could* fire here is
given a reason not to: each note has ≥2 resolving links with distinct verbs, each has an
inbound link, both raw files are cited, the index lists every note, and the one
`contradicts` link is recorded on both sides.

## Files

| File | Purpose | Expected findings |
|---|---|---|
| `SCHEMA.md` | Declares all six vocabulary dimensions — the four-tag taxonomy, the nine required fields, one type, two statuses, two confidences, six verbs — and every note conforms to all six, so ZK003 is exercised rather than skipped | None |
| `log.md` | Three dated entries; no check counts them any more | None |
| `inbox/` (empty) | Present because the scaffold creates it. No check reads it now: the check that did was the unfiled-capture nudge, retired with the thresholds | None |
| `structure/index.md` | Lists all 8 notes — an incomplete index is ZK012 | None |
| `structure/concept-table.md` | Links only to `structure/`, which never counts toward the inbound-link total | None |
| `structure/overview.md` | Prose, no links | None |
| `raw/articles/karpathy-llm-wiki-2026.md` | Cited by 6 notes; digest recorded and correct | None |
| `raw/articles/attention-2001.md` | Cited by 2 notes; digest recorded and correct | None |
| `permanent/202609200900-attention-budget.md` | `contradicts` its reciprocal pair; 3 links | None |
| `permanent/202609200901-spaced-repetition.md` | Rotation; 2 links | None |
| `permanent/202609200902-working-memory.md` | The other side of the reciprocal `contradicts` pair; 3 links | None |
| `permanent/202609200903-retrieval-beats-review.md` | Two tags, both from the taxonomy | None |
| `permanent/202609200904-compile-beats-retrieve.md` | Cited `raw/articles/karpathy-llm-wiki-2026.md` | None |
| `permanent/202609200905-link-density.md` | Status `seed`, one of the two the declaration lists | None |
| `permanent/202609200906-provenance-marker.md` | Body carries a `^[raw/...]` marker | None |
| `permanent/202609200907-atomic-note.md` | Title has no "and" in it, and a body of one idea | None |

## Why these links

Note *i* links to notes *i+1* and *i+2* (mod 8), so every note has exactly two inbound
links and the orphan check has nothing to report — without `structure/index.md` being
allowed to cure anything, since `structure/` links are excluded from the inbound count by
design. The rotation uses `supports`, `extends`, `applies`, `source` and `supersedes`;
`contradicts` is deliberately kept out of it and given a single hand-built reciprocal pair
(`attention-budget` ↔ `working-memory`), because a one-sided `contradicts` is ZK027 and
scattering the verb through a rotation is exactly how that finding gets made by accident.

## Nothing is not applicable here, and that is the point

Every one of the fifteen checks has a surface to read in this vault, and all fifteen read it
clean. That is a stronger claim than it used to be. Under v1 this fixture reported three
checks as `NOT RUN` — no note cited three sources, the graph was below the monoculture floor,
and the inbox was empty. All three were threshold checks, and all three are gone.

The one that would have gone quiet for a bad reason is `ZK003`. Conformance is the check a
vault can switch off by declaring nothing, so a "clean" report from a vault that declares
nothing means *unjudged*, not *conforming* — which is exactly what `vault_minimal/` and
`vault_foreign/` show. This fixture declares all six dimensions and conforms to all six, so
its clean report is about conformance rather than about silence. A check that could not run
must say so: silence and success are indistinguishable in a count.

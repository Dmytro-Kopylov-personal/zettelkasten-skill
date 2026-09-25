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
| `SCHEMA.md` | Domain and the four-tag taxonomy (`cognition`, `memory`, `method`, `knowledge-management`) every note's tags come from | None |
| `log.md` | Three dated entries; well under the 500-entry rotation threshold | None |
| `inbox/` (empty) | Present, so ZK031 is *not applicable* rather than *failing* | None |
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
| `permanent/202609200905-link-density.md` | Status `seed`, `updated` recent enough to be unstale | None |
| `permanent/202609200906-provenance-marker.md` | Body carries a `^[raw/...]` marker | None |
| `permanent/202609200907-atomic-note.md` | Title has no "and" (ZK025) and the body is one paragraph short of multi-idea | None |

## Why these links

Note *i* links to notes *i+1* and *i+2* (mod 8), so every note has exactly two inbound
links and the orphan check has nothing to report — without `structure/index.md` being
allowed to cure anything, since `structure/` links are excluded from the inbound count by
design. The rotation uses `supports`, `extends`, `applies`, `source` and `supersedes`;
`contradicts` is deliberately kept out of it and given a single hand-built reciprocal pair
(`attention-budget` ↔ `working-memory`), because a one-sided `contradicts` is ZK027 and
scattering the verb through a rotation is exactly how that finding gets made by accident.

## Checks that are not applicable here, and why that is reported

`ZK024` (no note cites 3 or more sources — every note cites one, two notes cite two),
`ZK029` (17 links; the monoculture check needs 20 before a ratio is meaningful), and
`ZK031` (the inbox is empty). These are printed as `NOT RUN` with their reasons. A check
that could not run must say so: silence and success are indistinguishable in a count.

vault_clean deliberately stays under the ZK029 floor. The verb-monoculture measurement
needs a bigger graph, and inventing 20 links here would make this fixture about the
monoculture check instead of about being clean.

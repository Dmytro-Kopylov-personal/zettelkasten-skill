# vault_minimal — the smallest vault that still has a graph

Written by hand before the linter was run against it.

**Expected: 0 findings, exit 0, 3 notes, 11 checks not applicable.**

## What this fixture is for

`vault_clean` shows a full vault with a full set of checks running. This one shows the
opposite failure mode: a vault so small that more than a third of the checks have nothing to
read. The question it answers is whether a green report from such a vault means "everything
passed" or "almost nothing ran" — and the answer must be the second one, *out loud*.

Eleven checks are reported as not applicable, each naming its own reason:

| Check | Why it cannot run |
|---|---|
| `ZK012` | there is no `structure/index.md` |
| `ZK013` | no note cites a source |
| `ZK014`, `ZK019` | the vault has no `raw/` |
| `ZK016` | `SCHEMA.md` declares no tag taxonomy |
| `ZK018` | no note carries a provenance marker |
| `ZK024` | no note cites 3 or more sources |
| `ZK026` | the vault has no `raw/` |
| `ZK027` | no note uses the `contradicts` verb |
| `ZK029` | only 6 links; the check needs 20 |
| `ZK031` | the vault has no `inbox/` |

The distinction that matters: `ZK029` is not applicable because the graph is too small for a
ratio to mean anything, while `ZK016` is not applicable because there is no taxonomy to
violate. Neither is a pass, and neither is a failure. Only the report can say so.

## Files

| File | Purpose | Expected findings |
|---|---|---|
| `permanent/202609260900-alpha-claim.md` | Links to the other two | None |
| `permanent/202609260901-beta-claim.md` | Links to the other two | None |
| `permanent/202609260902-gamma-claim.md` | Links to the other two | None |
| `SCHEMA.md` | Frontmatter has a domain and **no `tags:` key** — that absence is what makes ZK016 not applicable | None |
| `log.md` | Exists, has no entries: ZK022 and ZK032 both run and find nothing to say | None |

Deliberately absent: `raw/`, `structure/`, `inbox/`, and any `sources:` or `tags:` field.
Each absence is a claim the report must make explicitly.

## What this fixture does not test

The three notes form a cycle (each links to the other two), so the orphan check has nothing
to report — but that is `vault_clean`'s property too. `ZK011`'s positive case is
`vault_trap`, where being listed in the index does not save a note from being an orphan.

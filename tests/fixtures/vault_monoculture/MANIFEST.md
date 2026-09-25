# vault_monoculture — a defect that lives in no single file

Written by hand before the linter was run against it.

**Expected: 1 finding (ZK029, subject `supports`), exit 0, 4 notes.**

## Why this vault exists separately

Every other fixture in this directory defects one file at a time. `ZK029` cannot work that
way: it is a ratio over every link in the vault, so tripping it inside `vault_defects` would
require most of that corpus's 55 links to share a verb — and every other note there would
have to become monotone to keep the proportion high, which fights every other fixture at
once. A four-note vault built for this one measurement is the honest way to test it.

The four notes are well formed. Each links to two others with the verb `supports`, eight
links in all, and the report is:

```
ZK029  8 of 8 links use the verb 'supports' (100%)
```

## The fixture also pins the two properties of the check

**The floor.** `SCHEMA.md` sets `lint_verb_monoculture_min_links: 6`, well below the default
of 20. That is what lets a four-note vault carry the measurement at all — and it means this
fixture tests the ratio, not the default floor. The floor itself is tested negatively by
`vault_clean` (17 links, quiet) and `vault_defects` (55 links, quiet), where the check runs
and must not fire.

**The severity.** `ZK029` is `info`, so the exit code stays 0 at the default `--fail-on
error`. `expected.json` records that, and also records that the same vault exits 1 at
`--fail-on info`. A finding that no threshold can fail on is decoration; this one can be
made to fail on, deliberately, by the person who wants that.

## The predicted failure this measures

The six link verbs are a taxonomy, and taxonomies collapse: the predicted failure mode is
that every link becomes `supports` because `supports` is always defensible. That is not
visible in any single note — each one looks reasonable — and it *is* visible as a
distribution over a vault. Hence a check, and hence a fixture that must flag it.

## Files

| File | Purpose | Expected findings |
|---|---|---|
| `permanent/202609260900-first-claim.md` | Monotone links | None |
| `permanent/202609260901-second-claim.md` | Monotone links | None |
| `permanent/202609260902-third-claim.md` | Monotone links | None |
| `permanent/202609260903-fourth-claim.md` | Monotone links | None |
| `SCHEMA.md` | Lowers the link floor to 6 | None |
| `structure/index.md` | Lists all four | None |
| `log.md` | One dated entry | None |

There is no `raw/` and no `inbox/`, so nine checks are not applicable by name.

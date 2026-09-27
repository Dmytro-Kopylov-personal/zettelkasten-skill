# vault_foreign — a vault that declares no vocabulary is not judged against one

Written by hand before the linter was run against it.

**Expected: 0 findings, exit 0, 3 notes, 1 raw source, 6 links, ZK003 not applicable.**

## What this fixture is for

v2 made conformance the vault's own declaration: `ZK003` reads `SCHEMA.md` and judges the notes
against what it finds there. That gives every vault a switch that turns the check off — declare
nothing, and nothing is checked. A switch like that is indistinguishable from a broken check
unless it is pulled in both directions, and this is the direction that matters most, because it
is the one a real user hits: a vault that has never heard of this skill, carried into it
unchanged.

So the claim this fixture makes is *negative and specific*: a foreign vocabulary is not wrong.
Its notes say `type: essay`, `status: growing`, `confidence: weak`, `tags: [epistemics, tooling]`
and link with `refines`, `cites`, `builds-on` and `undercuts`. Under v1 every one of those was a
finding — `ZK004`, `ZK009`, `ZK016` — because the linter carried its own taxonomy as a default.
Under v2 the report is empty, and `declared: {}` with all six dimensions reading
`not declared` in the JSON is the positive evidence that the check looked and stood down rather
than passed.

## Files

| File | Purpose | Expected findings |
|---|---|---|
| `SCHEMA.md` | Frontmatter has a domain and **no vocabulary key at all** — no `tags`, `required_fields`, `types`, `statuses`, `confidences` or `verbs`. This is the fixture's entire input | None |
| `log.md` | Two dated entries | None |
| `structure/index.md` | Lists all three notes | None |
| `raw/articles/somebody-elses-source.md` | Cited by all three notes; digest recorded and correct | None |
| `permanent/202609300900-notes-are-epistemic-tools.md` | `type: essay`, `status: growing`, `confidence: weak`, two foreign tags, verbs `refines` and `cites` | None |
| `permanent/202609300901-tools-shape-thought.md` | `confidence: moderate`, verb `builds-on`, and `undercuts` — a verb the six-verb format does not have | None |
| `permanent/202609300902-writing-is-thinking.md` | `status: dormant`, verb `undercuts` | None |

Note the filenames: this vault *does* use `YYYYMMDDHHMM-slug.md` and *does* carry `id`,
`title`, `created` and a `^[raw/...]` marker. That is not an oversight, it is the fixture's
scope. **The format is the skill's; the vocabulary is the vault's** — and this fixture varies
only the second. A vault that also renamed its files and dropped `id` would fire `ZK006`, which
is a fact about identity rather than an opinion about vocabulary, and would have made the
fixture about two things instead of one.

## The one thing a foreign vocabulary does switch off besides conformance

`ZK027` is not applicable here, and it is worth being exact about why: the reciprocity
obligation is attached to the literal verb `contradicts`, so a vault that expresses disagreement
with `undercuts` gets no reciprocity check. Declaring `verbs:` and leaving `contradicts` out has
the same effect, and by design — a vault that does not use the verb cannot have a one-sided use
of it. But it is a real consequence of "the format is ours", so it is written down here rather
than discovered by a user whose links quietly stopped being checked.

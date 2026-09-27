# The note format

The full contract for a permanent note. `references/lint-checks.md` gives the check that
enforces each rule; this file says what the rule is and why it exists.

## The file

`permanent/YYYYMMDDHHMM-slug.md`

- Twelve digits: year, month, day, hour, minute at the moment of creation.
- The slug is lowercase words joined by hyphens, and it is a *name*, not a sentence.
- The timestamp is the note's identity. Titles change; timestamps do not, because every
  link in the vault is written against the filename.

The `id` field must equal those twelve digits. A file whose name and `id` disagree is
reported as `ZK006`, and the disagreement is worse than either half being wrong: links
resolve by filename, so the frontmatter and the graph would be telling different stories.

**Quote the `id`** — `id: "202609261430"`, not `id: 202609261430`. Twelve digits is a
number to anything that infers a type from the text, and an editor that decides so will
show it as one and let it be edited as one. Obsidian's Properties panel is the one you will
meet: unquoted, the field is typed `Number` and has no text affordances; quoted, it is
`Text`. Both spellings parse and lint identically — the linter reads either — so this is
about the value being what it looks like, and identifiers are not quantities.

Notes may sit in subdirectories of `permanent/`, and every check walks the whole tree, so a
vault filed by topic or by year is read the same as a flat one. Links need not say which:
`[[202609251200-slug]]`, `[[memory/202609251200-slug]]` and `[[permanent/memory/202609251200-slug]]`
all resolve to the same note, as does any of them with `.md` appended — Obsidian writes the
shortest form by default and lengthens it only when two notes share a basename, which the
timestamp prefix prevents. Only `structure/` is read flat, because its files have fixed
names and fixed roles.

## Frontmatter

```yaml
---
id: "202609261430"
title: Attention budget is a scarce resource
type: permanent
status: seed
created: 2026-09-26
updated: 2026-09-26
sources:
  - raw/articles/karpathy-llm-wiki-2026.md
confidence: medium
tags: [cognition, productivity]
links:
  - target: 202609251200-spaced-repetition
    verb: supports
  - target: 202609240900-working-memory-limits
    verb: extends
---
```

| Field | Required | Values |
|---|---|---|
| `id` | yes | the twelve digits of the filename |
| `title` | yes | the claim, as a sentence you could disagree with |
| `type` | yes | `permanent`, `source`, `structure` |
| `status` | yes | `draft`, `seed`, `evergreen`, `archived` |
| `created` | yes | `YYYY-MM-DD` |
| `updated` | no | `YYYY-MM-DD`, never earlier than `created` |
| `sources` | for anything drawn from a source | paths under `raw/` |
| `confidence` | no | `low`, `medium`, `high` |
| `tags` | no | from the tags list in `SCHEMA.md` |
| `links` | yes | a list of `target` + `verb` |

The **Required** column is this vault's own starting declaration, not a rule the linter
carries: `required_fields`, `types`, `statuses`, `confidences` and `verbs` are all read from
`SCHEMA.md`, and the values above are what `init` scaffolds there. Edit that file and the
table above stops describing your vault — which is the intended direction of travel. A field
the linter imposes regardless is the filename, the `id` agreement and a body; everything else
in this table is yours to change.

Use the YAML subset the linter can read: plain and quoted scalars, flow lists, block
lists, and lists of single-key maps. **Tabs, anchors, aliases, block scalars, flow mappings
and duplicate keys are refused** (`ZK002`) — not because they are invalid YAML, but because
a parser that guesses at a construct it half-supports is a parser that reports the wrong
thing. If the frontmatter of a note you wrote fails to parse, the note is excluded from
every check that reads it, and you have lost the checks rather than the note.

### Writing a title

The title is the claim, not the topic. "Spaced repetition" is a topic — a note about a
thing. "Spacing beats massing for durable recall" is a claim, and a claim can be linked to,
supported, extended or contradicted by another note. A vault of topics becomes a wiki; a
vault of claims becomes an argument.

### Choosing a status

- `draft` — written but not trusted. Expect to revise it soon.
- `seed` — the claim is settled enough to link to, but thin.
- `evergreen` — you would defend it as written.
- `archived` — retired, kept for the record, no longer maintained.

A note can sit in `draft` or `seed` indefinitely without being reported. That used to be
`ZK017`, a nudge after a fixed number of days, and the number was the opinion — nothing about
a tenth day makes a note ready and nothing about a ninetieth makes it stale. The prompt to
promote, split or archive is still worth acting on; it just is not something the linter can
tell you.

## The body

One idea, argued in one place, with citations as you go.

- **Opening sentence: the claim.** It should be possible to read the first sentence and
  know what the note asserts.
- **Elaboration, evidence, counterarguments.** Cite each factual claim at the point it is
  made: `^[raw/articles/karpathy-llm-wiki-2026.md]`. Writing the citations at the end is
  how a claim ends up unattributed.
- **The Links section**, at the end, restating the frontmatter links as prose:

  ```markdown
  ## Links

  - **supports** [[202609251200-spaced-repetition]] — both describe a fixed capacity
  - **extends** [[202609240900-working-memory-limits]] — narrows it to deliberate attention
  ```

  The reason for the duplication is that the frontmatter is for finding and the body is for
  reading: a reader following the argument sees where it connects. The frontmatter is
  authoritative — when the two drift, the body is what gets corrected (`ZK028`).

Notes shorter than a paragraph are usually a title with no argument; notes with several
substantial `##` sections are usually several ideas wearing one title. The second of those
was `ZK030` until v2 — a section count and a word count deciding it — and the shape is still
worth noticing, by eye, which is the only instrument that ever really decided it.

## Links

Every link is a `target` and a `verb`. The target is a slug; the verb is one of six.

| Verb | Use it when |
|---|---|
| `extends` | this note adds to the target's claim without disagreeing |
| `supports` | this note is independent evidence for the target |
| `contradicts` | this note disagrees, and the target must link back (`ZK027`) |
| `source` | the target is where this note's material came from |
| `applies` | this note puts the target's idea to use in a particular case |
| `supersedes` | this note replaces the target, which stays for the record |

Two outbound links is the working floor, not the goal, and it is advice rather than a rule:
the linter reports a note that links to nothing and a note that nothing links to (`ZK010`),
and a note with exactly one link is reported by neither. Links from `structure/` do not count
towards reachability — otherwise the index every vault is required to have would make every
note look connected.

## Raw sources

`raw/{articles,papers,notes}/descriptive-name.md`

```yaml
---
source_url: https://example.com/the-thing
ingested: 2026-09-26
sha256: <the digest the bundled `hash` subcommand prints for the body>
---

The source, in full or as the portion that matters.
```

The digest covers the body bytes, so it is computed once the text is final and never
recomputed to make a check pass: a mismatch (`ZK019`) means the file changed after capture,
which means the notes compiled from it may be resting on text that is no longer there. The
remedy is a re-ingest, never an edited digest.

**Nothing writes to `raw/` after capture.** Corrections belong in notes about the source;
a source that was wrong is a fact about the source.

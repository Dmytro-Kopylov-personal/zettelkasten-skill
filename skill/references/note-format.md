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

## Frontmatter

```yaml
---
id: 202609261430
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
| `tags` | no | from the taxonomy in `SCHEMA.md` |
| `links` | yes | a list of `target` + `verb` |
| `provenance` | no | `note` to opt out of the inline-marker check (`ZK024`) |

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

`draft` and `seed` notes older than the vault's stale threshold are reported as `ZK017`,
which is a prompt to promote, split or archive, not a deadline.

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
substantial `##` sections are usually several ideas wearing one title (`ZK030`).

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

Two outbound links is the floor (`ZK010`), not the goal. At least one inbound link is what
keeps a note reachable (`ZK011`), and links from `structure/` do not count towards it —
otherwise the index would make every note look connected.

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

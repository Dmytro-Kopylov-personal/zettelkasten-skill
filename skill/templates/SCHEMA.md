---
domain: unset
# The vocabulary this vault declares for itself. These six lists ARE the conformance rule:
# the linter reads them out of this file and judges the notes against what it finds here,
# and against nothing else. Nothing here is a default the linter also holds — delete a line
# and that dimension stops being checked, in this vault, in every run from then on.
#
# The lists below are a starting point, not a standard. Edit them to say what this vault
# actually does.
tags: []
required_fields: [id, title, type, status, created]
types: [permanent, source, structure]
statuses: [draft, seed, evergreen, archived]
confidences: [low, medium, high]
verbs: [extends, supports, contradicts, source, applies, supersedes]
---

# Schema

This vault is about **a domain nobody has filled in yet**. Replace this paragraph with one
sentence naming the subject: a vault without a domain accumulates everything and links
nothing, and the sentence is what an ingest turns to when it has to decide whether a source
belongs.

## The vocabulary

Six dimensions, each declared as a list in the frontmatter above. Each is independent, and
each is opt-in by being present:

| Dimension | What it says |
|---|---|
| `tags` | the subjects this vault writes about |
| `required_fields` | the frontmatter keys every note must carry |
| `types` | the kinds of note this vault keeps |
| `statuses` | the stages a note moves through |
| `confidences` | how sure a note is allowed to say it is |
| `verbs` | the link verbs this vault uses |

A dimension you have not declared is **not checked** — not defaulted, not guessed at. That
is deliberate: a vault carried in from elsewhere is not wrong for having its own words, and
the linter has no business inventing a taxonomy to report it against. The trade is that an
undeclared dimension is also unguarded, so declare the ones you care about.

`tags:` is empty above, and an empty list declares nothing — the check is silent rather than
failing every note. Start with five to ten tags that name recurring subjects, not one per
note. Tags that grow one note at a time stop being a vocabulary.

## Page Threshold

A source earns a permanent note when the idea is one you would want to find again *without*
the source in hand — roughly whenever the idea would survive the source being deleted. A
passing mention does not clear it; an idea you will build on does. There is no numeric
threshold, and this is deliberate: the test is whether the idea stands alone, and a word
count cannot answer that. The proxy to watch is notes per source — a vault averaging far
above one note per source is applying the threshold too loosely.

## The six link verbs

Every link carries a verb, because an untyped link is a mention.

| Verb | Use it when |
|---|---|
| `extends` | this note adds to the target's claim without disagreeing |
| `supports` | this note is independent evidence for the target |
| `contradicts` | this note disagrees — and the target must link back (`ZK027`) |
| `source` | the target is where this note's material came from |
| `applies` | this note puts the target's idea to use in a particular case |
| `supersedes` | this note replaces the target, which stays for the record |

## Contradictions

New evidence that conflicts with an existing note never edits that note into agreement. It
gets its own note with a `contradicts` link, and both sides keep their dates, so a reader
can see what was believed and when. The old claim may well be the one that was right.

## Local conventions

Anything this vault does differently from the defaults goes here, and the skill follows this
file over its own defaults wherever the two differ.

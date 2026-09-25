---
domain: unset
tags: []
# Thresholds the checks read. Every key is optional: the value in the comment is the
# default the linter uses when the key is absent. Uncomment one to change it for this
# vault only.
# lint_oversized_note_words: 800
# lint_multi_idea_sections: 3
# lint_multi_idea_section_words: 40
# lint_verb_monoculture_ratio: 0.6
# lint_verb_monoculture_min_links: 20
# lint_stale_draft_days: 90
# lint_inbox_stale_days: 30
# lint_log_rotation_entries: 500
# lint_provenance_min_sources: 3
# lint_provenance_min_words: 25
---

# Schema

This vault is about **a domain nobody has filled in yet**. Replace this paragraph with one
sentence naming the subject: a vault without a domain accumulates everything and links
nothing, and the sentence is what an ingest turns to when it has to decide whether a source
belongs.

## Tags

The taxonomy the notes draw from, declared as `tags:` in the frontmatter above. A note
carrying a tag that is not declared there is reported as `ZK016`, and while the list is
empty the check is not applicable rather than failing every note.

Start with five to ten tags that name recurring subjects, not one per note. Tags that grow
one note at a time stop being a vocabulary.

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

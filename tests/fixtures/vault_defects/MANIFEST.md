# vault_defects — one defect per file, on purpose

Written by hand before the linter was run against it. `expected.json` is the same
information in machine-readable form, and the test asserts **set equality**: the linter's
findings must equal this list exactly, so a file whose defect goes unnoticed fails the
suite *and* so does a finding nobody predicted.

**Expected: 20 findings, exit 1, 27 notes, 6 raw sources, 55 links.**

The counts in `expected.json` are pinned deliberately. A fixture that silently loses three
notes — a botched edit, a glob that stops matching — still produces the right findings for
the files it has left, and would otherwise keep passing while quietly testing less.

## The one rule this corpus follows

Every note carries exactly **one** defect, applied as the smallest possible mutation to an
otherwise-valid note. That is harder than it sounds, because checks cascade: a note with no
body has no `## Links` section either, so "no body" and "the body and the frontmatter
disagree" are both, technically, true. Where a cascade was unavoidable it is listed below
and the reason is stated. Where it was avoidable, the fixture was changed rather than the
expectation — several checks were made quieter during this corpus's design (see
`## Cascades that were avoided rather than accepted`).

## Files

| File | The defect, in words | Finding |
|---|---|---|
| `permanent/202609270903-missing-status.md` | The `status` key is absent | `ZK003` · `status` |
| `permanent/202609270904-bad-enum.md` | `status: in-progress`, and the declaration lists `draft, seed, evergreen, archived` | `ZK003` · `status` |
| `permanent/202609270909-bad-verb.md` | `verb: relates` — not one of the six declared | `ZK003` · the target |
| `permanent/202609270915-foreign-tag.md` | `tags: [astrophysics]`, which the declaration does not list | `ZK003` · the tag |
| `permanent/202609270905-bad-date.md` | `created: 26 September 2026` — a date no parser should accept | `ZK005` · `created` |
| `permanent/202609270906-id-mismatch.md` | Filename says `202609270906`, `id:` says `202609270999` | `ZK006` · `id` |
| `permanent/202609270907-dup-id-one.md` | The first of two files claiming one id | — |
| `permanent/202609270907-dup-id-two.md` | The second file claiming id `202609270907` | `ZK006` · the id |
| `permanent/202609270908-broken-link.md` | Links to `202609279999-nowhere`, which was never written | `ZK008` · the target |
| `permanent/202609270913-dangling-source.md` | Cites `raw/articles/never-captured.md`; its **inline marker** points at a file that does exist, so the frontmatter half and the inline half are shown to be different references | `ZK008` · the path |
| `permanent/202609270917-bad-marker.md` | Body marker `^[raw/articles/absent.md]` | `ZK008` · the path |
| `raw/articles/no-hash.md` | Captured with no `sha256`, cited by `202609270920-cache-slug-one` so it is not also ZK026 | `ZK014` · `sha256` |
| `permanent/202609270914-no-body.md` | Frontmatter and two links, no body at all | `ZK015` · its own slug |
| `permanent/202609270911-orphan-note.md` | Links out to two notes; nothing links to it. **`structure/index.md` does list it**, which is the point: structure links are excluded from the inbound count, or the index would cure every orphan and `ZK010` would be vacuous | `ZK010` · its own slug |
| `raw/articles/drifted.md` | Edited after capture, digest never updated, cited so it is not also ZK026 | `ZK019` · `sha256` |
| `log.md` | Seven entries: one is a bullet with no date on line 9 | `ZK022` · line 9 |
| `raw/notes/orphan-source.md` | Captured, never cited by any note or marker | `ZK026` · its own path |
| `permanent/202609270925-contradicts-a.md` | Contradicts `…-contradicts-b` and says so | — |
| `permanent/202609270926-contradicts-b.md` | Is contradicted, and does not link back. **This is the finding's file**: the note that is missing half the relationship is the one that needs it | `ZK027` · the contradicting slug |
| `permanent/202609270927-drift.md` | Frontmatter links to one set of notes, the body's Links section to another | `ZK028` · its own slug |
| `structure/index.md` | Two index defects in one file: `202609270912-unindexed.md` is absent from it, and it links to `202609279998-phantom`, which does not exist | `ZK012` · the unindexed slug, `ZK012` · the phantom |

The vault also carries `structure/concept-table.md`, `structure/overview.md`,
`raw/articles/clean.md` (cited by nearly every note), `raw/articles/extra.md` and
`raw/articles/silent.md` (cited only by the provenance-gap note), and `SCHEMA.md`.

## Files that are deliberately silent

v2 retired every check that decided by a number. A file whose only defect was one of those
is **kept exactly as it is**, as a negative control: its defect is still there, and the
suite asserts that nothing fires on it. Deleting them would have been easier and would have
thrown away the only input proving the retired rules are really gone — and deleting notes
out of a link ring would have cascaded new `ZK008` findings, changing what the corpus tests
as a side effect of a cleanup.

| File | What it carries | Retired code |
|---|---|---|
| `permanent/202609270910-one-link.md` | One outbound link; the old floor was two | `ZK010` |
| `permanent/202609270916-stale-draft.md` | `status: draft`, last touched 2020-01-01 | `ZK017` |
| `permanent/202609270918-self-link.md` | Links to itself, alongside two real links | `ZK020` |
| `permanent/202609270919-dup-link.md` | Links to the same note twice with different verbs | `ZK020` |
| `permanent/202609270920-cache-slug-one.md` | First of two notes whose titles slugify identically | `ZK021` |
| `permanent/202609270921-cache-slug-two.md` | Titled "Cache invalidation is genuinely hard", like the note before it | `ZK021` |
| `permanent/202609270922-oversized.md` | 108 words of one paragraph | `ZK023` |
| `permanent/202609270923-provenance-gap.md` | Three sources, and a 44-word paragraph with no marker | `ZK024` |
| `permanent/202609270924-notes-and-links.md` | Titled "Notes and their links" | `ZK025` |
| `permanent/202609270928-multi-idea.md` | Three `##` sections of ≥10 words each | `ZK030` |
| `inbox/2020-01-01-old-capture.md` | Captured 2020-01-01, still unfiled | `ZK031` |
| `log.md` | Seven entries | `ZK032` |

`log.md` appears twice for a reason: its rotation count was a threshold, so that half of the
file went silent, while the undated bullet on line 9 stayed a fact and still fires as
`ZK022`. The same file is both a live defect and a retired one.

## Cascades that were avoided rather than accepted

- **One broken reference, one finding.** The body's Links section restates the frontmatter,
  so a broken target is named twice. `ZK008` reports one finding per (note, target); before
  this corpus existed, `vault_defects` would have carried two ZK008s for one defect. v2
  widened this to every surface — frontmatter links, wikilinks, `sources:` and `^[raw/...]`
  markers — through one resolver, and the dedupe is what keeps "one defect, one finding" true
  now that four surfaces can name the same missing target.
- **An empty body is one finding.** `ZK028` skips notes with no body: `ZK015` already says
  the file is empty, and "bring the body into line" is not useful advice for a file whose
  body does not exist.

Both are changes to the linter, not to the expectation. The distinction matters: an
expectation written to match the output is not an expectation.

## What is *not* here, and why

- **ZK001 and ZK002** need a vault that is missing its root or has unparseable frontmatter.
  Those are `not_a_vault/` and `vault_hostile/`.
- **`contradicts` never appears in the link rotation.** It is the one verb with a reciprocity
  obligation, so it is applied by hand in exactly one place. A rotation that emitted it would
  make ZK027 fire on half the corpus.
- **Two declared dimensions are never violated.** `types` and `confidences` are declared by
  this vault's `SCHEMA.md` and every note conforms, so they are exercised as negative
  controls only. The declaration is checked in all six dimensions; this corpus defects in
  four.

## The declared vocabulary, and what replaced the old thresholds

`SCHEMA.md` here used to carry three lowered thresholds — `lint_oversized_note_words: 80`,
`lint_multi_idea_section_words: 10`, `lint_log_rotation_entries: 5` — so that a corpus this
size could reach checks whose defaults were 800 / 40 / 500. Those checks are gone, and so are
the keys: v2 ignores unknown `lint_*` keys rather than rejecting them, so leaving them behind
would have been a comment claiming something the linter no longer does.

What `SCHEMA.md` declares now is the vocabulary this vault holds itself to — `tags`,
`required_fields`, `types`, `statuses`, `confidences`, `verbs` — and `ZK003` is the single
check that reads it. The four conformance findings above are one per dimension that can be
violated by a single note: a required field missing, an enum value outside the list, a tag
outside the taxonomy, a link verb outside the six. **An absent dimension is not checked at
all**, never defaulted: `vault_foreign/` is the fixture that pins that, and it is the same
behaviour a vault that has never heard of this skill gets.

`declared_sources` in the JSON reports where each dimension came from — `SCHEMA.md` or
`not declared` — which is the property the old `config_sources` carried. A test asserts the
six keys are attributed rather than inferred, so a typo in a key name fails loudly instead of
silently shrinking what is checked.

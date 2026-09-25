# vault_defects — one defect per file, on purpose

Written by hand before the linter was run against it. `expected.json` is the same
information in machine-readable form, and the test asserts **set equality**: the linter's
findings must equal this list exactly, so a file whose defect goes unnoticed fails the
suite *and* so does a finding nobody predicted.

**Expected: 31 findings, exit 1, 27 notes, 6 raw sources, 55 links.**

The counts in `expected.json` are pinned deliberately. A fixture that silently loses three
notes — a botched edit, a glob that stops matching — still produces the right findings for
the files it has left, and would otherwise keep passing while quietly testing less.

## The one rule this corpus follows

Every note carries exactly **one** defect, applied as the smallest possible mutation to an
otherwise-valid note. That is harder than it sounds, because checks cascade: a note with no
body has no `## Links` section either, so "no body" and "the body and the frontmatter
disagree" are both, technically, true. Where a cascade was unavoidable it is listed below
and the reason is stated. Where it was avoidable, the fixture was changed rather than the
expectation — three checks were made quieter during this corpus's design (see
`## What building this corpus changed`).

## Files

| File | The defect, in words | Finding |
|---|---|---|
| `permanent/202609270903-missing-status.md` | The `status` key is absent | `ZK003` · `status` |
| `permanent/202609270904-bad-enum.md` | `status: in-progress`, a value that does not exist | `ZK004` · `status` |
| `permanent/202609270905-bad-date.md` | `created: 26 September 2026` — a date no parser should accept | `ZK005` · `created` |
| `permanent/202609270906-id-mismatch.md` | Filename says `202609270906`, `id:` says `202609270999` | `ZK006` · `id` |
| `permanent/202609270907-dup-id-one.md` | The first of two files claiming one id | — |
| `permanent/202609270907-dup-id-two.md` | The second file claiming id `202609270907` | `ZK007` · the id |
| `permanent/202609270908-broken-link.md` | Links to `202609279999-nowhere`, which was never written | `ZK008` · the target |
| `permanent/202609270909-bad-verb.md` | `verb: relates` — not one of the six | `ZK009` · the target |
| `permanent/202609270910-one-link.md` | One outbound link; the minimum is two | `ZK010` · its own slug |
| `permanent/202609270911-orphan-note.md` | Nothing links to it. **`structure/index.md` does list it**, which is the point: structure links are excluded from the inbound count, or the index would cure every orphan and `ZK011` would be vacuous | `ZK011` · its own slug |
| `structure/index.md` | Two index defects in one file: `202609270912-unindexed.md` is absent from it, and it links to `202609279998-phantom`, which does not exist | `ZK012` · the unindexed slug, `ZK012` · the phantom |
| `permanent/202609270913-dangling-source.md` | Cites `raw/articles/never-captured.md`; its **inline marker** points at a file that does exist, so the frontmatter half and the inline half are shown to be different checks | `ZK013` · the path |
| `raw/articles/no-hash.md` | Captured with no `sha256`, cited by `202609270920-cache-slug-one` so it is not also ZK026 | `ZK014` · `sha256` |
| `permanent/202609270914-no-body.md` | Frontmatter and two links, no body at all | `ZK015` · its own slug |
| `permanent/202609270915-foreign-tag.md` | `tags: [astrophysics]`, which SCHEMA.md does not declare | `ZK016` · the tag |
| `permanent/202609270916-stale-draft.md` | `status: draft`, last touched 2020-01-01 | `ZK017` · its own slug |
| `permanent/202609270917-bad-marker.md` | Body marker `^[raw/articles/absent.md]` | `ZK018` · the path |
| `raw/articles/drifted.md` | Edited after capture, digest never updated, cited so it is not also ZK026 | `ZK019` · `sha256` |
| `permanent/202609270918-self-link.md` | Links to itself, alongside two real links | `ZK020` · its own slug |
| `permanent/202609270919-dup-link.md` | Links to the same note twice with different verbs | `ZK020` · the repeated target |
| `permanent/202609270920-cache-slug-one.md` | The first of two notes whose titles slugify identically | — |
| `permanent/202609270921-cache-slug-two.md` | Titled "Cache invalidation is genuinely hard", like the note before it | `ZK021` · the shared slug |
| `log.md` | Seven entries: one is a bullet with no date on line 9 | `ZK022` · line 9 |
| `permanent/202609270922-oversized.md` | 108 words of one paragraph (the fixture lowers the soft limit to 80) | `ZK023` · its own slug |
| `permanent/202609270923-provenance-gap.md` | Three sources, and a 44-word paragraph with no marker | `ZK024` · its own slug |
| `permanent/202609270924-notes-and-links.md` | Titled "Notes and their links" | `ZK025` · its own slug |
| `raw/notes/orphan-source.md` | Captured, never cited by any note or marker | `ZK026` · its own path |
| `permanent/202609270925-contradicts-a.md` | Contradicts `…-contradicts-b` and says so | — |
| `permanent/202609270926-contradicts-b.md` | Is contradicted, and does not link back. **This is the finding's file**: the note that is missing half the relationship is the one that needs it | `ZK027` · the contradicting slug |
| `permanent/202609270927-drift.md` | Frontmatter links to one set of notes, the body's Links section to another | `ZK028` · its own slug |
| `permanent/202609270928-multi-idea.md` | Three `##` sections of ≥10 words each — the shape of a note holding several ideas | `ZK030` · its own slug |
| `inbox/2020-01-01-old-capture.md` | Captured 2020-01-01, still unfiled | `ZK031` · its own path |
| `log.md` | Seven entries against a soft limit of five | `ZK032` · `log.md` |

The vault also carries `structure/concept-table.md`, `structure/overview.md`,
`raw/articles/clean.md` (cited by nearly every note), `raw/articles/extra.md` and
`raw/articles/silent.md` (cited only by the provenance-gap note), and `SCHEMA.md`.

## Cascades that were avoided rather than accepted

- **One broken link, one finding.** The body's Links section restates the frontmatter, so a
  broken target is broken twice. `ZK008` now reports one finding per (note, target); before
  this corpus existed, `vault_defects` would have carried two ZK008s for one defect.
- **An empty body is one finding.** `ZK028` skips notes with no body: `ZK015` already says
  the file is empty, and "bring the body into line" is not useful advice for a file whose
  body does not exist.

Both are changes to the linter, not to the expectation. The distinction matters: an
expectation written to match the output is not an expectation.

## What is *not* here, and why

- **ZK029 (verb monoculture) is deliberately absent.** The check is a vault-level statistic:
  to trip it in a corpus this size, most of the 55 links would have to share one verb, which
  would fight every other fixture in the file. It lives in `vault_monoculture/`, a four-note
  vault built for exactly that measurement, and here it is present as an **active negative**
  case: 55 links is above the threshold of 20, so the check runs, and the verbs are spread
  across five of the six, so it must not fire.
- **ZK001 and ZK002** need a vault that is missing its root or has unparseable frontmatter.
  Those are `not_a_vault/` and `vault_hostile/`.
- **`contradicts` never appears in the link rotation.** It is the one verb with a reciprocity
  obligation, so it is applied by hand in exactly one place. A rotation that emitted it would
  make ZK027 fire on half the corpus.

## Config: three lowered thresholds, and why that is honest

`SCHEMA.md` sets `lint_oversized_note_words: 80`, `lint_multi_idea_section_words: 10` and
`lint_log_rotation_entries: 5`, all far below their defaults of 800 / 40 / 500. Without them
the corpus would need a 900-word note, a 130-word section and a 501-entry log to exercise
three checks — size, not substance, and every other note would then have to stay under those
much looser limits, which they trivially do.

This fixture therefore exercises each check's *predicate* but not its *default threshold*.
The defaults are covered by `vault_clean` (where they must stay quiet) and by the per-check
tests in `tests/test_lint_checks.py`, which build a three-line vault and pass `--set`.
`config_sources` in the JSON output reports which layer each value came from, and a test
asserts these three are attributed to `SCHEMA.md` rather than to the defaults — otherwise a
typo in the key name would silently test the default threshold instead.

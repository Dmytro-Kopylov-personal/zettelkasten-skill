# Check codes

Every code the bundled linter can report, one section each: what it fires on, what to do,
and how to find the same thing by hand when scripts cannot run on the machine you are on.

A finding is a claim, not a verdict. The linter reads frontmatter, links, dates and digests;
it cannot read meaning. When a finding and your judgement disagree, the judgement wins — but
say so in `log.md` rather than leaving the next reader to wonder.

## How to read a finding

| Field | Meaning |
|---|---|
| `code` | which check fired, e.g. `ZK011` |
| `severity` | `error` (CI fails), `warn` (decay), `info` (advisory) |
| `file`, `line` | where to look; `line` is a real line of that file, or null for whole-file findings |
| `subject` | what the finding is *about* — a slug, a path, a tag, a field name. Together with `code` and `file` it is the finding's identity, and it is what a baseline records |
| `evidence` | the text the verdict came from |
| `action` | the remediation, phrased as an instruction |
| `doc` | this file, and the anchor for the code |
| `fix` | reserved, always null. There is no `--fix`; see below |

## Three tiers, three exit codes

- `error` — the vault is structurally broken, or a claim's provenance cannot be checked.
  Default `--fail-on` threshold: these are the findings that make the command exit 1.
- `warn` — the vault is decaying: an orphan, a stale draft, a digest that no longer matches.
- `info` — advisory, and some of it is a matter of taste. Never fails a run unless you ask
  for it with `--fail-on info`.

Exit codes: **0** clean at the threshold · **1** findings at or above it · **2** not a vault,
or a usage error. Exit 2 with well-formed JSON on stdout means the linter did not understand
the directory, which is not the same answer as "no findings" and must never be read as one.

## Not applicable is not the same as passed

When a check has nothing to read — no `raw/` to hash, no `inbox/`, fewer links than a ratio
needs — it is reported in `skipped_checks` with its reason, not silently counted as clean.
A vault of three notes is not a vault that passed twenty-nine checks; the report says which
ones had no surface to examine.

## No `--fix`, on purpose

The tool verifies; you write. Three reasons, in order of weight:

1. The highest-value findings are semantic — is this one idea or two? which verb is it
   really? — and no mechanical rule can answer them.
2. The mechanically easy ones (bumping a date, inserting an index line) are exactly where a
   wrong edit silently corrupts the vault rather than failing loudly.
3. Ingest has a propose-then-approve contract. A second write path that skips it would be the
   exception that ends up doing the work.

So the loop is: run the linter, read the JSON, group the findings, propose the changes, apply
the ones that are approved with your own editing tools, then run it again and report the
delta. Hash drift is never repaired by editing the digest — `raw/` is immutable, so the
remedy is a re-ingest.

## Baselines: adoption without weakening

`--baseline FILE` takes the JSON list produced by `--baseline-keys` and suppresses exactly
those findings. The key is `code|file|subject` — deliberately without the line number, so
that editing a file's top does not resurrect a finding you already reviewed and accepted.

Suppressed findings are counted in `summary.baselined`. They are not hidden: a report that
says "0 findings, 31 baselined" is telling you something quite different from one that says
"0 findings", and this tool will not let you confuse the two.

---

<a id="zk001"></a>
### ZK001 — the vault root is missing a required path

**Severity:** error

**Fires when** the directory is missing `permanent/`, `SCHEMA.md` or `log.md`. One finding
per missing path, each naming it. If `permanent/` is missing the exit code is 2, whatever
the threshold.

**Fix:** initialise the vault, or point the linter at the directory that really is one.
Three findings here usually means the path is wrong, not that the vault is broken.

**By hand:** list the directory and look for `permanent/`, `SCHEMA.md` and `log.md`. If they
are not there, you are not looking at a vault, and nothing else in this file applies.

<a id="zk002"></a>
### ZK002 — frontmatter could not be parsed

**Severity:** error

**Fires when** the frontmatter is unreadable — a tab in the indentation, an unclosed quote, a
block scalar, an anchor or alias, a duplicate key, a byte-order mark, bytes that are not
valid UTF-8, or no frontmatter block at all. The note is then **excluded** from every check
that reads its frontmatter, rather than being treated as having none.

**Fix:** repair the frontmatter by hand. The message names the construct and the line. If the
file is not meant to be a note, move it out of `permanent/`.

**By hand:** open the file at the reported line. The supported subset is deliberately small —
plain scalars, quoted scalars, flow lists, block lists, lists of single-key maps — and
anything else is refused rather than guessed at.

<a id="zk003"></a>
### ZK003 — a required field is missing

**Severity:** error

**Fires when** `id`, `title`, `type`, `status` or `created` is absent or empty. One finding
per field.

**Fix:** add the field. `id` must equal the timestamp in the filename.

**By hand:** read the frontmatter and check that all five keys are present and non-empty.

<a id="zk004"></a>
### ZK004 — a field has a value outside its enum

**Severity:** error

**Fires when** `type` is not one of `permanent`, `source`, `structure`; `status` is not one
of `draft`, `seed`, `evergreen`, `archived`; or `confidence` is not one of `low`, `medium`,
`high`. An absent field is ZK003's business, not this check's.

**Fix:** use a documented value. If the vocabulary genuinely needs a new word, change
`SCHEMA.md` first, so every note is judged against one vocabulary.

**By hand:** compare each of the three fields against the lists in `references/note-format.md`.

<a id="zk005"></a>
### ZK005 — a date is not a date

**Severity:** error

**Fires when** `created` or `updated` is not `YYYY-MM-DD`, or when `updated` is earlier than
`created`.

**Fix:** write the date unquoted as `YYYY-MM-DD`. A quoted date that *looks* right is still
reported when it is not in that exact form.

**By hand:** check the two dates lie in the calendar, in order, and in the documented format.

<a id="zk006"></a>
### ZK006 — the filename and the id disagree

**Severity:** error

**Fires when** the filename is not `YYYYMMDDHHMM-slug.md`, the timestamp is not a real
date and time, or the `id` field does not match the timestamp.

**Fix:** rename the file, or correct `id`. The filename is what links resolve to, so when the
two disagree the filename is the one that other notes already depend on. IDs are identity:
renaming to fix a typo is fine, renaming to move a note is not.

**By hand:** compare the first twelve characters of the filename with the `id` field.

<a id="zk007"></a>
### ZK007 — two notes claim the same id

**Severity:** error

**Fires when** more than one note carries the same `id`. Reported once per extra note, with
every path that shares the id in the evidence.

**Fix:** these are almost always one idea written twice. Merge them, or give one a fresh id
and filename from the moment you actually split them. The evidence line names both files.

**By hand:** collect the `id` values; a duplicate jumps straight out of a sorted list.

<a id="zk008"></a>
### ZK008 — a link points at a note that does not exist

**Severity:** error

**Fires when** a frontmatter link target, or a `[[wikilink]]` in the body, does not resolve
to any note. One finding per target, not per mention: a broken target is broken in the
frontmatter and in the body's Links section, and counting it twice would inflate the total
for a single defect.

**Fix:** create the note, or point the link at the note that does exist. A link to a note you
*intend* to write is a note you have not written.

**By hand:** list every `[[...]]` and every `target:` value and check each against the
filenames in `permanent/`.

<a id="zk009"></a>
### ZK009 — a link verb is not one of the six

**Severity:** error

**Fires when** a link's `verb` is not `extends`, `supports`, `contradicts`, `source`,
`applies` or `supersedes`.

**Fix:** choose one of the six. The verb is the whole point of a typed link — an untyped link
is a mention. If none of the six fits, that is a signal about the taxonomy, and the place to
record it is `SCHEMA.md`, deliberately.

**By hand:** read the `verb:` lines. The six are short and there is no seventh.

<a id="zk010"></a>
### ZK010 — fewer than two outbound links

**Severity:** error

**Fires when** a note has zero or one outbound link. Two is the floor, not the target.

**Fix:** link the note to the ideas it extends, supports or contradicts. If you cannot name
two, the note is probably not atomic and needs splitting — a note with no relatives is
usually two half-notes sharing a title.

**By hand:** count the `target:` entries under `links:`.

<a id="zk011"></a>
### ZK011 — the note has no inbound links

**Severity:** warn

**Fires when** nothing links to a note. **Links from `structure/` do not count** — otherwise
`index.md` would cure every orphan and the check would be vacuous. Being listed in the index
is not the same as being linked, which is why an indexed note can still be an orphan.

**Fix:** link it from a note that depends on it. An orphan is invisible: nothing will lead a
reader to it, and it will not be found by following links.

**By hand:** for each note, search the other notes for its slug. Ignore hits that come only
from `structure/`.

<a id="zk012"></a>
### ZK012 — the index and the vault disagree

**Severity:** error

**Fires when** `structure/index.md` does not mention an existing note, or links to a note
that does not exist. Both findings are attached to the index file, with the offending slug as
the subject.

**Fix:** add the missing entry, or remove the dangling one. The index is a map, and a map
that is wrong in either direction is worse than no map.

**By hand:** compare the wikilinks in the index with the filenames in `permanent/`, both
ways. The second direction is the one people forget.

<a id="zk013"></a>
### ZK013 — a cited source is not in the vault

**Severity:** error

**Fires when** a path in a note's `sources:` list is not a file in the vault.

**Fix:** capture the source under `raw/`, or correct the path. This check is about the
frontmatter citation; the inline marker is ZK018, and it is a separate check because the two
can disagree — a note can cite a source it never marks, and mark one it never cites.

**By hand:** for each `sources:` entry, look for the file.

<a id="zk014"></a>
### ZK014 — a captured source records no digest

**Severity:** error

**Fires when** a file under `raw/` has an empty or absent `sha256`.

**Fix:** compute the digest and record it. Without it there is no way to know later whether
the capture still matches what was read, and the drift check has nothing to compare against.

**By hand:** run the bundled `hash` subcommand on the file and paste the result into the
frontmatter; the digest covers the body bytes only, so recording it does not change it.

<a id="zk015"></a>
### ZK015 — the note has no body

**Severity:** error

**Fires when** the file has frontmatter and nothing else.

**Fix:** write the claim and its evidence, or delete the file. A title with no body is a
bookmark, not a note; if it is a note you will write later, it belongs in `inbox/`.

**By hand:** open the file and look below the closing `---`.

<a id="zk016"></a>
### ZK016 — a tag is not in the taxonomy

**Severity:** warn

**Fires when** a note's `tags:` include one that `SCHEMA.md` does not declare. If `SCHEMA.md`
declares no tags at all, this check is not applicable rather than failing everything.

**Fix:** use an existing tag, or add the new one to `SCHEMA.md` deliberately. Tags that drift
one note at a time stop being a vocabulary.

**By hand:** compare each tag against the list in `SCHEMA.md`.

<a id="zk017"></a>
### ZK017 — a draft or seed note has gone stale

**Severity:** warn

**Fires when** `status` is `draft` or `seed` and the note has not been touched for longer
than `stale_draft_days` (default 90), measured from `updated`, falling back to `created`.

**Fix:** promote it, split it, or archive it. A seed that has been a seed for a year is not
growing, and the useful decision is usually to archive it and stop paying attention to it.

**By hand:** list the notes whose status is `draft` or `seed`, sorted by `updated`.

<a id="zk018"></a>
### ZK018 — a provenance marker points at nothing

**Severity:** error

**Fires when** an inline marker `^[raw/path/file.md]` names a file that is not in the vault.

**Fix:** capture the source under `raw/`, or remove the marker. Never leave a marker that
cannot be followed: it is a claim about where something came from, and a claim that cannot be
checked is worse than an honest absence of one.

**By hand:** collect every `^[...]` in note bodies and check each target exists.

<a id="zk019"></a>
### ZK019 — the recorded digest no longer matches

**Severity:** warn

**Fires when** a `raw/` file's recorded `sha256` differs from the digest of its body bytes.

**Fix:** **do not edit the digest.** `raw/` is immutable: a mismatch means the file changed
after capture, so the notes compiled from it may be resting on text that is no longer there.
Re-ingest the source and update the notes that cite it.

**By hand:** recompute the digest with the bundled `hash` subcommand and compare. The
evidence field shows both values.

<a id="zk020"></a>
### ZK020 — a link that says nothing

**Severity:** warn

**Fires when** a note links to itself, or links to the same target more than once.

**Fix:** remove the self-link; keep one link with the verb that fits best. Two links to one
target is not emphasis, it is a sign that the two verbs were both nearly right, which is
worth resolving rather than recording.

**By hand:** read the `links:` block and look for a repeated target or the note's own slug.

<a id="zk021"></a>
### ZK021 — two notes share a title slug

**Severity:** warn

**Fires when** two or more notes have titles that reduce to the same slug. One finding per
extra note, with all the paths in the evidence.

**Fix:** these are usually one idea; merge them, or retitle one so its title says what makes
it different.

**By hand:** slugify the titles — lowercase, non-alphanumerics to hyphens — and sort them.

**This is deliberately the only duplication check.** Detecting notes that *mean* the same
thing without sharing a title needs embeddings, which this linter does not have and does not
pretend to. A shared slug is a proxy, and a weak one: it catches the copies and misses the
paraphrases. Query-time obligations in the skill body cover the rest.

<a id="zk022"></a>
### ZK022 — a log entry carries no date

**Severity:** warn

**Fires when** a bullet in `log.md` contains no `YYYY-MM-DD` anywhere in the line.

**Fix:** date it. A log you cannot order is not a log; it is a list of things that happened
at some point.

**By hand:** read the bullets and check each has a date.

<a id="zk023"></a>
### ZK023 — the note is long

**Severity:** info

**Fires when** the body exceeds `oversized_note_words` (default 800). Word count only, code
fences included.

**Fix:** length alone is not a defect — some ideas are long. Check whether it holds one idea,
or several wearing one title. The better signal for splitting is ZK030, which looks at the
shape rather than the size.

**By hand:** count the words, then read the note and ask what its title promises.

<a id="zk024"></a>
### ZK024 — a paragraph carries no provenance

**Severity:** info

**Fires when** a note cites `provenance_min_sources` or more sources (default 3) and has a
top-level paragraph of `provenance_min_words` or more (default 25) with no `^[raw/...]`
marker. Headings, tables, lists and quotations are not paragraphs for this purpose.
**Aggregated to one finding per note**, with the offending lines in the evidence, capped at
five. A note with `provenance: note` in its frontmatter is skipped entirely — that is the
opt-out, and using it is a statement that the paragraph is your own synthesis.

**Fix:** cite the source inline, or add `provenance: note` if the paragraph really is your
own reasoning rather than a restatement of something you read.

**By hand:** for each note with three or more sources, read its long paragraphs and check
each has a marker.

**Known false positives, stated rather than discovered later:** a synthesis paragraph that
legitimately draws on all the sources at once; verbatim quotations; and languages written
without spaces between words, where the word count is meaningless. This check ships at
`info` for that reason, and is promoted only if a measurement supports it. The deterministic
half of provenance — whether the cited files exist — is ZK018 at `error`, and that is the
half worth failing a build on.

<a id="zk025"></a>
### ZK025 — the title contains "and"

**Severity:** info

**Fires when** the word "and" appears in the title, case-insensitively.

**Fix:** a title that needs "and" usually names two ideas, and the note is often two notes.
Sometimes "and" is part of one idea's name — "truth and reconciliation" is not two things —
in which case this finding is wrong and you should say so and move on.

**By hand:** read the titles.

<a id="zk026"></a>
### ZK026 — a captured source is never used

**Severity:** info

**Fires when** no note cites a `raw/` file, either in `sources:` or in an inline marker.

**Fix:** compile a note from it, or delete it and say why in the log. Every raw file is a
promise that something will be made from it; a folder of unmined sources is a reading list
wearing a vault's clothes.

**By hand:** for each file under `raw/`, search the notes for its path.

<a id="zk027"></a>
### ZK027 — a contradiction is recorded on one side only

**Severity:** info

**Fires when** note A links to note B with the verb `contradicts`, and B does not link back
to A. **The finding is attached to B** — the note missing half the relationship is the one
that needs the edit — with A's slug as the subject.

**Fix:** add the link on the other side, or with the verb that actually applies. A
contradiction is a relationship, and recording it from one side only means the reader who
arrives at B never learns that something disagrees with it.

**By hand:** find every `contradicts` link and check the target links back.

<a id="zk028"></a>
### ZK028 — the Links section and the frontmatter disagree

**Severity:** info

**Fires when** the set of wikilinks in the body differs from the set of `target:` values in
the frontmatter. Notes with no body are skipped: ZK015 already reports an empty note, and
"bring the body into line" is not useful advice for a file whose body does not exist.

**Fix:** the frontmatter is authoritative — bring the body into line. The prose is for
reading and the frontmatter is for finding, and this check exists so the two cannot drift.

**By hand:** compare the `[[...]]` links in the body with the `target:` list.

<a id="zk029"></a>
### ZK029 — the verbs have collapsed

**Severity:** info

**Fires when** the vault has at least `verb_monoculture_min_links` links (default 20) and
more than `verb_monoculture_ratio` of them (default 60%) use the same verb.

**Fix:** either the vault really is monotone — that happens, and a vault about one thing can
be all `extends` — or the taxonomy is too fine for how you actually think, in which case the
honest response is to merge verbs in `SCHEMA.md` rather than to keep assigning verbs you do
not believe. This finding is about the vault, not about a file, so it has no file.

**By hand:** count the verbs and look at the distribution. Six verbs with one of them at 90%
is a taxonomy that has collapsed to a favourite.

<a id="zk030"></a>
### ZK030 — the note has several substantial sections

**Severity:** info

**Fires when** a note has `multi_idea_sections` or more `##` sections (default 3) each
holding at least `multi_idea_section_words` words (default 40).

**Fix:** a split candidate — each section may be its own idea. This is the real splitting
signal, and it is about shape rather than length: a long single-section note is usually one
idea argued at length, while a short note with four headed sections is usually four ideas.

**By hand:** read the `##` headings and ask whether each one could stand as a title.

<a id="zk031"></a>
### ZK031 — something has been sitting in the inbox

**Severity:** info

**Fires when** a file in `inbox/` has a `created`, `captured` or `ingested` date older than
`inbox_stale_days` (default 30). Files with no readable date are not reported.

**Fix:** ingest it, or delete it and say why. An inbox is a queue, not a folder: if it only
grows, the capture step is working and the compile step is not.

**By hand:** list `inbox/` and compare the dates with today.

<a id="zk032"></a>
### ZK032 — the log is growing without bound

**Severity:** info

**Fires when** `log.md` holds more than `log_rotation_entries` entries (default 500).

**Fix:** rotate the older entries into `log-archive.md`. The log is the vault's history and
should be readable; nobody reads entry 900.

**By hand:** count the bullets.

## Deliberately not checked

Recorded here so that their absence is a decision rather than an oversight:

| Not checked | Why |
|---|---|
| semantic duplicates (notes that mean the same thing) | needs embeddings; the deterministic proxy is ZK021, and it is a weak one, as its section says |
| contradictory tags across notes | not deterministic. Partly covered by ZK027 for explicit contradictions, and otherwise by the obligation on the agent, at query time, to flag a conflict it notices |
| "the note is stale relative to its newest source" | ill-defined — a note is not invalidated by a newer source, it is contextualised by it |
| "the first paragraph should be one sentence" | computable and meaningless; it would generate noise in proportion to how many notes are written well |

# Check codes

Every code the bundled linter can report, one section each: what it fires on, what to do,
and how to find the same thing by hand when scripts cannot run on the machine you are on.

A finding is a claim, not a verdict. The linter reads frontmatter, links, dates and digests;
it cannot read meaning. When a finding and your judgement disagree, the judgement wins — but
say so in `log.md` rather than leaving the next reader to wonder.

**Every check here asserts a fact about the vault's own files.** A reference that resolves to
nothing, a digest that no longer matches, two notes claiming one identity, a log entry with
no date. Nothing here decides by a number: "800 words is too long" and "ninety days without
promoting a draft is too long" are opinions, they were once shipped with the same authority as
the facts beside them, and they are gone. The rule that removed them is in
`## What v2 retired, and why`, with every code it took.

## How to read a finding

| Field | Meaning |
|---|---|
| `code` | which check fired, e.g. `ZK010` |
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
- `warn` — the vault is inconsistent: an isolated note, a digest that no longer matches, a
  note that does not match the vocabulary its own `SCHEMA.md` declares.
- `info` — advisory, and some of it is a matter of judgement. Never fails a run unless you
  ask for it with `--fail-on info`.

Exit codes: **0** clean at the threshold · **1** findings at or above it · **2** not a vault,
or a usage error. Exit 2 with well-formed JSON on stdout means the linter did not understand
the directory, which is not the same answer as "no findings" and must never be read as one.

## Not applicable is not the same as passed

When a check has nothing to read — no `raw/` to hash, no `structure/index.md` to compare, no
permanent notes at all — it is reported in `skipped_checks` with its reason, not silently
counted as clean. A vault of three notes is not a vault that passed fifteen checks; the
report says which ones had no surface to examine.

The one to watch is `ZK003`, because a vault can switch it off by declaring nothing in its
`SCHEMA.md`. That is the intended behaviour for a vault carried in from elsewhere, and it
means a clean report from such a vault is *unjudged* on conformance rather than *conforming*.
`declared_sources` in the JSON says which dimensions were read and which were absent.

## No `--fix`, on purpose

The tool verifies; you write. Three reasons, in order of weight:

1. The highest-value findings are semantic — is this one idea or two? which verb is it
   really? — and no mechanical rule can answer them. Some of those are no longer checks at
   all, which changes the phrasing of this reason but not its weight.
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
says "0 findings, 20 baselined" is telling you something quite different from one that says
"0 findings", and this tool will not let you confuse the two.

**A baseline written under v1 keeps working.** A surviving code means what it always meant, so
its key still matches and still suppresses. A retired code matches nothing, so its key is
inert and silences nothing — but read the retirement table below before trusting an old
baseline to be complete: a finding that changed code is reported once more before it can be
baselined again under the new one.

## What v2 retired, and why

The v2 rule: **a check may assert only a fact about the vault's own files; if it needs a
number to decide, it is an opinion and does not ship.** Seventeen codes went. Retired numbers
are never reused — `ZK019` means one thing in every version — so the gaps are honest, and this
table is the record of what each one did.

Three groups, and the third is a scope decision rather than a consequence of the rule. It is
listed anyway, because a code that stops being checked is a code that stops being checked
however it got there.

**Folded into a survivor.** Same subject, one code. Each survivor's old subject is contained
in the new one, which is the only way a surviving number was allowed to change meaning.

| Retired | What it did | Now |
|---|---|---|
| `ZK004` | a `type`, `status` or `confidence` outside its enum | `ZK003` — the enum is the vault's now |
| `ZK007` | two notes claiming one `id` | `ZK006` — identity is one subject |
| `ZK009` | a link verb outside the six | `ZK003` — the six are declared, not imposed |
| `ZK011` | no note linked to this one | `ZK010` — either direction is isolation |
| `ZK013` | a `sources:` entry named no file in the vault | `ZK008` — a reference that resolves to nothing |
| `ZK016` | a tag outside the taxonomy | `ZK003` — the taxonomy is the vault's |
| `ZK018` | a `^[raw/...]` marker named no file | `ZK008` — the same defect, another surface |

**Decided by a number.**

| Retired | The number | Why it went |
|---|---|---|
| `ZK017` | 90 days in `draft` or `seed` | nothing about a ninetieth day makes a note ready |
| `ZK023` | 800 words | a long note is not a defect; some ideas are long |
| `ZK024` | 3 sources, 25 words | the reasoning it gated is still good advice, and is prose now |
| `ZK029` | 20 links, 60% one verb | a share that is honest in one vault is evasion in another |
| `ZK030` | 3 sections, 40 words each | the shape is worth noticing; the counts never decided it |
| `ZK031` | 30 days in `inbox/` | an inbox is a queue, and how long is too long is yours |
| `ZK032` | 500 log entries | nobody reads entry 900, and nobody agrees where 900 starts |

**Advisory by nature — a hint the reader was told to overrule.**

| Retired | What it did | Why it went |
|---|---|---|
| `ZK020` | a self-link, or one target linked twice | a style preference, and not what integrity means |
| `ZK021` | two notes whose titles share a slug | a weak proxy for duplication, and it said so |
| `ZK025` | "and" in the title | "truth and reconciliation" is one thing; the code admitted this |

None of the seventeen is gone because it was wrong to *think about*. What is gone is the
claim that the linter had measured something. Where the idea survives it survives as advice —
in `references/note-format.md` and `references/schema-reference.md` — which is where a
judgement call belongs.

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
### ZK003 — the note does not match the vocabulary its vault declares

**Severity:** warn

**Fires when** a note breaks any dimension its own `SCHEMA.md` declares. Six dimensions, each
independent:

| Dimension | Fires on |
|---|---|
| `required_fields` | a declared field absent or empty |
| `types` | a `type` value not in the list |
| `statuses` | a `status` value not in the list |
| `confidences` | a `confidence` value not in the list |
| `tags` | a tag not in the list |
| `verbs` | a link verb not in the list |

**An undeclared dimension is not checked, and is not defaulted.** A vault that declares
nothing is judged against nothing, and the check is reported not applicable rather than
passing — that is what makes this check safe for a vault carried in from another tool, whose
`essay` and `enquête` are not wrong for being different words. The trade is that an
undeclared dimension is unguarded, so declare the ones you care about.

**Fix:** use a declared value, or add the new one to `SCHEMA.md` deliberately. The vocabulary
that grows one note at a time is not a vocabulary, and the file is the place to argue with it
— `declared_sources` in the JSON says which dimensions were actually read.

**By hand:** read the six lists in `SCHEMA.md` and compare each note's fields against them.
A dimension that is not there is a dimension nobody is checking.

<a id="zk005"></a>
### ZK005 — a date is not a date

**Severity:** error

**Fires when** `created` or `updated` is not `YYYY-MM-DD`, or when `updated` is earlier than
`created`.

**Fix:** write the date unquoted as `YYYY-MM-DD`. A quoted date that *looks* right is still
reported when it is not in that exact form.

**By hand:** check the two dates lie in the calendar, in order, and in the documented format.

<a id="zk006"></a>
### ZK006 — identity is broken

**Severity:** error

**Fires when** the filename is not `YYYYMMDDHHMM-slug.md`, the timestamp is not a real date
and time, the `id` field does not match the timestamp, or two notes carry the same `id`.

**Fix:** rename the file, or correct `id`. The filename is what links resolve to, so when the
two disagree the filename is the one that other notes already depend on. IDs are identity:
renaming to fix a typo is fine, renaming to move a note is not. Two notes sharing an id are
almost always one idea written twice — merge them, or give one a fresh id and filename from
the moment you actually split them.

**By hand:** compare the first twelve characters of each filename with its `id`, then sort the
`id` values — a duplicate jumps straight out of a sorted list.

<a id="zk008"></a>
### ZK008 — a reference points at nothing

**Severity:** error

**Fires when** any of the four ways a note names a target fails to resolve:

| Surface | Written as |
|---|---|
| a frontmatter link | `target: 202609251200-spaced-repetition` |
| a wikilink in the body | `[[202609251200-spaced-repetition]]` |
| a citation | `sources: [raw/articles/karpathy-llm-wiki-2026.md]` |
| a provenance marker | `^[raw/articles/karpathy-llm-wiki-2026.md]` |

One finding per (note, target), not per mention. A target appears in the frontmatter and again
in the body's Links section by design, and may be named several times in the prose besides;
counting each would inflate the total for one defect.

A target resolves if it names a note, or a file in the vault. A note resolves by its name
alone — `[[202609251200-slug]]`, `[[memory/202609251200-slug]]` and either with `.md`
appended all reach the same file wherever it sits. A path under `raw/` may also be written
without the extension: `raw/articles/captured` resolves to `raw/articles/captured.md` if that
is there, and to nothing if it is not.

**Fix:** create the note, capture the source, or point the reference at what does exist. A
link to a note you *intend* to write is a note you have not written.

**By hand:** list every `[[...]]`, every `target:`, every `sources:` entry and every `^[...]`
marker, and check each against the filenames in the vault.

<a id="zk010"></a>
### ZK010 — the note is isolated

**Severity:** warn

**Fires when** a note links out to nothing, nothing links to it, or both. **Links from
`structure/` do not count** — otherwise `index.md` would cure every isolated note and the
check would be vacuous. Being listed in the index is not the same as being linked, which is
why an indexed note can still be isolated.

One link is enough to be reachable in one direction, and this check does not ask for two. The
floor of two outbound links is still the advice — a note with no relatives is usually two
half-notes sharing a title — but it was a number deciding, and the numbers are gone.

**Fix:** link it to the ideas it extends, supports or contradicts, and link it from a note
that depends on it. An isolated note is invisible: nothing will lead a reader to it, and it
will not be found by following links.

**By hand:** for each note, list its `target:` entries and search the other notes for its own
slug. Ignore hits that come only from `structure/`.

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

<a id="zk019"></a>
### ZK019 — the recorded digest no longer matches

**Severity:** warn

**Fires when** a `raw/` file's recorded `sha256` differs from the digest of its body bytes.

**Fix:** **do not edit the digest.** `raw/` is immutable: a mismatch means the file changed
after capture, so the notes compiled from it may be resting on text that is no longer there.
Re-ingest the source and update the notes that cite it.

**By hand:** recompute the digest with the bundled `hash` subcommand and compare. The
evidence field shows both values.

<a id="zk022"></a>
### ZK022 — a log entry carries no date

**Severity:** warn

**Fires when** a bullet in `log.md` contains no `YYYY-MM-DD` anywhere in the line.

**Fix:** date it. A log you cannot order is not a log; it is a list of things that happened
at some point.

**By hand:** read the bullets and check each has a date.

How long the log is allowed to get is not a check. Rotating older entries into
`log-archive.md` when the file stops being readable at a glance is still the practice, and the
judgement is yours.

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

This check is keyed on the verb `contradicts` by name. A vault whose declaration leaves it out
— or which expresses disagreement with a different verb — has no way to state the
relationship, and so has nothing to reciprocate; the check is reported not applicable. If you
disagree with something, saying so in the vocabulary is what makes the obligation apply.

<a id="zk028"></a>
### ZK028 — the Links section and the frontmatter disagree

**Severity:** info

**Fires when** the set of wikilinks in the body differs from the set of `target:` values in
the frontmatter. Notes with no body are skipped: ZK015 already reports an empty note, and
"bring the body into line" is not useful advice for a file whose body does not exist.

**Fix:** the frontmatter is authoritative — bring the body into line. The prose is for
reading and the frontmatter is for finding, and this check exists so the two cannot drift.

**By hand:** compare the `[[...]]` links in the body with the `target:` list.

## Deliberately not checked

Recorded here so that their absence is a decision rather than an oversight:

| Not checked | Why |
|---|---|
| semantic duplicates (notes that mean the same thing) | needs embeddings. There is no deterministic proxy any more: the shared-title-slug check was `ZK021` and it retired, because a proxy that catches the copies and misses the paraphrases was being read as more than it was |
| contradictory tags across notes | not deterministic. Partly covered by ZK027 for explicit contradictions, and otherwise by the obligation on the agent, at query time, to flag a conflict it notices |
| "the note is stale relative to its newest source" | ill-defined — a note is not invalidated by a newer source, it is contextualised by it |
| "the first paragraph should be one sentence" | computable and meaningless; it would generate noise in proportion to how many notes are written well |

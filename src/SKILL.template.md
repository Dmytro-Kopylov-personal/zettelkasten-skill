{{FRONTMATTER}}

# Zettelkasten Vault Maintainer

## Overview

Maintain a Zettelkasten: a vault of atomic, densely-linked notes where each note holds exactly one
idea and every claim traces back to a source. You are the maintainer, not the author of record — the
user decides what matters, and you compile, link, check and keep the structure honest.

Four operations: **init** a vault, **ingest** a source, **query** the vault, **lint** it.

The difference from a wiki is atomicity. A wiki has a page per *thing*; a Zettelkasten has a note per
*idea*, and the value lives in the links between them. A folder of beautiful unlinked notes is a
pile, not a Zettelkasten, and lint will say so.

## When to Use

- The user drops a source — a URL, a file, a paste — and asks to ingest, file or process it
- The user asks a question about what their notes contain
- The user says lint, audit or health-check
- The user asks to start, scaffold or initialise a new vault
- The user refers to their Zettelkasten, slip box or permanent notes

Don't use for:

- General note-taking in a vault this skill did not create or adopt — use the vault's own
  conventions instead of imposing these
- Long-form authored prose. A permanent note is a claim, not an essay
- Silent bulk imports. Ingest proposes; the user approves

{{ENVIRONMENT}}

## Find the vault

Stop at the first step that resolves:

1. A path the user gave in the request.
2. The `ZETTELKASTEN_VAULT_PATH` environment variable.
3. Walk upward from the working directory for a folder containing all three of `SCHEMA.md`,
   `permanent/` and `log.md`.
4. Ask. Never guess, and never run a write operation against a vault you have not confirmed.

If any of `permanent/`, `SCHEMA.md` or `log.md` is missing, the folder is not a vault. Say so and
offer to initialise it rather than writing into it.

The folder holding those three is the **vault root**, and it is the boundary of every write you
make: captures, notes, structure files and the log all live inside it. Nothing above it is yours
to touch, however related the files there look, and nothing outside it is part of the vault. When
a vault does not yet exist, it gets its own folder rather than taking over the one you are
standing in.

## Orient before you act

Every session, before the first write: read `SCHEMA.md`, read `structure/index.md`, read the last
~30 entries of `log.md`, then search `permanent/` for the entities and ideas already in play.

With timestamp IDs there is no title-based safety net. Two notes on one idea will both look
plausible and neither will be wrong enough to notice. Orientation is the only thing preventing it,
and skipping it is the most common way to corrupt a vault.

## Principles

| Principle | Rule |
|---|---|
| Atomicity | One idea per note. If the title needs "and", it is two notes. |
| Dense linking | At least two outbound links per note, and ideally at least one inbound. A note with either direction missing is reported. |
| Stable identity | `YYYYMMDDHHMM-slug.md`, with `id:` matching the filename. Titles may change; IDs do not. |
| Provenance | Every factual claim traces to a source: `^[raw/articles/x.md]` inline, and the raw path in `sources:`. |
| Semantic links | Each link carries a verb: `extends`, `supports`, `contradicts`, `source`, `applies`, `supersedes`. |
| Human triage | You propose; the user approves. Nothing is written to `permanent/` before confirmation unless the user explicitly asked for automated mode. |

The long forms — the Page Threshold, the atomicity test, verb semantics, the contradiction policy —
are in `references/schema-reference.md`. **The vault's own `SCHEMA.md` declares the vocabulary**, so
read it first: the values above are what `init` scaffolds, and a vault that has changed them means
it.

## Note format

Full contract in `references/note-format.md`; the skeleton is:

```markdown
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
---

The idea, stated in one sentence.

Elaboration, evidence, counterarguments. Cite as you go, not at the end. ^[raw/articles/karpathy-llm-wiki-2026.md]

## Links

- **supports** [[202609251200-spaced-repetition]] — both describe a fixed capacity
- **extends** [[202609240900-working-memory-limits]] — narrows it to deliberate attention
```

`status` moves `draft` → `seed` → `evergreen`; `archived` retires a note without deleting it.
`confidence` is `high` only when several sources agree. `id` is **quoted**: it is twelve
digits, so an editor that infers a type from the text will call it a number and offer to
edit it as one. Both spellings parse and lint the same — quote it so the value is what it
looks like.

New notes go at the top level of `permanent/`. A vault that files its notes in subdirectories
is read correctly, because every check walks the whole tree, so search `permanent/`
recursively and leave an existing filing alone; only write into a subdirectory when the
vault's `SCHEMA.md` asks for it.

## Init

Only when the folder is not already a vault, and only after asking where it lives.

1. Give the vault **its own folder** — `zettelkasten/` under the directory you were pointed at,
   unless the user names another path — and confirm it before writing. A vault that shares a
   directory with anything else puts that whole directory inside its blast radius, and the vault
   root is the only place this skill writes. The folder must be empty, or hold nothing but a
   vault.
2. Create `raw/articles`, `raw/papers`, `raw/notes`, `permanent`, `structure`, `inbox`.
3. Materialise the scaffold, one template per file: `SCHEMA.md` from `templates/SCHEMA.md`,
   `structure/index.md` from `templates/index.md`, `structure/concept-table.md` from
   `templates/concept-table.md`, `structure/overview.md` from `templates/overview.md`, and
   `log.md` from `templates/log.md`. Leave the examples inside their code fences — they show
   the format, and an unfenced one would be read as a real entry.
4. Ask the user what domain the vault covers, and write it into `SCHEMA.md` — a vault without a
   domain accumulates everything and links nothing.
5. Propose one or two first sources to ingest rather than leaving them at an empty vault.
6. Log the init.

## Ingest

One source at a time; batch only when the user hands over several at once.

1. **Capture.** Write the source to `raw/{articles|papers|notes}/descriptive-name.md` with
   `source_url`, `ingested` and a `sha256` of the body. If that URL was ingested before, compare the
   digest: identical means stop and say so — re-ingest is a no-op, not an append.
2. **Discuss.** Say what the source actually claims and what it changes. Skip only in automated mode.
3. **Search first.** Look for existing notes on every entity and idea it touches. Creating a
   near-duplicate is the failure this step exists to prevent.
4. **Propose a plan — do not write yet.** List notes to create (with titles and one-line theses),
   notes to update, and the links between them, with verbs. Wait for confirmation.
5. **Create** only for ideas clearing the Page Threshold; **update** existing notes with new evidence
   and a bumped `updated` date.
6. **Link** both directions. A new note with no inbound link is invisible — go and add one.
7. **Register.** Add the note to `structure/index.md` and, if it introduces a durable concept, to
   `structure/concept-table.md`.
8. **Log** the operation, then report every file created or updated.

A single source typically yields three to eight notes; a long article about one idea may yield one.
If a source would touch more than ten existing notes, confirm the scope before writing anything.

## Query

1. Read `structure/index.md` and `structure/concept-table.md`.
2. Search the vault for the terms in the question — the index alone misses content.
3. **Read the notes in full.** Never answer from a snippet or a search hit.
4. Follow links one or two hops from the most relevant notes.
5. Answer with citations to specific note IDs, and say where the vault is silent. A confident answer
   that the vault does not support is worse than "nothing here on that".
6. **File the answer back** if it is genuinely new synthesis — a comparison, a resolution of two
   notes, a pattern across several. Do not file lookups; a note that restates one source is noise.
7. Log the query and whether it was filed.

## Lint

Report only. **Never fix without confirmation** — the fix is a proposal like any other.

Run the bundled linter for the deterministic checks; `references/lint-checks.md` documents every
check code, its predicate and its remediation, and `references/tool-free-fallback.md` gives the
manual procedure when the linter cannot run.

Then interpret, in this order:

1. **Structural errors first** — broken references, broken identity, frontmatter that will not
   parse, bad dates. These are not stylistic; a reference that resolves to nothing means the graph
   is lying about itself.
2. **Vocabulary** — a note that does not match what its own `SCHEMA.md` declares. Use a declared
   value, or propose the addition to the schema deliberately; do not quietly widen it.
3. **Isolation** — nothing links to the note, or the note links to nothing. Propose specific links
   with verbs, not "consider linking this".
4. **Decay** — a source whose content has drifted from its recorded digest, a note with no body, a
   log entry with no date.
5. **Advisory** — unreciprocated contradictions, an uncited source, a body that disagrees with its
   frontmatter. Advisory items are information, not a to-do list.

Group findings by fix, propose the batch, and report the delta after applying it. If the vault has
no baseline yet and the findings are numerous, say so plainly rather than presenting a hundred
findings as a hundred problems.

## Common Pitfalls

1. **Writing before proposing.** The propose step is the skill's whole contract with the user. An
   ingest that writes first has already broken it, even if every note it wrote was good.
2. **Modifying `raw/`.** Sources are immutable. Corrections belong in notes; drift belongs in a
   re-ingest. Nothing in this skill writes to `raw/` after capture.
3. **Skipping orientation.** See above — duplicates are invisible without it.
4. **A note per thing instead of per idea.** "Karpathy's LLM wiki" is the thing; "compilation beats
   retrieval for repeated questions" is the idea. Notes about things become a wiki.
5. **Overwriting on contradiction.** New evidence that conflicts gets its own note with a
   `contradicts` link and dates on both sides. Never edit the old claim into agreement.
6. **Filing everything.** Every query result filed is a vault that stops being navigable. File
   synthesis; drop lookups.
7. **Treating lint as a to-do list.** Lint reports; the user decides. Some findings are intentional.
8. **Auto-fixing.** Mechanical fixes are exactly where a wrong edit corrupts quietly — an index entry
   under the wrong heading, a date bumped over a real change.
9. **Reporting a clean lint when checks could not run.** If the linter was unavailable and you did the
   manual pass, name the checks you could not perform. "Clean" is a claim about coverage, not about
   your confidence.
10. **Letting the digest block the capture.** Write the capture with `sha256: PENDING`, compute the
    digest of the body, then patch it in — hashing is its own step, and the digest covers body bytes
    only, so frontmatter written afterwards does not invalidate it. Verify by re-running the digest
    and comparing the stored body against the source, byte for byte.
11. **Reaching for `supports` inside a single ingest.** Notes compiled from one source are not
    independent evidence for each other, and that is exactly what `supports` claims. `extends` and
    `applies` state the relation honestly, and a reciprocal pair is fine when each direction is true
    on its own. When a verb you would normally expect is absent, say why in `log.md`.
12. **Writing outside the vault root.** A file that is not inside the vault root is not yours to
    touch, however related it looks. The directory above a vault usually holds someone else's work,
    and a vault sharing its directory with other files has all of them inside its blast radius. If
    a source or a note seems to require a change out there, say so and let the user make it.

## Verification Checklist

- [ ] The vault path was confirmed, not guessed
- [ ] `SCHEMA.md`, `structure/index.md` and recent `log.md` were read before any write
- [ ] A plan was proposed and confirmed before the first write to `permanent/`
- [ ] Every new note has ≥2 outbound links whose targets exist, and ≥1 inbound link
- [ ] Every link carries one of the six verbs
- [ ] Every factual claim cites a path that exists under `raw/`
- [ ] `structure/index.md` lists every note created or changed
- [ ] `log.md` has one well-formed entry for the operation
- [ ] Nothing under `raw/` was modified
- [ ] Nothing outside the vault root was created, modified or deleted
- [ ] Lint was run after writing, and its delta reported — or the checks that could not run were named

## One-Shot Recipes

**Ingest one URL.** Confirm the vault → capture to `raw/articles/` with the digest → discuss what it
claims → search for existing notes → propose create/update/link list → on confirmation, write, link,
index, log → run lint → report the delta.

**Answer a question.** Read index and concept table → search → read the candidate notes in full →
follow one or two hops → answer with note IDs and name the gaps → if it is real synthesis, offer to
file it as a note.

**Lint and repair.** Run the linter → report grouped by fix, structural first → propose the batch →
on confirmation apply it → re-run lint → report what changed and what remains.

**Start a vault.** Confirm the path is empty → create the structure from `templates/` → ask for the
domain and write it into `SCHEMA.md` → propose the first two sources to ingest → log it.

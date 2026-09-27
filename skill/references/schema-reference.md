# The long forms

The parts of the method that do not fit in a table: what clears the threshold for a note,
how to tell one idea from two, what each verb commits you to, and what to do when a source
contradicts a note you already trust.

**`SCHEMA.md` in the vault overrides everything here.** Where the two differ, the vault is
right and this file is a default. Read it before the first write of a session.

## The vault

```text
SCHEMA.md                 what this vault is about, and the vocabulary it declares
log.md                    one line per operation, oldest first
permanent/                the notes: atomic, linked, sourced — may be filed in subdirectories
raw/articles/             captured sources, immutable
raw/papers/
raw/notes/
structure/index.md        every note, one line each
structure/concept-table.md the durable concepts and their canonical note
structure/overview.md     what the vault is about, for a newcomer
inbox/                    captures that are not notes yet
```

A folder without `permanent/`, `SCHEMA.md` and `log.md` is not a vault. Say so and offer to
initialise it rather than writing into it.

`permanent/` may be filed into subdirectories, and every check walks the whole tree, so a
vault filed by topic or by year reads the same as a flat one. A link resolves by name alone:
`[[202609251200-slug]]` finds its note wherever it sits, and so do `[[memory/202609251200-slug]]`
and the same with `.md` appended. The other directories are read **flat** — `structure/`'s
files have fixed names and fixed roles, so a nested `index.md` is a sub-list rather than the
index, and a vault that has no `structure/index.md` is told so instead of being silently
indexed by the wrong file.

## The atomicity test

One idea per note. Three tests, in the order that resolves the question fastest:

1. **The title test.** If the title needs "and", it is two notes. This catches most of them,
   with the standing caveat that it is a hint rather than a verdict: "truth and
   reconciliation" is one thing.
2. **The deletion test.** Delete one clause. Does the note still say something true and
   complete? Then the clause was a second note.
3. **The link test.** Can you name two different notes this one extends, supports or
   contradicts? A note with no relatives is usually two half-notes sharing a title. Two
   outbound links is the working floor for this reason — advice to a writer, not a rule the
   linter enforces: a note that links to nothing at all is reported (`ZK010`), and one that
   links once is reported by nobody.

The failure mode is not a note that is too long. It is a note that answers two questions, so
that neither answer can be linked precisely, and a reader who arrives for one of them gets
both.

### The Page Threshold

A source earns a permanent note when the idea is one you would want to find again **without
the source in hand** — roughly, whenever the idea would survive the source being deleted.

- A passing mention does not clear it. Neither does a restatement of the source's own
  abstract.
- An idea you will build on does. So does a claim you disagree with.
- The unit is the *idea*, not the source and not the paragraph. One paper often yields
  three to eight notes, and a long article about one idea yields one.

There is no numeric threshold, deliberately: the test is whether the idea stands alone, and
no word count can answer that. The observable proxy is **notes per source**. A vault
averaging far above one note per source is applying the threshold too loosely; a vault where
every source yields exactly one note is compiling abstracts, which is a wiki.

## Verb semantics

The verb is what makes a link a statement rather than a connection. Choosing between two
candidates is worth a moment: the wrong verb is a small lie the graph tells forever.

- **`extends`** — the target is right, and this note says more. The natural verb for a
  refinement, a special case you are naming, or a mechanism the target left implicit.
- **`supports`** — the target is a claim, this note is evidence for it, from a different
  place. Use it when the two notes could have been written independently and happen to
  agree.
- **`contradicts`** — the target is wrong, or right in a narrower domain than it claims.
  **The target must link back** (`ZK027`). See the contradiction policy below.
- **`source`** — the target is where the material came from. The only verb that points at a
  summary note rather than a claim, and the only one that usually also appears in `sources:`
  and as an inline marker.
- **`applies`** — the target is a general idea and this note uses it on a particular case.
  The direction matters: the application `applies` the general note, not the reverse.
- **`supersedes`** — this note replaces the target. The target stays, and stays linkable: a
  vault that deletes what it no longer believes cannot show that it changed its mind.

If none of the six fits, that is information about the vocabulary, not about the link. Record
it in `SCHEMA.md` deliberately; do not reach for the nearest verb and move on.

### When the verbs stop fitting

A vault where almost every link uses one verb is worth a look: either it is genuinely about
one line of argument, or the verb list is finer than the way you actually think, and the
verbs are being assigned rather than chosen. Nothing reports this. It was `ZK029` until v2,
as a ratio against a ceiling, and the ratio was an opinion — a share of links that is honest
in one vault is evasion in another. The judgement is yours now, and the observable is in the
report: `metrics.verb_distribution` counts the links by verb. Read it, and if it says what
you already feared, merge the verbs or accept them in `SCHEMA.md` where a reader can see it.

## Contradictions

New evidence that conflicts with an existing note **never edits that note into agreement**.

1. Write a new note stating the conflicting claim, with its own sources and date.
2. Link it to the old note with `contradicts`, and link back from the old note.
3. Leave both notes readable as they were written. A reader should be able to see what was
   believed, when, and on what evidence.
4. If the new evidence is decisive, mark the old note `archived` and link `supersedes` from
   the new one — but do not delete it.

The old claim may have been right and the new source wrong. Overwriting destroys the only
record that could settle it, and a vault whose history cannot be read is a vault you cannot
audit.

## Adoption

A vault that already has notes does not become a Zettelkasten in one pass, and trying is how
the skill gets uninstalled. The order that works:

1. **Read `SCHEMA.md` and `structure/index.md`.** If the vault has its own conventions,
   follow them and say what you are following instead of importing these wholesale. If it
   declares no vocabulary, that is not a gap to fill in for it: report what the linter says
   and leave the declaration to the vault's owner.
2. **Lint, then baseline.** Hundreds of findings on an existing vault is the expected
   result. Record the baseline rather than fixing them all, and read the report as a map of
   where the vault is uneven.
3. **Fix the structural errors first** — broken references, broken identity, dates. They are
   mechanical and they make every later measurement trustworthy.
4. **Then the isolated notes**, in batches, with proposed links rather than a list of
   complaints.
5. **Adopt the format for new notes immediately**, and convert old notes only when you are
   already editing them for another reason.

Do not convert the whole vault before writing anything new in it. The compounding only
starts once new notes are arriving in the new format, and a conversion project with no
arrivals is the most common way this ends.

## The vocabulary

Six dimensions, declared in `SCHEMA.md`'s frontmatter as flat lists. Each one is checked
against the notes, and each is independent of the others:

| Dimension | What it declares |
|---|---|
| `tags` | the subjects this vault writes about |
| `required_fields` | the frontmatter keys every note must carry |
| `types` | the kinds of note this vault keeps |
| `statuses` | the stages a note moves through |
| `confidences` | how sure a note is allowed to say it is |
| `verbs` | the link verbs this vault uses |

One check reads them — `ZK003` — and it reports one finding per note per violation.

**An absent dimension is not checked, and it is not defaulted.** That is the rule that makes
the rest safe: `init` scaffolds a starting declaration into every new vault, but the linter
holds no copy of it, and a vault that declares nothing is judged on nothing. A vault carried
in from another tool is not wrong for calling its notes `essay` rather than `permanent`; it
is simply not asked. The trade is real and worth stating: an undeclared dimension is an
unguarded one, so declare the ones you care about.

The JSON reports which dimensions were read and where each came from, so a declaration that
silently stopped being parsed — a typo in a key name, a nested mapping the subset parser
refuses — is visible in the output rather than inferred from a shorter report.

```json
"declared": {"statuses": ["draft", "seed"], "tags": ["method"]},
"declared_sources": {
  "tags": "SCHEMA.md", "statuses": "SCHEMA.md", "types": "not declared",
  "confidences": "not declared", "required_fields": "not declared", "verbs": "not declared"
}
```

`verbs` is the one with a consequence beyond conformance: `ZK027` obliges a `contradicts`
link to be returned, and it is keyed on that verb. Declare a verb list that leaves
`contradicts` out — or declare none and never use the word — and there is no reciprocity to
check, because the vault has no way to say "this disagrees with that" in the first place.

### Writing a declaration

Flat lists, not nested mappings: the linter reads the frontmatter with a deliberately small
YAML subset that rejects nesting outright, so `tags: [a, b]` parses and a `tags:` followed by
indented `- a` lines does not. That is the same form `tags:` has always taken here.

Change a list when the vault's own practice justifies it, and change it in `SCHEMA.md` rather
than in your head: a vocabulary nobody can read is a vocabulary nobody can argue with. If a
value keeps being reported, the choice is to add it to the list or to stop writing it — the
one thing that does not work is leaving the finding and the note disagreeing indefinitely.

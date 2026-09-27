# Linting without the linter

The bundled linter is one file of stdlib Python and runs anywhere Python 3.11+ does, with no
installation, no virtual environment and no network. Use it when you can.

This file is for when you cannot: a sandbox with no interpreter, a policy that forbids
running bundled scripts, a vault the tool cannot read. In that case the checks do not
disappear — they become something you do by hand, more slowly and less reliably. What must
not happen is that they become nothing, and the report comes back saying "clean".

**"Clean" is a claim about coverage, not about confidence.** A manual pass that could not
compute a digest ran fourteen of the fifteen checks, and it says so.

## The manual pass, in order

Work in this order and stop when the user's patience runs out — not when you feel finished.
The order is the value: the first group makes the rest trustworthy.

### 1. Structural: the vault is lying about itself

Read the frontmatter of every note.

| Look for | Code |
|---|---|
| `permanent/`, `SCHEMA.md` or `log.md` missing | `ZK001` |
| frontmatter that will not parse — tabs, anchors, block scalars, a duplicate key | `ZK002` |
| a field the vault declares required that is absent or empty, or a value outside the vocabulary its own `SCHEMA.md` declares | `ZK003` |
| a date that is not `YYYY-MM-DD`, or `updated` before `created` | `ZK005` |
| the filename's twelve digits not matching `id`, or two notes sharing an `id` | `ZK006` |
| a reference that resolves to nothing — a link target, a `sources:` path, a `^[raw/...]` marker | `ZK008` |

**`ZK003` checks only what the vault declares.** Read the six lists in `SCHEMA.md` —
`required_fields`, `types`, `statuses`, `confidences`, `tags`, `verbs` — and compare the notes
against those. A dimension the file does not declare is not a defect and must not be reported
as one, however odd the note looks: a vault that calls its notes `essay` is not wrong.

`ZK001`, `ZK002` and `ZK006` are the ones to do first, because every later check depends on
the note set being right, and a note whose frontmatter will not parse is invisible to
everything downstream of it.

### 2. Decay: the vault is drifting

| Look for | Code |
|---|---|
| a note nothing links to, a note that links to nothing, or both — links from `structure/` do not count | `ZK010` |
| the index missing a note, or naming one that is not there | `ZK012` |
| a `raw/` file with no `sha256` | `ZK014` |
| a note with no body | `ZK015` |
| a `raw/` digest that no longer matches its file | `ZK019` |
| a `log.md` bullet with no date | `ZK022` |

**The isolation pass is the one that needs a system.** List every note's slug, then, for each
note, list what it links to; invert that into an inbound map. Reading notes one at a time and
trying to remember who mentioned them is how isolated notes survive a manual lint. Ignore
links that come only from `structure/`, and remember that the finding is either direction:
linking out to nothing counts, and so does having nothing link in.

**The digest pass needs a digest.** If you have no way to compute one, say that `ZK014` and
`ZK019` were not run rather than reporting them as passing. A wrong digest is worse than a
missing one, because the drift check will then fire on everything.

**A reference is resolved by name, and one resolver answers for all four surfaces.** A note
resolves by its slug wherever it sits, with or without `.md`; a file under `raw/` resolves
with or without its extension. Everything else is a reference to nothing.

### 3. Advisory: the vault is telling you something

| Look for | Code |
|---|---|
| a `raw/` file no note cites | `ZK026` |
| a `contradicts` link the target does not return | `ZK027` |
| the body's links disagreeing with the frontmatter | `ZK028` |

These are information, not a to-do list. Report them grouped, say which ones you would act
on and why, and leave the decision with the user.

**Nothing in this pass decides by a number.** No word count, no day count, no share of links.
If you find yourself reaching for one — "this note is long", "this draft is old", "this vault
uses one verb too much" — that is a judgement, and it is worth saying. It is not a finding,
and it must not be reported with a code: there is no code for it any more, and inventing one
gives an opinion the same authority as a broken reference.

## Reporting a manual pass

Do all of this in the reply, in this order:

1. **What ran.** Name the groups you completed.
2. **What did not run, and why.** By code or by group: "`ZK019` was not run — no way to
   compute a digest on this machine". This is the sentence that keeps a partial pass from
   reading as a clean vault.
3. **Findings, structural first**, grouped by the fix rather than by the file, since the same
   fix usually applies to several.
4. **The delta**, if this is a re-check: what changed since the last one.

Do not summarise a hundred findings as a hundred problems, and do not summarise ten real
ones as "a few issues". If the vault has no baseline and the count is large, say plainly that
the number is a first measurement rather than a verdict on the vault.

`references/lint-checks.md` gives, for every code, what it fires on, what to do about it, and
the by-hand procedure — read the entry before reporting a finding you are unsure of, since a
manual pass has no test suite behind it.

## What a manual pass is worse at

Worth saying out loud, because it is the reason to prefer the script:

- **Exhaustiveness.** Every surviving check is a total comparison — all notes against the
  index, all references against the file tree, every digest against its bytes. A person does
  this well for twenty notes and starts sampling at two hundred, which is exactly when the
  one broken reference is the one that matters.
- **Consistency.** The mechanical checks are the ones you will skip when a vault is large,
  which is when they matter most.
- **Order.** Two runs by hand will not agree on the order of findings, so the diff between
  them is noise.

The manual pass is a genuine fallback for a vault of tens of notes and a polite fiction for
one of thousands. Say which one you are looking at.

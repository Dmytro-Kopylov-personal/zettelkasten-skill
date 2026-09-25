# Linting without the linter

The bundled linter is one file of stdlib Python and runs anywhere Python 3.11+ does, with no
installation, no virtual environment and no network. Use it when you can.

This file is for when you cannot: a sandbox with no interpreter, a policy that forbids
running bundled scripts, a vault the tool cannot read. In that case the checks do not
disappear — they become something you do by hand, more slowly and less reliably. What must
not happen is that they become nothing, and the report comes back saying "clean".

**"Clean" is a claim about coverage, not about confidence.** A manual pass that ran eight of
thirty-two checks is a report of eight checks, and it says so.

## The manual pass, in order

Work in this order and stop when the user's patience runs out — not when you feel finished.
The order is the value: the first group makes the rest trustworthy.

### 1. Structural: the vault is lying about itself

Read the frontmatter of every note.

| Look for | Code |
|---|---|
| `permanent/`, `SCHEMA.md` or `log.md` missing | `ZK001` |
| frontmatter that will not parse — tabs, anchors, block scalars, a duplicate key | `ZK002` |
| a required field absent or empty: `id`, `title`, `type`, `status`, `created` | `ZK003` |
| a value outside its vocabulary (`type`, `status`, `confidence`) | `ZK004` |
| a date that is not `YYYY-MM-DD`, or `updated` before `created` | `ZK005` |
| the filename's twelve digits not matching `id` | `ZK006` |
| two notes sharing an `id` | `ZK007` |
| a link target, frontmatter or `[[wikilink]]`, that resolves to no note | `ZK008` |
| a verb outside the six | `ZK009` |
| fewer than two outbound links | `ZK010` |

`ZK001`, `ZK003` and `ZK006` are the ones to do first, because every later count depends on
the note set being right.

### 2. Decay: the vault is drifting

| Look for | Code |
|---|---|
| a note nothing links to — links from `structure/` do not count | `ZK011` |
| the index missing a note, or naming one that is not there | `ZK012` |
| a `sources:` path that is not a file | `ZK013` |
| a `raw/` file with no `sha256` | `ZK014` |
| a note with no body | `ZK015` |
| a tag outside the taxonomy in `SCHEMA.md` | `ZK016` |
| a `draft` or `seed` older than the vault's stale threshold | `ZK017` |
| a `^[raw/...]` marker pointing at nothing | `ZK018` |
| a `raw/` digest that no longer matches its file | `ZK019` |
| a self-link, or two links to one target | `ZK020` |
| two notes whose titles slugify the same way | `ZK021` |
| a `log.md` bullet with no date | `ZK022` |

**The orphan pass is the one that needs a system.** List every note's slug, then, for each
note, list what it links to; invert that into an inbound map. Reading notes one at a time and
trying to remember who mentioned them is how orphans survive a manual lint. Ignore links that
come only from `structure/`.

**The digest pass needs a digest.** If you have no way to compute one, say that
`ZK014` and `ZK019` were not run rather than reporting them as passing. A wrong digest is
worse than a missing one, because the drift check will then fire on everything.

### 3. Advisory: the vault is telling you something

| Look for | Code |
|---|---|
| a note past the length threshold | `ZK023` |
| a long paragraph in a multi-source note with no inline marker | `ZK024` |
| "and" in a title | `ZK025` |
| a `raw/` file no note cites | `ZK026` |
| a `contradicts` link the target does not return | `ZK027` |
| the body's links disagreeing with the frontmatter | `ZK028` |
| one verb holding most of the links | `ZK029` |
| several substantial sections in one note | `ZK030` |
| a capture sitting in `inbox/` past the stale threshold | `ZK031` |
| a log past the rotation threshold | `ZK032` |

These are information, not a to-do list. Report them grouped, say which ones you would act
on and why, and leave the decision with the user.

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

- **Counting.** Link counts, word counts, verb distributions. People are unreliable at
  estimating these, and quietly confident about it.
- **Consistency.** The mechanical checks are exactly the ones you will skip when a vault is
  large, which is when they matter most.
- **Order.** Two runs by hand will not agree on the order of findings, so the diff between
  them is noise.

The manual pass is a genuine fallback for a vault of tens of notes and a polite fiction for
one of thousands. Say which one you are looking at.

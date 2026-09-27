# vault_nested — a clean vault whose notes are not in the top directory

Written by hand, before the linter is run against it. The test asserts **set equality**:
every file below must produce exactly the finding listed against it, and the linter must
produce no finding that is not listed. "None" is a claim, not an absence of information.

**Predicted: 0 findings, exit 0, 4 notes, 8 links, 1 raw source, orphan_rate 0.0.**
Predicted not-applicable: `ZK027` alone — no `contradicts` verb is used anywhere in this
vault, unlike `vault_clean`, which has a reciprocal pair and so runs it.

## What this fixture is for

Every other fixture is flat. `permanent.glob("*.md")` and `structure.glob("*.md")` are
non-recursive while `raw/` and `inbox/` are recursive, so before this fixture existed a
note one directory deep was **invisible**: the vault loaded zero notes and reported
"0 notes, no findings", exit 0. A silent report of success is the failure mode this
repository exists to catch, and no flat fixture can catch it.

So this fixture is `vault_clean` reorganised: the same well-formedness, the only variable
changed being where the files sit. Each mutation below was run, and each must fail:

| Mutation | What must break | Result |
|---|---|---|
| `rglob` → `glob` on `permanent/` | 0 notes load; every note disappears from the report | 4 failed |
| dropping the `permanent/`-prefixed form from `Vault.link_index` | `202609200900`'s long-form link becomes a broken `ZK008` | 2 failed |
| dropping the `.md`-suffixed form from `Vault.link_index` | `202609200903`'s link becomes a broken `ZK008` | 2 failed |
| `inbound_counts` back to keying on the target string | `202609200902` and `202609200901` each lose one of their two inbound links and become false `ZK010` isolated notes | 7 failed |

The last two rows only fail because this fixture writes three different spellings of the
same idea: `202609200901-spaced-repetition` (the short form Obsidian writes by default),
`permanent/memory/202609200902-working-memory` (the vault-relative long form) and
`202609200901-spaced-repetition.md` (the extension, which Obsidian also resolves). Each was
run as a mutation before being trusted, and the `.md` form found a real gap: it was handled
by the old code and the new, and covered by no fixture at all, so deleting the branch left
the suite green. It is now covered — for a form Obsidian accepts, an unexercised branch and
a missing one look identical from the inside.

**`structure/` is deliberately not recursive, and reaching that cost a mutation that did not
fail.** The first version of this fixture also recursed into `structure/` and keyed the
result by path, so a nested `structure/topics/index.md` could not clobber the real index.
Flipping that `rglob` back to `glob` left all 534 tests green: `structure/index.md` is a
top-level file, so recursion adds only files *nothing reads*. The only thing it bought was a
hazard — under basename keying the nested index took over, and `ZK012` then fired on the two
notes it did not list. A layout with a meaning to give a nested file is recursed; one without
is left flat and says so where the layout is defined.

## Files

| File | Purpose | Expected findings |
|---|---|---|
| `SCHEMA.md` | Declares all six vocabulary dimensions, as `vault_clean` does — conformance reads frontmatter, so where the notes live must not change its answer | None |
| `log.md` | Three dated entries; no check counts them any more | None |
| `structure/index.md` | Lists all 4 notes by slug, the short form Obsidian writes by default | None |
| `structure/overview.md` | Prose, no links — `structure/` is never counted toward anyone's inbound links | None |
| `raw/articles/nested-source.md` | Cited by all 4 notes; digest recorded and correct | None |
| `permanent/cognition/202609200900-attention-budget.md` | Links to `202609200901` by the short form and to `202609200902` by the **vault-relative long form**, in frontmatter and body alike | None |
| `permanent/cognition/202609200901-spaced-repetition.md` | Two links, both short form | None |
| `permanent/memory/202609200902-working-memory.md` | The long-form link target: two inbound links, one written the long way | None |
| `permanent/memory/202609200903-retrieval-beats-review.md` | Links to `202609200901` **with the `.md` extension**, which Obsidian also resolves | None |

## Why these links

Note *i* links to notes *i+1* and *i+2* (mod 4), so every note has exactly two outbound and
two inbound links, and the isolation check has nothing to report — without `structure/` curing
anything, since `structure/` links are excluded from the inbound count by design. `contradicts`
is not used at all, which is what makes `ZK027` not-applicable rather than passing: a check
that could not run must say so, because silence and success are indistinguishable in a count.

## The link spellings Obsidian actually writes

Obsidian's default is `newLinkFormat: shortest`, which is exactly the short form used here
and in every other fixture. It lengthens a link only when two notes share a basename, which
the twelve-digit filename prefix prevents — and which `ZK006`/`ZK007` check. A user who sets
`newLinkFormat` to `absolute` gets the long form everywhere, so one link is written that way
here, and a third is written with the extension, to prove the linter resolves every spelling
Obsidian accepts and that they credit the same note. That is also why inbound counts key on
the *note* rather than on the string: the same target written three ways is one inbound link,
and a count that keyed on the string would report two false orphans.

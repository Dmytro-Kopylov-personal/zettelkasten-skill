# vault_regressions — three defects that were fixed, and the fixtures that keep them fixed

Written by hand before the linter was run against it.

**Expected: 5 findings across 4 codes, exit 1 at every threshold, 5 notes.**

Every other fixture in this corpus pins a check against *inputs*. This one pins fixes against
the *code that was wrong*, because each shipped and passed the full suite while being wrong —
no existing fixture had a shape that could tell the difference. A regression fixture earns its
place only if it fails when the bug comes back, so each trap below was verified by
reintroducing the original code and watching the finding set move. The mutation is recorded
with each one.

Two of the three original traps still pin a live check. The third — the ordered-list trap for
the provenance check — lost its check to v2 and is kept as a negative control; it is marked
below, and its files stay exactly as they were.

## Trap 1 — a broken link is one defect, not two (ZK008)

The body's `## Links` section restates the frontmatter by design, so a broken target appears
*twice* in any well-formed but wrong note: once in `links:` and once as a wikilink. Both loops
that walk those two sources share a `reported` set so the pair yields one finding. The
frontmatter loop never populated that set, which made the guard in the body loop dead: every
broken link was reported twice, and the total was meaningless.

Two notes carry it, because there are two loops and each one had the same hole:

| Note | Where the target appears | Which loop must dedupe | Evidence shape |
|---|---|---|---|
| `202609281001-question-the-method.md` | frontmatter `links:` **and** `## Links` | the body loop, against the frontmatter's entry | `- target: …` (frontmatter form) |
| `202609281005-hand-edited-links.md` | twice in `## Links`, absent from `links:` | the body loop, against its own earlier mention | `[[…]]` (wikilink form) |

The second note is why the target is absent from its frontmatter: with the target in both
places the first loop populates `reported` and the second loop's guard is exercised by
accident, so the body-loop hole stays hidden. `202609289998-also-missing` is named twice in
one Links section for exactly this reason.

**Mutation:** removing `reported.add(target)` from the body loop moves ZK008 from 2 to 3
findings — the second mention of `also-missing` becomes its own finding.

## Trap 2 — an ordered list is not a paragraph (retired with ZK024)

> **This trap no longer pins a check.** The provenance check was one of the ones that decided
> by a number — a paragraph of 25 words with no marker — and v2 retired it. Both notes are kept
> exactly as they were, and the fixture now asserts that nothing fires on either of them. What
> is lost is the count assertion; what is kept is the input, which is the only record of the
> false positive that shaped the check while it existed.

The provenance check judged *top-level paragraphs* ≥25 words with no `^[...]` marker. Its skip
list covered headings, quotes, tables and bullet lists but not numbered ones, so an ordered
step was read as prose. A three-source note giving instructions was told to cite a source for
its own step 1 — the false positive that gets a check switched off.

| Note | Shape | v1 | v2 |
|---|---|---|---|
| `202609281002-ordered-reasons.md` | 3 sources; step 1 is 40 words, unmarked | **none** — it is a list item | none |
| `202609281003-unmarked-claim.md` | 3 sources; one 35-word prose paragraph, unmarked | **one** — this is the real thing | none |

The pair was the point: the negative control alone could not distinguish a fixed check from a
check that stopped firing, so `202609281003-unmarked-claim.md` was the positive control. With
the check gone, neither note can fail the suite, and that is stated here rather than left for a
reader to infer from a finding that quietly disappeared.

**Mutation (v1 only):** removing `ORDERED_ITEM_RE` from the skip tuple moved ZK024 from 1
finding to 2. There is no mutation left to run.

## Trap 3 — a note named `index` is still a note (ZK010)

`check_isolation` skipped any note whose slug was `index`. `slug` is the filename stem and
`structure/` is loaded into `vault.structure`, never into `vault.notes` — so that exemption
could never match the vault's real index and matched only a *note* the user had filed as
`permanent/index.md`. A hand-kept index of one's own notes is exactly the kind of file that
receives no inbound links, so the exemption silently suppressed one isolated note per vault,
and did it inconsistently: the same note was still reported by `ZK006`.

`permanent/index.md` is that note. It links out to two notes, receives none, and is listed in
`structure/index.md`. It carries `ZK010` **and** `ZK006`, and both are wanted: the filename
genuinely is not `YYYYMMDDHHMM-slug.md`, and the note is genuinely isolated.

**Mutation:** restoring `note.slug in ("index",)` to the guard makes ZK010 on `index` vanish.

## Trap 1's second consequence — the drift it implies (ZK028)

`202609281005-hand-edited-links.md` cannot carry a body-only target without its Links section
disagreeing with its frontmatter, so `ZK028` fires on it. That is not collateral damage: the
note really is drifted, `ZK028` is `info`, and a reader is told both things about one file.
Recorded here so the finding is not mistaken for noise from the ZK008 trap.

## Files

| File | Purpose | Expected findings |
|---|---|---|
| `permanent/202609281001-question-the-method.md` | Trap 1, frontmatter-and-body form; links to 1002 and 1003; cited by 1002 | `ZK008` · `202609289999-retracted-claim` |
| `permanent/202609281002-ordered-reasons.md` | Retired Trap 2 negative control; 3 sources, long ordered item | None |
| `permanent/202609281003-unmarked-claim.md` | Retired Trap 2 positive control; 3 sources, one unmarked paragraph; links to 1005 | None |
| `permanent/202609281005-hand-edited-links.md` | Trap 1, body-only form; body-only target named twice | `ZK008` · `202609289998-also-missing`; `ZK028` · its own slug |
| `permanent/index.md` | Trap 3; a user's own index, no inbound links | `ZK010` and `ZK006` · `index` |
| `structure/index.md` | Lists all five notes; structure links do not cure isolation | None |
| `SCHEMA.md` | Declares no vocabulary, so `ZK003` is not applicable | None |
| `log.md` | One dated entry; no check counts them any more | None |
| `raw/articles/one.md` | Cited by 1001, 1002, 1003, 1005 and index; digest correct | None |
| `raw/articles/two.md` | Second source for the two provenance notes; digest correct | None |
| `raw/articles/three.md` | Third source for the two provenance notes; digest correct | None |

The three raw files exist so that `202609281002` and `202609281003` each cite three *distinct*
sources — that is what made the retired provenance check applicable to them, and removing the
files now would rewrite the inputs the trap was calibrated against.

## What this fixture does not test

It does not test that `ZK008` and `ZK010` are *capable* of firing on ordinary input — that is
`vault_defects`, which carries each of them in its plain form. What is tested here is the
narrower property the suite could not see: that each check reports its defect the right
*number* of times, on the right notes, after the fixes that changed how they count. A check
that fires on the wrong count fails these traps and passes every other fixture in the corpus.

If a future change makes one of these traps stop being a defect — a `ZK006` that tolerates a
hand-named index, say — the fixture must be changed deliberately, in the same commit as the
reason, rather than deleted quietly.

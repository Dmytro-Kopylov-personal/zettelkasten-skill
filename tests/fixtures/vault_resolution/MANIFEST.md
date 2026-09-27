# vault_resolution — one resolver, measured in both directions

Written by hand before the linter was run against it.

**Expected: 1 finding (`ZK008` on `permanent/202610010901-missing-without-extension.md`),
exit 1, 3 notes, 1 raw source, 6 links.**

## What this fixture is for

v2 replaced four coexisting notions of "does this target exist" with one helper. Three of them
were a literal `(root / target).is_file()`, which meant an extension-less `sources:` entry or
`^[raw/...]` marker **never** resolved — not even when the file it named was sitting right
there. A writer who drops `.md` has named a file that exists, and the old answer was a finding.

The v1 → v2 difference is the only reason this fixture exists, so it is pinned by running both
linters over it rather than by a sentence claiming they differ. **Measured, v1 (`v1.0.3` from
git) against this fixture: 4 findings. v2: 1.** The three that disappear are all the same
defect — `raw/articles/captured` reported missing from the frontmatter twice (`ZK013`) and from
the marker once (`ZK018`) — and the one that remains is a target that is genuinely absent.

| Target | Named in | v1 | v2 |
|---|---|---|---|
| `raw/articles/captured` (no extension; `raw/articles/captured.md` exists) | frontmatter `sources:` **and** body marker | 3 findings (`ZK013` ×2, `ZK018`) | **none** |
| `raw/articles/absent` (no extension; nothing exists either way) | frontmatter `sources:` | 1 finding (`ZK013`) | **1 finding** (`ZK008`) |
| `raw/articles/captured.md` (the ordinary spelling) | frontmatter `sources:` and marker | none | none |

The third row is the control that keeps "resolves more" from quietly becoming "resolves
differently": widening resolution is only safe if the spelling every other fixture already uses
still resolves to the same file.

## Files

| File | Purpose | Expected findings |
|---|---|---|
| `SCHEMA.md` | Declares no vocabulary, so this fixture's report is about references and nothing else | None |
| `log.md` | Two dated entries | None |
| `structure/index.md` | Lists all three notes | None |
| `raw/articles/captured.md` | The file both spellings have to reach; cited by all three notes; digest recorded and correct | None |
| `permanent/202610010900-captured-without-extension.md` | Names `raw/articles/captured` in `sources:` **and** as a body marker — the extension-less form that v1 rejected and v2 resolves | None |
| `permanent/202610010901-missing-without-extension.md` | Names `raw/articles/absent`; its body marker points at the file that does exist, so only the frontmatter half can fire | `ZK008` · `raw/articles/absent` |
| `permanent/202610010902-cited-with-extension.md` | The ordinary spelling, unchanged from every other fixture | None |

Both notes that cite the missing target are otherwise well formed: three notes form a full
cycle, so nothing else has anything to report and the one finding is the whole report. There is
no `raw/articles/absent` and no `raw/articles/absent.md` — the fallback is a search for the
other spelling, not a decision that anything close enough will do.

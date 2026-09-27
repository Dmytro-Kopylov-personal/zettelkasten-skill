# vault_hostile — a file the parser gave up on is not an empty file

Written by hand before the linter was run against it.

**Expected: 8 findings, all `ZK002`, exit 1, 11 notes.**

## The rule this fixture exists to enforce

When frontmatter cannot be parsed, there are two things a linter can do, and one of them is
wrong in a way that is hard to see. It can treat the frontmatter as empty — which is what
Hermes' own skill parser does with its `split(":")` fallback — and then report a fistful of
"missing field" findings that all describe the same broken file, or worse, report nothing at
all because there was nothing left to check. Or it can say **"I could not read this"**, once,
and exclude the file from every check that depends on reading it.

This fixture asserts the second: exactly one `ZK002` per bad file, and nothing else from
that file. If the parser ever started returning an empty mapping on failure, each note here
would produce three to five findings instead of one — the total would jump and the test
would fail loudly.

## The bad files

| File | What is wrong | Expected findings |
|---|---|---|
| `permanent/202609280901-tab-indent.md` | tabs in indentation | `ZK002` · frontmatter |
| `permanent/202609280902-unclosed-quote.md` | a quote that never closes | `ZK002` · frontmatter |
| `permanent/202609280903-block-scalar.md` | `description: \|` — a block scalar | `ZK002` · frontmatter |
| `permanent/202609280904-anchor.md` | `confidence: &medium medium` | `ZK002` · frontmatter |
| `permanent/202609280905-duplicate-key.md` | `status` declared twice | `ZK002` · frontmatter |
| `permanent/202609280906-no-frontmatter.md` | a body with no `---` at all | `ZK002` · frontmatter |
| `permanent/202609280907-byte-order-mark.md` | a UTF-8 BOM before the first `---` | `ZK002` · frontmatter |
| `permanent/202609280909-latin-1.md` | not valid UTF-8 (`café` in latin-1) | `ZK002` · frontmatter |

Each file is named `YYYYMMDDHHMM-slug.md`, so `ZK006` stays quiet: the filename is readable
even when the frontmatter is not, and the fixture must not confuse the two.

## The control, in the other direction

Three notes — `permanent/202609280910-crlf-one.md`, `permanent/202609280911-crlf-two.md` and
`permanent/202609280912-crlf-three.md` — are written with **CRLF line endings** and are
ordinary, valid, linked notes. They must produce nothing.

| File | Purpose | Expected findings |
|---|---|---|
| `permanent/202609280910-crlf-one.md` | A Windows-authored note: parses, links, reports nothing | None |
| `permanent/202609280911-crlf-two.md` | The same, and the cycle closes | None |
| `permanent/202609280912-crlf-three.md` | The same | None |
| `SCHEMA.md` | Declares no vocabulary, so `ZK003` is not applicable | None |
| `log.md` | One dated entry | None |

This is the fixture's most important assertion. CRLF is tolerated by contract ("a Windows-
authored note is still a note"), and there was a real bug here: before `FRONTMATTER_OPEN`
and `FRONTMATTER_CLOSE` learned about `\r`, a CRLF file had no recognisable frontmatter at
all and produced five conformance findings — the exact "loud wrong answer" this file is
about. The three CRLF notes fail the suite if that ever comes back.

Six checks are not applicable: `ZK003` (no vocabulary is declared), `ZK012` (no
`structure/index.md`), `ZK014` and `ZK019` and `ZK026` (there is no `raw/`), and `ZK027` (no
note uses the `contradicts` verb). Everything else runs and reports clean.

## What this fixture does not test

It does not test the *wording* or the *line number* of each parse error. Those are pinned in
`tests/test_yaml_subset.py` (`EXPECTED_ERROR_LINE`), where each construct is also checked
against PyYAML: seven of these constructs are accepted by PyYAML and rejected here on
purpose, and the test asserts that PyYAML really does accept them, so "stricter" cannot
quietly become "broken".

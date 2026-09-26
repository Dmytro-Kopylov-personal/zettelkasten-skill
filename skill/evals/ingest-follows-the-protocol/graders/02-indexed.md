---
type: regex
name: indexed-the-note
target:
  source: file
  path: vault/structure/index.md
pattern: "\\[\\["
match: contains
weight: 1
---

A wikilink in `structure/index.md`. A note that is not indexed is invisible, and the
scaffold's index is empty of examples, so a passing run had to put the entry there itself.
This is why the scaffold does not use `templates/index.md`: that file ships a fenced example
`[[202609261430-attention-budget]]` so a fresh vault lints clean, and a regex cannot tell it
from a real entry.

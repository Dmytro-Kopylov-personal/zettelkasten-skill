---
type: tool_used
name: skill-fired
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?zettelkasten"'
min: 1
weight: 1
arm: with-only
---

The plugin-fired indicator, not a score: under `--ablation with-without` this is excluded
from the score by construction, because the baseline arm has no plugin and could never pass
it. It answers a different question — did *this* skill load and get invoked, or did the run
succeed (or fail) without it ever firing?

`input_match` is load-bearing. Without it this grader passes if *any* skill fires, and this
machine has sixteen. The Skill payload is `{"skill": "<name>"}`, and the optional prefix
covers a plugin-qualified name.

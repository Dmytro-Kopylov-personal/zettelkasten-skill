---
type: regex
name: logged-the-operation
target:
  source: file
  path: vault/log.md
pattern: "^\\s*[-*]\\s*\\d{4}-\\d{2}-\\d{2}"
flags: "m"
match: contains
weight: 1
---

A dated bullet in `log.md`, empty at scaffold time. The log is the operation's only durable
trace — it outlives the context window — so a run that writes notes and leaves the log bare
has not finished the protocol. For the same reason as the index grader, the scaffold writes
this file empty rather than from `templates/log.md`.

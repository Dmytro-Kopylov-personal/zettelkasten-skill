---
type: file_exists
name: no-schema-at-the-cwd-root
path: "SCHEMA.md"
exists: false
weight: 1
---

The negative half. An agent that adopts the directory it is standing in puts `SCHEMA.md`
here — at the top of somebody else's working directory — and every later ingest then edits
files it never created. `file_exists` grades only files the run created, so this passes
exactly when the run did not put one here.

# Log

One line per operation, oldest first. The form is:

```text
- 2026-09-26 14:30 — ingest — raw/articles/example.md → 3 notes created, 1 updated
```

Every entry starts with a date, which is what makes the log orderable and what `ZK022`
checks for. Use the operation name the skill uses — `init`, `ingest`, `query`, `lint` — then
what changed, then anything the next session would want to know: a decision, a source that
contradicted a note, a check that could not run.

Write the log as you go, not at the end of a session. Its value is that it survives the
context window, and a session that ends unexpectedly never gets to write the summary.

Rotate older entries into `log-archive.md` when the file passes a few hundred lines
(`ZK032`), so that the log stays readable rather than merely complete.

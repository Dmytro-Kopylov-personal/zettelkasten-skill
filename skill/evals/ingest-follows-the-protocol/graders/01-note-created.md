---
type: file_exists
name: note-created
path: "vault/permanent/*.md"
exists: true
weight: 1
---

A note exists under `permanent/`. The scaffold creates that directory and nothing inside it,
and `file_exists` grades only files the *run* created — so this cannot pass unless the run
wrote a note. The filename is the agent's to choose, which is why the path is a glob.

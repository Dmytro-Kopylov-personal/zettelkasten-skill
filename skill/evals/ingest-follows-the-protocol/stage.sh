#!/bin/sh
# The vault the case starts from. Runs with cwd = the run's workspace.
#
# Every file here is deliberately empty of examples. `templates/log.md` and
# `templates/index.md` ship a fenced example each — they must, or a fresh vault would fail
# its own linter — and a regex cannot tell a fenced example from a real entry. A grader over
# those templates would pass on a vault nobody had touched, which is the flags-nothing
# failure this repo exists to catch. So the scaffold writes them empty, and the task is to
# add to them.
set -eu

mkdir -p vault/permanent vault/raw/articles vault/raw/papers vault/raw/notes \
         vault/structure vault/inbox

cat > vault/SCHEMA.md <<'SCHEMA'
---
domain: how claims get verified
tags: []
---

# Schema

This vault is about **how claims get verified**.

## The six link verbs

`extends`, `supports`, `contradicts`, `source`, `applies`, `supersedes`.
SCHEMA

printf '# Log\n\nOne line per operation.\n\n' > vault/log.md
printf '# Index\n\nOne line per note.\n\n' > vault/structure/index.md

cat > source.md <<'SOURCE'
# Spacing and the Forgetting Curve

Reviews that are spaced out beat reviews that are massed, even when the total time spent is
identical. The effect is large and it holds across ages and materials. What makes spacing
work is not the passage of time itself but the effort of retrieval after partial forgetting:
the memory has to be reconstructed, and reconstruction is what strengthens it.

This has a cost that is easy to miss. Spacing feels worse while it is happening. Learners
rate massed practice as more effective than spaced practice in the same session where spaced
practice is producing better retention, a dissociation that has been replicated many times.
Fluency during study is therefore a poor guide to learning, and a learner who trusts the
feeling will choose the schedule that works less well.

Retrieval practice is a separate mechanism with a similar profile. Testing yourself is not
only a measurement of what you know; the act of retrieval changes what you will know later.
The two interact: a test is most valuable when it comes after enough forgetting to be hard,
which is the same condition that makes spacing work.
SOURCE

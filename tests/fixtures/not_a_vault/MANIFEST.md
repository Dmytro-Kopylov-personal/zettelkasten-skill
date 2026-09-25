# not_a_vault — "clean" and "not understood" must not look the same

Written by hand before the linter was run against it. This one is a directory, not a vault.

**Expected: 3 findings (ZK001), exit 2, 0 notes.**

## What this fixture is for

The failure this whole tool guards against is a green report from a directory the linter
never understood. A linter pointed at `~/Downloads` finds no notes, so every note-scoped
check finds nothing wrong, and the summary is "0 findings" — a report that is *true* and
completely misleading. So:

- each of the three required paths is named by its own `ZK001`: `permanent`, `SCHEMA.md`,
  `log.md`;
- the exit code is **2**, and it is 2 at every `--fail-on` threshold, including `info`. No
  setting makes this vault pass;
- well-formed JSON is still written to stdout, so a CI job can tell "this is not a vault"
  from "this vault has findings". Exit 2 with nothing on stdout would be indistinguishable
  from a crash;
- the human summary says out loud what the code means, on stderr, so it cannot be confused
  with a finding.

## Thirty checks are not applicable

With no notes, no raw sources, no log and no inbox, thirty checks are reported as not
applicable — twenty-two of them because "the vault has no permanent notes". That is the
same emptiness as the `ZK001`s, reported once per check.

It is worth being explicit that this is *true and not enough*: the not-applicable list is
long, and a reader skimming a report could take its length as a sign that something ran. The
exit code is the part that cannot be skimmed, which is why the fixture pins it at 2 rather
than at 0 or 1.

## Files

| File | Purpose | Expected findings |
|---|---|---|
| `README.md` | A file, so the directory is not empty — and not a note, so it produces nothing | None |

The three `ZK001` findings have `file: ""`, because the file that is missing is the vault
root itself. Their subjects are the paths: `permanent`, `SCHEMA.md`, `log.md`.

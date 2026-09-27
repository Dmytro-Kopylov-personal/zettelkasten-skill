# Architecture

How this repo is shaped, and where the three platforms pull apart. The *reasons* — and the
platform code that was executed to find them — are in `design.md`; this file is the map.

## One body, three renders

The skill is written once in capability language and assembled three times. Nothing in the
shared body knows which platform it will run on.

```mermaid
flowchart TD
  T["src/SKILL.template.md<br/>shared body — capability language<br/>exactly two seams"]

  FH["frontmatter.hermes.yaml<br/>version · author · platforms"]
  FC["frontmatter.claude.yaml<br/>version nested under metadata"]
  FP["frontmatter.copilot.yaml<br/>name · description"]

  EH["environment.hermes.md<br/>names read_file · search_files · terminal"]
  EC["environment.claude.md<br/>names Read · Glob · Grep · Bash"]
  EP["environment.copilot.md<br/>names no tools at all"]

  R["src/render.py<br/>compose, then validate<br/>an unloadable render is never deployed"]

  T --> R
  FH --> R
  FC --> R
  FP --> R
  EH --> R
  EC --> R
  EP --> R

  R --> GH["tests/golden/hermes.SKILL.md"]
  R --> GC["tests/golden/claude.SKILL.md"]
  R --> GP["tests/golden/copilot.SKILL.md"]

  GH --> IH["~/.hermes/skills/research/zettelkasten/"]
  GC --> IC["~/.claude/skills/zettelkasten/<br/>or installed as a Claude Code plugin"]
  GP --> IP["~/.copilot/skills/zettelkasten/<br/>or PROJECT/.github/skills/zettelkasten/"]
```

The two seams are `{{FRONTMATTER}}` and `{{ENVIRONMENT}}`. An unfilled placeholder is a render
error rather than a truncated file, which is why the body can never ship half-assembled.

`tests/golden/` holds the three renders. They are the reviewable artifact *and* the oracle
`make check` diffs against, so the thing you read and the thing CI compares are the same bytes.

## Where the three contracts diverge

Every render must clear the same bar first: a `name` matching the kebab pattern and ≤64 chars, a
non-empty `description` ≤1024 chars, and a non-empty body. After that the rules are per-platform,
and each one exists because a platform's own code does something.

```mermaid
flowchart TD
  S["Shared bar — all three renders<br/>name · description ≤1024 chars · non-empty body"]

  S --> H["Hermes"]
  S --> C["Claude Code"]
  S --> P["Copilot"]

  H --> H1["must declare platforms<br/>values must be OS names"]
  H --> H2["the catalog shows description only<br/>up to 57 characters then an ellipsis"]

  C --> C1["no key outside Anthropic's allowlist"]
  C --> C2["description: no angle brackets"]

  P --> P1["name must equal the directory name"]
  P --> P2["body ≤500 lines"]
  P --> P3["description: no angle brackets"]

  H1 --> WHY1["it is an OS gate, not an agent gate —<br/>copilot in that list hides the skill entirely"]
  H2 --> WHY2["trigger verbs sit inside the first 53 chars"]
  C1 --> WHY3["the allowlist is name, description, license,<br/>allowed-tools, metadata, compatibility"]
  P1 --> WHY4["the directory is what Copilot resolves"]
```

Three divergences are worth naming, because each is a silent failure rather than a loud one:

**The same version, written three ways.** Hermes takes `version:` at the top level. Claude's
allowlist has no `version` key at all, so it moves under `metadata:`. Copilot declares none.
Nothing validates that these agree — the tag, `plugin.json` and the Hermes fragment are three
separate declarations of one number.

**Hermes truncates the description to 57 characters.** That truncated string is the entire
discovery surface: a skill whose trigger verbs fall past it is present but unfindable. The
render is asserted to keep `ingest`, `query`, `lint`, `init` and `zettelkasten` inside the first
53.

**Copilot resolves the skill by directory name**, so `name:` must equal `zettelkasten`, and the
body is capped at 500 lines on third-party guidance. VS Code documents no limit; the cap is kept
because exceeding it is a real load failure in the wild.

## What ships, and what only looks like it ships

```mermaid
flowchart LR
  subgraph SRC["src/ — never shipped"]
    T["SKILL.template.md<br/>fragments<br/>render.py"]
  end

  subgraph TESTS["tests/ — never shipped"]
    FX["fixtures/<br/>each with a hand-written MANIFEST"]
    GD["golden/<br/>the three renders"]
    SU["the suite"]
  end

  subgraph SHIPPED["skill/ — the payload"]
    SK["SKILL.md"]
    RF["references/<br/>4 files, loaded on demand"]
    TP["templates/<br/>5 files, copied by init"]
    SC["scripts/zettel_lint.py<br/>stdlib only · read-only"]
  end

  T -->|render| GD
  T -->|render| SK
  GD -->|byte-compare| SK
  SK --> RF
  SK --> TP
  SK --> SC
```

`install.sh` copies `SKILL.md`, `references/`, `templates/` and `scripts/` and nothing else. The
sources that produced them stay behind.

`skill/SKILL.md` exists because a plugin must ship a loadable `SKILL.md`, and a gitignored one
installs as zero skills. It is the Claude render, and `test_golden.py` asserts it byte-identical
to `tests/golden/claude.SKILL.md` — so the copy is for the loader, and the golden is still the
single source of truth. The guarantee moved from absence to a test.

## What a vault is

The artifact, before the loop that maintains it. `init` creates all of this in one folder, and
nothing else belongs in that folder: the vault root is the boundary of every write.

```mermaid
flowchart TD
  subgraph VAULT["a vault — one folder, nothing else"]
    SCHEMA["SCHEMA.md<br/>the vault's own rules:<br/>domain · tags · verbs · thresholds"]
    PERM["permanent/<br/>one atomic idea per note<br/>id-slug.md"]
    RAW["raw/articles · raw/papers · raw/notes<br/>captures — immutable, sha256 recorded"]
    INBOX["inbox/<br/>material not yet processed"]
    STRUCT["structure/<br/>index · concept-table · overview"]
    LOG["log.md<br/>one line per operation"]
  end

  RAW -->|ingest| PERM
  INBOX -->|"ingest, or delete<br/>and say why"| RAW
  PERM -->|summarised by| STRUCT
  PERM -->|"every change<br/>is a line in"| LOG
  LOG -.->|"past 500 entries"| ARCH["log-archive.md"]
```

Three of those paths carry more weight than their contents: **`permanent/`, `SCHEMA.md` and `log.md`
are what make a folder a vault.** Resolution walks upward looking for all three together, and
`ZK001` names exactly these three when one is missing — a folder without them is reported as *not a
vault* and exits 2, rather than being linted as an empty vault and reported clean. That distinction
is the one the `not_a_vault` fixture exists to hold.

`log-archive.md` is the only path not there at the start. It appears when the log passes
`lint_log_rotation_entries`, because a log that only grows stops being readable and an unread log is
not a history. `SCHEMA.md` is the other file worth opening first: the linter carries a default for
every threshold, and a vault's own `SCHEMA.md` overrides them for that vault alone, which is how one
linter judges two vaults held to different standards.

## How it holds together at run time

The load-bearing separation: **the script verifies, the agent writes.** Nothing in `scripts/`
opens a file for writing, which is proven by a tree hash taken before and after a full lint run.

```mermaid
flowchart TD
  U["a source arrives"] --> A["the agent<br/>proposes before it writes"]

  A -->|"capture, once"| RAW["raw/<br/>immutable after capture<br/>sha256 recorded"]
  A -->|writes| PERM["permanent/<br/>one note per atomic idea"]
  A -->|writes| STRUCT["structure/<br/>index · concept table · overview"]
  A -->|writes| LOG["log.md"]

  subgraph VAULT["the vault"]
    RAW
    PERM
    STRUCT
    LOG
  end

  L["zettel_lint.py<br/>read-only"]
  VAULT --> L
  L -->|"JSON findings,<br/>plus what could not run"| A
```

The loop is deliberately one-directional. The linter reads the vault and reports; it has no
`--fix` and no write path at all. A fix mode would be a second write path around ingest's
propose-then-approve contract, and the findings most worth acting on — which verb, one idea or
two — are the ones no script can decide.

Two properties of that loop are structural rather than conventional. `raw/` is never written
after capture, so hash drift is remedied by re-ingesting, never by editing the digest. And the
report carries `parse_failures[]` and `skipped_checks[]` as mandatory fields, so a check that
could not run says so instead of quietly becoming a clean result.

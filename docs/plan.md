# Plan

The phase gates, and the evidence each one has to produce. A phase is done when its gate
is met by something measured, not by something written.

| Phase | Work | Gate — done means | Evidence |
|---|---|---|---|
| **P0** Scaffold | `git init`, README/LICENSE/.gitignore/Makefile, commit-msg hook, private GitHub repo, vault project doc + catalog entry | the hook demonstrably rejects an AI co-author trailer | repo URL, hook output |
| **P1** Render | template body, 6 fragments, `render.py`, goldens, render/invariant tests | three goldens byte-identical twice; denylist passes **with both controls**; shared-body invariant green; `--check` exits 0 | char/line counts vs budgets, control results |
| **P2** Parser | `zettel_lint.py` core: YAML subset parser, byte-exact frontmatter split, `Vault` model, wikilink + provenance-marker extraction, `hash` | parser matches `yaml.safe_load` on every fixture block; each unsupported construct raises with the right line; wikilink extraction returns `[]` on all four V3 traps | differential pass count |
| **P3** Checks | 32 checks, `references/lint-checks.md` 1:1, JSON/text contract, `--fail-on`, `--baseline`, exit codes, all fixtures + MANIFESTs | `vault_defects` matches its manifest in both directions; every expected finding is attributable to its own check by silencing it; `vault_trap` == 1 finding; `vault_clean` == 0; `vault_hostile` == the exact `ZK002` set; `not_a_vault` exits 2; every `doc` anchor resolves; determinism + read-only proofs green | per-fixture counts, baseline round-trip |
| **P4** Install + init | `install.sh` (5-case manifest, `--dry-run`, platform detection), `templates/`, the three remaining references, init protocol | install twice byte-identical; all five cases pass; an init'd vault lints clean; the body names only references that ship | tree-hash proof, case results |
| **P5** Hermes | install, `hermes curator pin zettelkasten`, fresh-session visibility, N=3 scripted ingest | `hermes skills list` shows it; the catalog line is not truncated mid-trigger; pass rate recorded | install log, list output, pin confirmation, N=3 results |
| **P6** Claude | `quick_validate.py`, `claude plugin validate --strict`, `/skills`, eval with an ablation | both validators exit 0; discovered; the `allowed-tools` decision recorded as verified or deferred | validator output, discovery + eval evidence |
| **P7** Copilot | install to `~/.copilot/skills/` and, via `--project-root`, to a work repo; verify with `/skills list`; write the manual VS Code procedure | CLI-side discovery confirmed; every locally checkable rule passes; VS Code and cloud-agent behaviour ship explicitly **unverified** | CLI output, the procedure, the unverified markers |
| **P8** Calibration | run against a real vault; measure `ZK024` and `ZK023` false-positive rates on hand-labelled samples, `ZK029` verb distribution, notes-per-source drift | numbers recorded; severities promoted only where the measurement supports it | the numbers, and the decision each drove |

Order follows the spec: Hermes first (clearer debugging output), then Claude (free, same
machine), then Copilot — which cannot be verified here beyond its CLI.

The check count was an estimate when the three tiers were sketched; the registry settled at
**32** codes (`ZK001`–`ZK032`), 15 `error` / 7 `warn` / 10 `info`, each documented 1:1 in
`skill/references/lint-checks.md` and exercised by at least one fixture.

## Decisions taken

| Fork | Decision |
|---|---|
| Home | Standalone private repo; `install.sh` copies into platform dirs. The repo is canonical, not the installed copy — otherwise the weekly one-way `rsync --delete` backup buries skill history under backup commits. |
| Linter | `scripts/zettel_lint.py` — stdlib only, single file, no venv, no pip, read-only. Prompt-only fallback documented for machines that cannot run scripts. |
| Operations | Four: `init`, `ingest`, `query`, `lint`. `init` resolves the specification's ambiguity about where `SCHEMA.md` lives by shipping `templates/SCHEMA.md` and materialising a per-vault copy. |
| Tool names | Never in the shared body; assembled per platform at install time. Enforced mechanically. |

## Risks

- **The agent can ignore the protocol.** Not fully mitigable; P5's pass rate is the only
  honest evidence, and lint makes post-hoc drift detectable.
- **Adoption makes CI red at birth** — `ZK010`/`ZK011` fail on every note by construction.
  Fixed with `--baseline`, never by weakening a predicate; suppressed findings are counted,
  not hidden.
- **Six link verbs may be too rigid.** The predicted failure is collapse to `supports`;
  `ZK029` detects it, and the response is to merge verbs in `SCHEMA.md`, recorded with the
  measurement that drove it.
- **The Page Threshold is not lint-checkable** (the agent applies it), so it can drift
  silently. Proxy: notes-per-source over time; a ratio far above 1.0 is threshold drift.
- **`ZK024` will make noise.** Claimed: aggregated to one finding per note, opt-out-able,
  `info`-tier, measured before promotion — not that it is quiet.

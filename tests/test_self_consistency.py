"""The vault the skill scaffolds, checked by the linter that ships beside it.

`init` produces a vault out of `skill/templates/`; the linter then judges that vault. If the
two ever disagree, the skill's first act is to build something its own tool calls broken —
and the user, having just been handed a fresh vault, is told to fix it. So the two are
closed into a loop here: materialise the templates exactly as the Init section describes,
run the real `lint_vault` over the result, and require zero findings and exit 0.

The loop has three sides, and all three are asserted, because any pair can agree while the
third drifts:

- the **body** names five templates,
- `skill/templates/` holds exactly those five files,
- and a vault built from them lints clean.

Two things are deliberately *not* asserted, because they are agent behaviour rather than
template content: the domain sentence the user supplies (init step 4), and the first log
entry (step 6). Both are performed below the way the protocol describes, so the lint that
follows is a lint of a realistic vault — but the assertions are about the templates, which
are the part that ships.
"""

from __future__ import annotations

import datetime as dt
import re
import sys

import pytest
from conftest import REPO

sys.path.insert(0, str(REPO / "skill" / "scripts"))
import zettel_lint  # noqa: E402

TEMPLATES = REPO / "skill" / "templates"
BODY = REPO / "src" / "SKILL.template.md"

#: Where each template is materialised, exactly as the Init section of the body lists it.
#: Destination is the key: two templates must not be able to claim one path.
PROTOCOL = {
    "SCHEMA.md": "SCHEMA.md",
    "index.md": "structure/index.md",
    "concept-table.md": "structure/concept-table.md",
    "overview.md": "structure/overview.md",
    "log.md": "log.md",
}

RAW_DIRS = ("raw/articles", "raw/papers", "raw/notes")
VAULT_DIRS = (*RAW_DIRS, "permanent", "structure", "inbox")

#: Init step 1: the vault gets its own folder rather than taking over the directory it runs in.
#: This is the containment property — the vault root is the only place the skill writes, so
#: whatever else shares that folder shares the blast radius.
VAULT_DIRNAME = "zettelkasten"

NOW = dt.date(2026, 9, 26)


def init(parent, *, domain: str = "how notes compound", stamp: str = "2026-09-26 14:30"):
    """The Init section, performed. Step 1 is the folder, 2-3 the templates, 4 and 6 the agent's."""
    root = parent / VAULT_DIRNAME
    for name in VAULT_DIRS:
        (root / name).mkdir(parents=True, exist_ok=True)

    for source, destination in PROTOCOL.items():
        target = root / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((TEMPLATES / source).read_bytes())

    # Step 4: the domain goes into SCHEMA.md, replacing the placeholder.
    schema = root / "SCHEMA.md"
    text = schema.read_text(encoding="utf-8")
    assert "domain: unset" in text, "the template no longer has a domain placeholder to fill"
    text = text.replace("domain: unset", f"domain: {domain}", 1)
    text = text.replace(
        "This vault is about **a domain nobody has filled in yet**. Replace this paragraph with one\n"
        "sentence naming the subject: a vault without a domain accumulates everything and links\n"
        "nothing, and the sentence is what an ingest turns to when it has to decide whether a source\n"
        "belongs.",
        f"This vault is about **{domain}**.",
        1,
    )
    schema.write_text(text, encoding="utf-8")

    # Step 6: the init is logged, in the form the log template documents.
    log = root / "log.md"
    with log.open("a", encoding="utf-8") as handle:
        handle.write(f"\n- {stamp} — init — created the vault\n")
    return root


@pytest.fixture()
def vault(tmp_path):
    return init(tmp_path)


def lint(root):
    return zettel_lint.lint_vault(root, NOW, set(), zettel_lint.ERROR)


# --- the three sides of the loop -------------------------------------------------------


def test_the_body_names_exactly_the_templates_that_ship():
    """A template the body never mentions is dead weight; one it mentions and we lack is a
    broken instruction the agent cannot follow."""
    body = BODY.read_text(encoding="utf-8")
    named = set(re.findall(r"templates/([A-Za-z-]+\.md)", body))
    assert named == set(PROTOCOL), f"the body names {sorted(named)}"


def test_every_template_the_protocol_materialises_exists_and_no_others_do():
    present = {path.name for path in TEMPLATES.glob("*.md")}
    assert present == set(PROTOCOL), f"templates dir holds {sorted(present)}"


def test_every_destination_is_distinct():
    """Two templates claiming one path would silently drop one of them at init."""
    assert len(set(PROTOCOL.values())) == len(PROTOCOL)


def test_a_freshly_initialised_vault_lints_clean(vault):
    """The gate: the skill's first act must not produce something its own tool rejects."""
    document, code = lint(vault)
    assert document["findings"] == [], "\n".join(
        f"{finding['code']} {finding['file']}: {finding['message']}"
        for finding in document["findings"]
    )
    assert code == 0
    assert document["parse_failures"] == []


def test_the_fresh_vault_is_clean_because_checks_ran_not_because_they_could_not(vault):
    """Zero findings has two very different meanings. The scaffold must produce the first:
    the checks that have something to read read it and found nothing."""
    document, _ = lint(vault)
    skipped = {entry["code"] for entry in document["skipped_checks"]}
    # These had input and passed on it.
    assert not {"ZK001", "ZK012", "ZK022"} & skipped
    # These had none, and say so rather than reporting a pass — every check whose subject is
    # a note, because the vault has none yet, and every check whose subject is a capture,
    # because a new vault has no `raw/` either. That every code is in one table or the other
    # is asserted in `test_lint_checks.py`; here it is the two sets, exactly.
    assert skipped == zettel_lint.NOTE_SCOPED | zettel_lint.RAW_SCOPED
    assert document["summary"]["metrics"]["notes"] == 0


def test_the_index_is_checked_even_though_it_is_empty(vault):
    """The scaffold's index holds a *fenced example* of the entry format. If the wikilink
    extractor ever stopped stripping code fences, that example would be read as a real entry
    and this vault would be born with a dangling link — which is the whole reason the V3
    trap exists. Empty index, one example, zero findings."""
    text = (vault / "structure" / "index.md").read_text(encoding="utf-8")
    assert "```" in text and "[[" in text, "the index template no longer shows an example"
    document, _ = lint(vault)
    assert not [f for f in document["findings"] if f["file"] == "structure/index.md"]


def test_the_log_example_is_not_read_as_an_undated_entry(vault):
    """The log template shows its format in a fence, and ZK022 reads every bullet line —
    fenced or not. The example carries a real date for that reason; if it ever loses one,
    every vault is born with a warning."""
    text = (vault / "log.md").read_text(encoding="utf-8")
    assert re.search(r"^```", text, flags=re.MULTILINE)
    document, _ = lint(vault)
    assert not [f for f in document["findings"] if f["code"] == "ZK022"]


def test_the_vault_gets_its_own_folder_and_leaves_nothing_beside_it(tmp_path):
    """Init step 1 — the containment property, asserted rather than described.

    The vault root is the only place this skill writes, so a vault sharing its directory with
    other files puts those files inside the blast radius. The scaffold must therefore *create*
    a folder rather than adopt the one it was run in.
    """
    root = init(tmp_path)
    assert root == tmp_path / VAULT_DIRNAME
    assert {path.name for path in tmp_path.iterdir()} == {VAULT_DIRNAME}


def test_the_body_states_the_write_boundary_in_both_places():
    """The pitfall says what not to do; the checklist asks whether it was done. A boundary
    stated in only one of them is the sort of rule that quietly stops being followed."""
    body = BODY.read_text(encoding="utf-8")
    assert "**Writing outside the vault root.**" in body
    assert "- [ ] Nothing outside the vault root was created, modified or deleted" in body
    assert "it gets its own folder rather than taking over the one you are" in body


def test_the_domain_the_user_gives_reaches_the_schema(vault):
    """Step 4 is the one init step whose effect is invisible to lint — nothing checks that a
    domain is set. So it is asserted here instead, by name, since nothing else will."""
    assert "domain: how notes compound" in (vault / "SCHEMA.md").read_text(encoding="utf-8")
    assert "a domain nobody has filled in yet" not in (vault / "SCHEMA.md").read_text(
        encoding="utf-8"
    )


# --- the scaffold is a starting point, not a state to stay in --------------------------


def test_a_note_written_into_the_fresh_vault_is_the_first_thing_that_goes_wrong(vault):
    """A control in the honest direction: the scaffold lints clean, and it must stop
    linting clean the moment there is a note that is not linked, indexed or sourced. If
    this ever passes, the clean result above came from the checks not firing at all."""
    (vault / "permanent" / "202609261500-an-unlinked-thought.md").write_text(
        "---\n"
        "id: 202609261500\n"
        "title: An unlinked thought\n"
        "type: permanent\n"
        "status: seed\n"
        "created: 2026-09-26\n"
        "---\n"
        "\nSomething nobody can reach.\n",
        encoding="utf-8",
    )
    document, code = lint(vault)
    assert code == 1
    assert {finding["code"] for finding in document["findings"]} >= {"ZK010", "ZK012"}


def test_the_scaffold_survives_its_own_round_trip_through_the_reader(vault):
    """The templates are read by the agent, so they are read here too: every one of them
    must exist, be non-empty, and be valid UTF-8. A template that cannot be read is a
    template that will be silently skipped at init."""
    for name in PROTOCOL:
        raw = (TEMPLATES / name).read_bytes()
        assert raw.strip(), f"{name} is empty"
        assert raw.decode("utf-8").strip(), f"{name} is not valid UTF-8"


def test_no_template_carries_a_placeholder_left_from_another_template():
    """Cheap, and it catches the copy-paste that would put a note skeleton in the index."""
    for name in PROTOCOL:
        text = (TEMPLATES / name).read_text(encoding="utf-8")
        assert "{{" not in text, f"{name}: an unrendered placeholder"
        assert "TODO" not in text, f"{name}: a TODO the agent would have to guess at"

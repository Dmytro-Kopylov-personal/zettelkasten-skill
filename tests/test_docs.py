"""The reference the findings point at, checked against the linter that points.

Every finding carries `doc: references/lint-checks.md#zkNNN`. That string is a promise: a
reader who wants to know what `ZK024` means, and what to do about it, can go straight there.
A promise that resolves to a missing anchor, or to an entry describing a different rule than
the one that fired, is worse than no link at all — it is a confident wrong answer, which is
the failure mode this whole repo is built around.

So the anchors are asserted against the *emitter*, not against a second copy of the format
string: each code is run through `Finding.as_dict()` — the code path that really produces the
`doc` field — and the resulting string must resolve to a section here. A rename of the emitter
breaks this test instead of silently producing dead links.

The labels are checked too. An entry is only useful if it says what fires, what to do, and how
to find the same thing without scripts; `**Fires when**`, `**Fix:**` and `**By hand:**` are
what make the file a reference rather than a list of codes.
"""

from __future__ import annotations

import pathlib
import re
import sys
import tempfile

import pytest
from conftest import REPO

sys.path.insert(0, str(REPO / "skill" / "scripts"))
import zettel_lint  # noqa: E402

REFERENCE = REPO / "skill" / "references" / "lint-checks.md"
SCHEMA_REFERENCE = REPO / "skill" / "references" / "schema-reference.md"
TEMPLATE_SCHEMA = REPO / "skill" / "templates" / "SCHEMA.md"
ANCHOR = re.compile(r'^<a id="(?P<anchor>[a-z0-9-]+)"></a>\s*$', flags=re.MULTILINE)

ENTRY_LABELS = ("**Fires when**", "**Fix:**", "**By hand:**")


def text() -> str:
    return REFERENCE.read_text(encoding="utf-8")


def anchors() -> dict[str, str]:
    """anchor -> the section that follows it, up to the next anchor."""
    document = text()
    found = {}
    matches = list(ANCHOR.finditer(document))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(document)
        found[match.group("anchor")] = document[match.end() : end]
    return found


def resolve(doc: str) -> str | None:
    """The section a `doc` string points at, or None. Raises on a foreign document."""
    path, _, anchor = doc.partition("#")
    assert path == "references/lint-checks.md", f"a finding points at {path}"
    return anchors().get(anchor)


def emitted_doc(code: str) -> str:
    """The `doc` string the linter really emits for a code — through the emitter itself."""
    finding = zettel_lint.Finding(
        code=code,
        severity=zettel_lint.SEVERITIES[code],
        file="permanent/202609261430-example.md",
        subject="example",
        message="the message is not part of the anchor",
    )
    return finding.as_dict()["doc"]


# --- the file and its anchors ---------------------------------------------------------


def test_the_reference_exists():
    assert REFERENCE.is_file(), "findings point at a file that does not exist"
    assert text().strip(), "the reference is empty"


def test_every_code_the_linter_can_report_has_a_section():
    documented = set(anchors())
    expected = {emitted_doc(code).rpartition("#")[2] for code in zettel_lint.SEVERITIES}
    assert documented == expected, (
        f"undocumented: {sorted(expected - documented)} · "
        f"documented but not a code: {sorted(documented - expected)}"
    )


def test_there_are_exactly_as_many_sections_as_codes():
    """Belt and braces with the set comparison above: a duplicate anchor with a missing
    section would still produce the right *set* while leaving a code undocumented."""
    assert len(anchors()) == len(zettel_lint.SEVERITIES) == 15


@pytest.mark.parametrize("code", sorted(zettel_lint.SEVERITIES))
def test_the_emitted_doc_string_resolves(code):
    """The closed loop: the bytes the linter puts in `doc` must land on the section."""
    section = resolve(emitted_doc(code))
    assert section is not None, f"{code}: {emitted_doc(code)} resolves to nothing"
    heading = section.strip().splitlines()[0]
    assert code in heading, f"{code}: the section it resolves to is headed {heading!r}"


@pytest.mark.parametrize("code", sorted(zettel_lint.SEVERITIES))
def test_the_documented_severity_matches_the_linter(code):
    """Severity is the part people act on — `info` can be ignored, `error` cannot. A doc
    that says `warn` for a code the registry fails the build on is a trap."""
    expected = zettel_lint.SEVERITIES[code]
    section = anchors()[code.lower()]
    match = re.search(r"^\*\*Severity:\*\*\s*(\w+)", section, flags=re.MULTILINE)
    assert match, f"{code}: no severity line, so its tier is undocumented"
    assert match.group(1) == expected, f"{code}: the doc says {match.group(1)}, the registry {expected}"


@pytest.mark.parametrize("code", sorted(zettel_lint.SEVERITIES))
def test_every_entry_says_what_fires_what_to_do_and_how_to_check_by_hand(code):
    section = anchors()[code.lower()]
    missing = [label for label in ENTRY_LABELS if label not in section]
    assert not missing, f"{code}: missing {missing}"


# --- controls -------------------------------------------------------------------------


def test_the_resolver_would_notice_a_dead_anchor():
    """Control: `resolve` must be able to return None, or every test above is vacuous."""
    assert resolve("references/lint-checks.md#zk999") is None
    assert resolve("references/lint-checks.md#zk03") is None, (
        "an anchor that is a prefix of a real one must not match it"
    )
    assert resolve(emitted_doc("ZK001")) is not None


def test_the_anchor_pattern_finds_the_anchors_at_all():
    """Control for the extractor, which is the one thing this module cannot check by
    comparing two sources: if it silently matched nothing, the set comparison would fail —
    but this names the reason."""
    assert len(anchors()) > 0
    assert ANCHOR.findall('<a id="zk003"></a>') == ["zk003"]
    assert ANCHOR.findall("### ZK003 — a heading is not an anchor") == []


def test_the_labels_are_checked_as_labels():
    """Control: the label list is what the entry test keys on, so it must not be empty or
    trivially satisfiable by a substring of the file as a whole."""
    assert all(label.startswith("**") and label.endswith(("**", ":**")) for label in ENTRY_LABELS)
    assert len(set(ENTRY_LABELS)) == len(ENTRY_LABELS)


# --- the other references the shipped body promises -----------------------------------


def references() -> set[str]:
    return {path.name for path in (REPO / "skill" / "references").glob("*.md")}


def test_the_body_points_at_references_that_ship():
    """A reference the body names and we do not ship is an instruction the agent cannot
    follow, discovered at the moment it is following it."""
    body = (REPO / "src" / "SKILL.template.md").read_text(encoding="utf-8")
    named = set(re.findall(r"references/([A-Za-z-]+\.md)", body))
    assert named <= references(), f"the body names {sorted(named - references())}"


def test_no_reference_ships_unlinked():
    """The other direction: a file nothing names is a file the agent will never open."""
    body = (REPO / "src" / "SKILL.template.md").read_text(encoding="utf-8")
    named = set(re.findall(r"references/([A-Za-z-]+\.md)", body))
    linked_elsewhere = set()
    for path in (REPO / "skill" / "references").glob("*.md"):
        if path.name == "lint-checks.md":
            continue
        linked_elsewhere |= set(
            re.findall(r"references/([A-Za-z-]+\.md)", path.read_text(encoding="utf-8"))
        )
    orphaned = references() - named - linked_elsewhere
    assert not orphaned, f"nothing points at {sorted(orphaned)}"


# --- the declaration, which is written down in three places ---------------------------


DIMENSION_ROW = re.compile(r"^\|\s*`(?P<key>[a-z_]+)`\s*\|", re.M)


def documented_dimensions() -> set[str]:
    """The six dimension names, as the reference's own table lists them."""
    return {match.group("key") for match in DIMENSION_ROW.finditer(SCHEMA_REFERENCE.read_text("utf-8"))}


def templated_declaration() -> dict[str, list[str]]:
    """The declaration the scaffold writes, read by the linter's own parser.

    Deliberately not a regex over the template. The template becomes a vault's `SCHEMA.md`,
    and the only question that matters is whether the linter reads a declaration out of it —
    a regex would agree with itself while the parser found nothing, which is the failure the
    control below exists to name.
    """
    with tempfile.TemporaryDirectory() as directory:
        root = pathlib.Path(directory)
        (root / "SCHEMA.md").write_bytes(TEMPLATE_SCHEMA.read_bytes())
        return zettel_lint.read_declaration(root)


def test_the_scaffold_ships_a_declaration_the_linter_can_read():
    """Init copies this file into a new vault, so it is the first thing `ZK003` ever reads.

    A misspelled dimension name would leave the new vault with that dimension silently
    unchecked, and nothing in the report would say so — it would simply be about four
    dimensions instead of five. `tags` is deliberately not among them; the test below says
    why.
    """
    declared = templated_declaration()
    assert set(declared) == set(zettel_lint.VOCABULARY_DIMENSIONS) - {"tags"}, (
        f"the template declares {sorted(declared)}"
    )
    assert all(declared.values()), declared


def test_the_templates_empty_tag_list_is_the_absence_of_a_declaration():
    """`tags: []` in the scaffold is not the claim that no tags are legal.

    The scaffold cannot know what a vault is about — its domain is literally `unset` — so it
    must not invent a taxonomy. An empty list is how a dimension goes undeclared, and the
    whole point of the v2 rule is that undeclared means unjudged rather than wrong.
    """
    assert "tags" not in templated_declaration()
    assert "tags: []" in TEMPLATE_SCHEMA.read_text("utf-8")


def test_every_dimension_the_linter_reads_is_documented_and_none_are_invented():
    """The linter reads six names; the reference must name those six and no others.

    This is what replaced the old three-way threshold check. The property is the same —
    the rule a vault is judged by must be the rule its own documentation describes — but it
    is now about which dimensions exist rather than which numbers they default to.
    """
    assert documented_dimensions() == set(zettel_lint.VOCABULARY_DIMENSIONS)


def test_the_dimension_parsers_would_notice_a_missing_row():
    """Control: a pattern that matched nothing would make the comparison above pass with
    two empty sets on both sides."""
    assert len(documented_dimensions()) == 6
    assert len(templated_declaration()) == 5


# --- the limits that are recorded rather than silently omitted ------------------------

DROPPED = {
    "semantic duplicates": "needs embeddings",
    "contradictory tags": "not deterministic",
    '"the note is stale relative to its newest source"': "ill-defined",
    "one sentence": "meaningless",
}


def test_the_checks_that_were_dropped_are_written_down_with_their_reasons():
    """The spec's ambiguity is that a missing check and a forgotten check look alike. This
    file has a table for the difference, and the table must stay honest about what it
    says — each of the four dropped checks names *why* it was dropped, not just that it was.
    """
    document = text()
    assert "Deliberately not checked" in document
    for name, reason in DROPPED.items():
        assert name in document, f"{name} was dropped without being recorded"
        section = document.split("Deliberately not checked", 1)[1]
        assert reason in section, f"{name} is listed without its reason ({reason})"

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

import re
import sys

import pytest
from conftest import REPO

sys.path.insert(0, str(REPO / "skill" / "scripts"))
import zettel_lint  # noqa: E402

REFERENCE = REPO / "skill" / "references" / "lint-checks.md"
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
    assert len(anchors()) == len(zettel_lint.SEVERITIES) == 32


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

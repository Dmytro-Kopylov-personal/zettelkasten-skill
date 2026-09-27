"""The known-answer calibration of the check layer, in both directions.

Each fixture under `tests/fixtures/` ships a `MANIFEST.md` written by hand *before* the
linter was run against it, and an `expected.json` holding the same claims in machine form.
This module asserts equality between what the manifest says and what the linter reports —
the full finding set, the metrics, the not-applicable list and the exit code at each
threshold. A fixture with an unlisted defect fails, and so does a finding nobody predicted:
a screen that flags everything and one that flags nothing must not both look green.

The strongest test here is `test_each_expected_finding_comes_from_its_own_check`. Matching a
manifest proves the linter reports what was predicted; it does not prove *which check*
reported it. So each check is removed from the registry in turn and the report must lose
exactly the findings attributed to it — which is what stops a neighbour that happens to fire
on the same file from silently covering for a check that does nothing.

Time is pinned (`NOW`) rather than read from the system clock. Decay checks age notes
against today's date, so a fixture with dates in it is a time bomb otherwise: it passes
today and fails in three months for a reason that has nothing to do with the code.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from collections import Counter

import pytest
from conftest import FIXTURES, REPO

sys.path.insert(0, str(REPO / "skill" / "scripts"))
import zettel_lint  # noqa: E402

#: Every fixture's dates sit within a few days of this. No check reads the clock in v2 —
#: that is asserted in `test_lint_contract.py` by linting the same vault at two dates — so
#: pinning it here is about making the report's own `now` field stable, not the findings.
NOW = dt.date(2026, 9, 28)

FIXTURE_NAMES = [
    "vault_clean",
    "vault_nested",
    "vault_defects",
    "vault_minimal",
    "vault_trap",
    "vault_hostile",
    "vault_regressions",
    "vault_foreign",
    "vault_resolution",
    "not_a_vault",
]


def expectation(name: str) -> dict:
    return json.loads((FIXTURES / name / "expected.json").read_text(encoding="utf-8"))


def lint(name: str, *, fail_on: str = zettel_lint.ERROR):
    """(document, exit code), exactly as the CLI computes them."""
    return zettel_lint.lint_vault(FIXTURES / name, NOW, set(), fail_on)


def keys(document: dict) -> Counter:
    """Multiset of finding identities: (code, file, subject). Line numbers are excluded —
    they shift when a fixture is edited, and the subject is what identifies the defect."""
    return Counter(
        (finding["code"], finding["file"], finding["subject"])
        for finding in document["findings"]
    )


# --- the fixtures themselves ----------------------------------------------------------


def test_every_fixture_has_a_manifest_and_an_expectation():
    """A fixture without written-down expectations proves nothing; it only exists."""
    missing = [
        name
        for name in FIXTURE_NAMES
        if not (FIXTURES / name / "MANIFEST.md").is_file()
        or not (FIXTURES / name / "expected.json").is_file()
    ]
    assert not missing, f"fixtures with nothing to assert against: {missing}"


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_no_fixture_file_is_undocumented(name):
    """Every file is named in its manifest, so a stray file cannot hide in a corpus."""
    manifest = (FIXTURES / name / "MANIFEST.md").read_text(encoding="utf-8")
    undocumented = [
        str(path.relative_to(FIXTURES / name))
        for path in sorted((FIXTURES / name).rglob("*"))
        if path.is_file() and path.suffix in {".md", ".py"} and path.name != "MANIFEST.md"
        and path.name not in manifest
    ]
    assert not undocumented, f"{name}: files absent from its MANIFEST.md: {undocumented}"


# --- the assertions -------------------------------------------------------------------


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_findings_match_the_manifest(name):
    document, _ = lint(name)
    wanted = Counter(tuple(entry) for entry in expectation(name)["findings"])
    got = keys(document)
    assert got == wanted, "\n".join(
        [
            f"{name}: {sum(got.values())} findings, expected {sum(wanted.values())}",
            f"  unexpected: {sorted((got - wanted).elements())}",
            f"  missing:    {sorted((wanted - got).elements())}",
        ]
    )


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_not_applicable_checks_are_named(name):
    document, _ = lint(name)
    reported = {entry["code"] for entry in document["skipped_checks"]}
    assert reported == set(expectation(name)["not_applicable"]), (
        f"{name}: not-applicable differs: extra {sorted(reported - set(expectation(name)['not_applicable']))}, "
        f"missing {sorted(set(expectation(name)['not_applicable']) - reported)}"
    )
    for entry in document["skipped_checks"]:
        assert entry["reason"].startswith("not applicable: "), entry


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_metrics_match_the_manifest(name):
    document, _ = lint(name)
    wanted = expectation(name)["metrics"]
    for key, value in wanted.items():
        assert document["summary"]["metrics"][key] == value, f"{name}: {key}"


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_the_exit_code_is_the_same_at_every_threshold_it_should_be(name):
    """Pinned through `--fail-on`, because the threshold is the part people argue about."""
    wanted = expectation(name)["exit"]
    for threshold, code in wanted.items():
        _, actual = lint(name, fail_on=threshold)
        assert actual == code, f"{name}: --fail-on {threshold} exited {actual}, expected {code}"


# --- the control that makes the above mean something ----------------------------------


def run_without(code: str, fixture: str):
    """One fixture's report, with one check deleted from the registry."""
    original = zettel_lint.CHECKS
    zettel_lint.CHECKS = tuple((name, fn) for name, fn in original if name != code)
    try:
        document, _ = lint(fixture)
    finally:
        zettel_lint.CHECKS = original
    return keys(document)


def test_the_registry_really_is_what_it_says():
    """Guard for the mutation test below: if this fails, the mutations proved nothing."""
    assert tuple(name for name, _ in zettel_lint.CHECKS) == tuple(sorted(zettel_lint.SEVERITIES))
    assert len(zettel_lint.CHECKS) == len(zettel_lint.SEVERITIES) == 15

    # v2 retired seventeen numbers and promised never to reuse them. A code that came back
    # under a retired number would be the one mistake the numbering rule exists to prevent,
    # so the absence is asserted rather than assumed.
    retired = {
        "ZK004", "ZK007", "ZK009", "ZK011", "ZK013", "ZK016", "ZK017", "ZK018",
        "ZK020", "ZK021", "ZK023", "ZK024", "ZK025", "ZK029", "ZK030", "ZK031", "ZK032",
    }
    assert not retired & set(zettel_lint.SEVERITIES), "a retired code was reused"
    assert len(zettel_lint.SEVERITIES) + len(retired) == 32, "the v1 code set was 32"


# Every (fixture, code) pair where a code's findings can be attributed. vault_defects carries
# 13 of the 15 codes; ZK001 and ZK002 need a directory that is not a vault and a file that
# cannot be parsed, so they live in fixtures of their own.
MUTATION_CASES = [
    (name, entry[0])
    for name in FIXTURE_NAMES
    for entry in expectation(name)["findings"]
]


@pytest.mark.parametrize("fixture, code", sorted(set(MUTATION_CASES)))
def test_each_expected_finding_comes_from_its_own_check(fixture, code):
    """Silence one check and exactly its findings disappear — no more, no fewer.

    Without this, a fixture would pass as long as *something* reported each file, and a
    check that had quietly become a no-op would be covered by a neighbour firing on the
    same note. The comparison is against the same corpus, so the only variable is the
    registry.
    """
    full, _ = lint(fixture)
    before, after = keys(full), run_without(code, fixture)
    lost = before - after
    wanted = Counter(
        tuple(entry) for entry in expectation(fixture)["findings"] if entry[0] == code
    )
    assert not (after - before), (
        f"{fixture}/{code}: silencing it produced new findings: {sorted((after - before).elements())}"
    )
    assert lost == wanted, (
        f"{fixture}/{code}: silencing it removed {sorted(lost.elements())}, "
        f"the manifest attributes {sorted(wanted.elements())} to it"
    )


# --- coverage -------------------------------------------------------------------------


def test_every_check_code_is_exercised_by_some_fixture():
    """A check with no fixture is a check nobody has ever seen fire."""
    covered = {
        entry[0]
        for name in FIXTURE_NAMES
        for entry in expectation(name)["findings"]
    }
    assert covered == set(zettel_lint.SEVERITIES)


def test_the_scope_tables_partition_the_codes():
    """Every code is note-scoped, raw-scoped, or vault-scoped — never two, never none."""
    note, raw = zettel_lint.NOTE_SCOPED, zettel_lint.RAW_SCOPED
    assert not note & raw, note & raw
    assert note | raw <= set(zettel_lint.SEVERITIES)
    assert note | raw | (set() if not hasattr(zettel_lint, "VAULT_SCOPED") else set()) <= set(
        zettel_lint.SEVERITIES
    )


def test_the_severity_table_covers_every_check():
    assert set(zettel_lint.SEVERITIES) == {code for code, _ in zettel_lint.CHECKS}


# --- the declaration the fixtures depend on ------------------------------------------


def test_vault_defects_declares_its_vocabulary_through_schema_md():
    """The corpus's four conformance defects must be defects against SCHEMA.md.

    If a dimension name were misspelled it would silently become "not declared", and the
    fixture would be testing a smaller declaration than its manifest claims — while still
    reporting the same four findings, because the values it does check are unchanged. The
    full declaration is pinned for that reason, not for its own sake.
    """
    document, _ = lint("vault_defects")
    assert document["declared"] == {
        "confidences": ["high", "low", "medium"],
        "required_fields": ["created", "id", "status", "title", "type"],
        "statuses": ["archived", "draft", "evergreen", "seed"],
        "tags": ["cognition", "memory", "method"],
        "types": ["permanent", "source", "structure"],
        "verbs": ["applies", "contradicts", "extends", "source", "supersedes", "supports"],
    }
    assert set(document["declared_sources"]) == set(zettel_lint.VOCABULARY_DIMENSIONS)
    assert set(document["declared_sources"].values()) == {"SCHEMA.md"}


def test_a_vault_that_declares_nothing_is_reported_dimension_by_dimension():
    """The other direction, and the reason `declared_sources` is not just an omission.

    An empty `declared` plus six named dimensions is the report saying *it looked and stood
    down*. A missing key would say nothing at all, and the two must not be the same output.
    """
    document, _ = lint("vault_foreign")
    assert document["declared"] == {}
    assert set(document["declared_sources"]) == set(zettel_lint.VOCABULARY_DIMENSIONS)
    assert set(document["declared_sources"].values()) == {"not declared"}

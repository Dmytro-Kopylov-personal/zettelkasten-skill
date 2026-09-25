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

#: Every fixture's dates sit within a few days of this, or far enough in the past to be
#: stale by any threshold. Pinning it makes the whole module independent of the real clock.
NOW = dt.date(2026, 9, 28)

FIXTURE_NAMES = [
    "vault_clean",
    "vault_defects",
    "vault_minimal",
    "vault_trap",
    "vault_hostile",
    "vault_monoculture",
    "not_a_vault",
]


def expectation(name: str) -> dict:
    return json.loads((FIXTURES / name / "expected.json").read_text(encoding="utf-8"))


def lint(name: str, *, fail_on: str = zettel_lint.ERROR, overrides: dict | None = None):
    """(document, exit code), exactly as the CLI computes them."""
    return zettel_lint.lint_vault(FIXTURES / name, overrides or {}, NOW, set(), fail_on)


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
    assert len(zettel_lint.CHECKS) == len(zettel_lint.SEVERITIES) == 32


# Every (fixture, code) pair where a code's findings can be attributed. vault_defects carries
# 29 of the 32 codes; ZK001, ZK002 and ZK029 live in fixtures of their own.
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


# --- the config layers the fixtures depend on ----------------------------------------


@pytest.mark.parametrize(
    "key, value",
    [
        ("oversized_note_words", 80),
        ("multi_idea_section_words", 10),
        ("log_rotation_entries", 5),
    ],
)
def test_vault_defects_lowers_its_thresholds_through_schema_md(key, value):
    """The corpus's three lowered thresholds must come from SCHEMA.md, not a typo.

    If the key were misspelled, the value would silently fall back to the default and the
    fixture would be testing a different threshold than its manifest claims.
    """
    document, _ = lint("vault_defects")
    assert document["config"][key] == value
    assert document["config_sources"][key] == "SCHEMA.md"


def test_the_command_line_outranks_schema_md():
    """The other half of the same mechanism, and the only place overrides are ordered."""
    document, _ = lint("vault_defects", overrides={"oversized_note_words": 5})
    assert document["config"]["oversized_note_words"] == 5
    assert document["config_sources"]["oversized_note_words"] == "command line"
    assert document["config"]["stale_draft_days"] == 90  # untouched by the override
    assert document["config_sources"]["stale_draft_days"] == "default"

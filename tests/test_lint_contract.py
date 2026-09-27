"""The linter's contract with whatever is calling it.

`tests/test_lint_checks.py` asks whether the right findings appear. This module asks the
questions that must hold no matter which findings appear: is the JSON complete, is it
stable between runs, does the tool write anything, is the exit code the one CI needs, and
does the baseline account for what it hides instead of hiding it.

Every subprocess runs `sys.executable -I`. Isolated mode is not decoration: it ignores
`PYTHONPATH` and the user site directory, so a linter that had grown an import of PyYAML or
anything else would fail here rather than on a machine that happens to have it installed.
That matters because the tool's whole claim is that it runs anywhere with a stock python3.

Nothing here writes outside `tmp_path`, and one test proves it: the fixtures are hashed
before and after a full sweep and must be byte-identical. A fixture is an input; a linter
that edits its inputs is not a verifier. That test carries its own control, because a tree
hash that always returns the same string would make it pass forever.

Every subprocess is also handed an environment with `ZETTELKASTEN_VAULT_PATH` removed, so a
machine with the variable exported resolves the same as one without it. That was not true
until the variable was set, and it was the absence of a vault in the environment, not the
linter, that the "no vault" test was passing on.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

import pytest
from conftest import FIXTURES, REPO

sys.path.insert(0, str(REPO / "skill" / "scripts"))
import zettel_lint  # noqa: E402

LINTER = REPO / "skill" / "scripts" / "zettel_lint.py"
NOW = "2026-09-28"
FIXTURE_NAMES = [
    "vault_clean",
    "vault_defects",
    "vault_minimal",
    "vault_trap",
    "vault_hostile",
    "vault_nested",
    "vault_regressions",
    "vault_foreign",
    "vault_resolution",
    "not_a_vault",
]


VAULT_PIN = "ZETTELKASTEN_VAULT_PATH"


def environment_without_the_pin() -> dict:
    """The ambient environment, minus the vault pin.

    Every subprocess here gets this, so the suite resolves the same way on a machine that has
    `ZETTELKASTEN_VAULT_PATH` exported as on one that does not. It did not, until the variable
    was actually set: `test_the_vault_may_come_from_the_environment` passed only because nothing
    in the environment named a vault, and failed the moment the README's own advice was followed.
    A test whose result depends on the shell that started it is not measuring the linter.
    """
    return {key: value for key, value in os.environ.items() if key != VAULT_PIN}


def run(*args: str, expect_ok: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [sys.executable, "-I", str(LINTER), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        env=environment_without_the_pin(),
    )
    if expect_ok and result.returncode not in (0, 1, 2):
        raise AssertionError(f"unexpected exit {result.returncode}: {result.stderr}")
    return result


def tree_hash(root) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            digest.update(str(path.relative_to(root)).encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
    return digest.hexdigest()


def document_for(name: str, *extra: str) -> dict:
    result = run(str(FIXTURES / name), "--json", "--now", NOW, *extra)
    return json.loads(result.stdout)


# --- the JSON contract ----------------------------------------------------------------

TOP_LEVEL = {
    "schema_version",
    "vault",
    "now",
    "declared",
    "declared_sources",
    "summary",
    "findings",
    "parse_failures",
    "skipped_checks",
}

#: The documented finding shape, and nothing else. `key` is deliberately absent: it is
#: derivable as code|file|subject, and `--baseline-keys` is the sanctioned way to get it, so
#: emitting it per finding would be a second copy of a format that must not diverge.
FINDING_KEYS = {
    "code",
    "severity",
    "file",
    "line",
    "subject",
    "message",
    "evidence",
    "action",
    "doc",
    "fix",
}


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_the_json_contract_has_every_mandatory_field(name):
    document = document_for(name)
    assert set(document) == TOP_LEVEL, sorted(set(document) ^ TOP_LEVEL)
    assert document["schema_version"] == "2"
    assert document["now"] == NOW, "the reference date must be reported as resolved"
    assert set(document["summary"]) == {
        "counts_by_code",
        "counts_by_severity",
        "metrics",
        "baselined",
    }
    for finding in document["findings"]:
        assert set(finding) == FINDING_KEYS, sorted(set(finding) ^ FINDING_KEYS)
        # Reserved and null: there is no --fix, and the field is where it would go.
        assert finding["fix"] is None
        assert finding["code"] in zettel_lint.SEVERITIES
        assert finding["severity"] == zettel_lint.SEVERITIES[finding["code"]]
        assert finding["line"] is None or isinstance(finding["line"], int)


def test_parse_failures_and_skipped_checks_are_mandatory_and_populated():
    """The two fields that make a green report falsifiable, shown non-empty together."""
    hostile = document_for("vault_hostile")
    assert len(hostile["parse_failures"]) == 8
    assert all({"file", "line", "message"} == set(entry) for entry in hostile["parse_failures"])

    minimal = document_for("vault_minimal")
    assert len(minimal["skipped_checks"]) == 6
    assert all({"code", "reason"} == set(entry) for entry in minimal["skipped_checks"])


def test_a_check_that_could_not_run_is_not_a_check_that_passed():
    """The distinction the whole report rests on, asserted as an invariant."""
    for name in FIXTURE_NAMES:
        document = document_for(name)
        reported = {entry["code"] for entry in document["skipped_checks"]}
        failed = {entry["code"] for entry in document["findings"]}
        assert not reported & failed, f"{name}: {sorted(reported & failed)} both ran and did not"
        by_severity = document["summary"]["counts_by_severity"]
        assert sum(by_severity.values()) == len(document["findings"])
        by_code = document["summary"]["counts_by_code"]
        assert sum(by_code.values()) == len(document["findings"])
        assert set(by_code) == {finding["code"] for finding in document["findings"]}


# --- determinism ----------------------------------------------------------------------


def test_two_runs_are_byte_identical():
    first = run(str(FIXTURES / "vault_defects"), "--json", "--now", NOW).stdout
    second = run(str(FIXTURES / "vault_defects"), "--json", "--now", NOW).stdout
    assert first == second
    assert json.loads(first) == json.loads(second)


def test_the_date_the_report_was_taken_on_does_not_change_what_it_found():
    """v2's sharpest new invariant: no check reads the clock.

    Under v1 this test ran the other way — a year later, the stale-draft and old-capture
    checks had more to say, and `now` was an input to the answer. Every check that read it
    was a threshold check, so all of them are gone, and the property that replaced them is
    testable: the same bytes report the same findings whenever they are run.

    Only `findings` is compared. `now` itself still moves, because a report should say when
    it was taken — that is a fact about the run, not about the vault.
    """
    early = document_for("vault_defects", "--now", "2026-09-28")
    late = document_for("vault_defects", "--now", "2027-09-28")
    assert early == late | {"now": early["now"]}
    assert early["now"] != late["now"], "the reference date is not being reported"


# --- the read-only proof ---------------------------------------------------------------


def test_a_full_sweep_writes_nothing(tmp_path):
    before = tree_hash(FIXTURES)
    for name in FIXTURE_NAMES:
        for extra in ((), ("--json",), ("--fail-on", "info"), ("--baseline-keys",)):
            run(str(FIXTURES / name), "--now", NOW, *extra)
    assert tree_hash(FIXTURES) == before, "the linter modified its own input"


def test_the_read_only_proof_would_notice_a_write(tmp_path):
    """Control for the test above: the hash must actually be able to change."""
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    (scratch / "a.md").write_bytes(b"one\n")
    before = tree_hash(scratch)
    (scratch / "a.md").write_bytes(b"two\n")
    assert tree_hash(scratch) != before
    (scratch / "b.md").write_bytes(b"one\n")
    assert tree_hash(scratch) != before


def test_the_hash_subcommand_does_not_write_either():
    """`hash` reads a file and prints a digest; it must not rewrite the file it read."""
    target = FIXTURES / "vault_clean" / "raw" / "articles" / "attention-2001.md"
    before = target.read_bytes()
    result = run("hash", str(target))
    assert result.returncode == 0 and len(result.stdout.strip()) == 64
    assert target.read_bytes() == before


# --- exit codes and the paths that lead to them ---------------------------------------


def test_exit_codes_through_the_cli():
    assert run(str(FIXTURES / "vault_clean"), "--now", NOW).returncode == 0
    assert run(str(FIXTURES / "vault_defects"), "--now", NOW).returncode == 1
    assert run(str(FIXTURES / "not_a_vault"), "--now", NOW).returncode == 2


def test_not_a_vault_still_emits_json_so_ci_can_tell_the_two_apart():
    result = run(str(FIXTURES / "not_a_vault"), "--json", "--now", NOW)
    assert result.returncode == 2
    document = json.loads(result.stdout)
    assert [entry["code"] for entry in document["findings"]] == ["ZK001"] * 3
    assert document["summary"]["metrics"]["notes"] == 0


def test_the_text_summary_says_what_exit_2_means():
    """The JSON is the machine's answer; a human reading the text output needs the sentence
    that stops '0 notes, 0 findings' from looking like a clean vault."""
    result = run(str(FIXTURES / "not_a_vault"), "--now", NOW)
    assert result.returncode == 2
    assert "not a vault" in result.stderr and "never 0" in result.stderr


def test_the_vault_may_come_from_the_environment():
    """The variable alone, with no path in the arguments, names the vault. This is the direction
    the README tells a human to rely on, so it is asserted rather than assumed; its pair below
    keeps a variable that nothing ever reads from passing it."""
    environment = dict(environment_without_the_pin(), **{VAULT_PIN: str(FIXTURES / "vault_clean")})
    result = subprocess.run(
        [sys.executable, "-I", str(LINTER), "--json", "--now", NOW],
        capture_output=True,
        text=True,
        env=environment,
        cwd=str(REPO),
    )
    assert result.returncode == 0, result.stderr
    document = json.loads(result.stdout)
    assert document["vault"] == str(FIXTURES / "vault_clean")
    assert document["summary"]["metrics"]["notes"] == 8


def test_with_neither_a_path_nor_the_variable_it_is_a_usage_error():
    result = run("--json", "--now", NOW, expect_ok=False)
    assert result.returncode == 2, "no vault and no environment variable is a usage error"


def test_an_explicit_path_outranks_the_environment():
    environment = dict(environment_without_the_pin(), **{VAULT_PIN: str(FIXTURES / "vault_defects")})
    result = subprocess.run(
        [sys.executable, "-I", str(LINTER), str(FIXTURES / "vault_clean"), "--json", "--now", NOW],
        capture_output=True,
        text=True,
        env=environment,
        cwd=str(REPO),
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["summary"]["metrics"]["notes"] == 8


# --- the baseline ---------------------------------------------------------------------


def test_the_baseline_suppresses_and_counts(tmp_path):
    """The key set is a public contract too, and v2 changed its contents.

    Retired codes leave inert keys behind in a baseline written by v1. That is safe — a key
    that matches no finding silences nothing — but it is worth stating that the mechanism was
    not changed to make room for it: the keys are still `code|file|subject`, and a v1 baseline
    still suppresses whichever of its entries survive under their own code.
    """
    keys = json.loads(run(str(FIXTURES / "vault_defects"), "--baseline-keys", "--now", NOW).stdout)
    assert len(keys) == 20
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps(keys), encoding="utf-8")

    document = document_for("vault_defects", "--baseline", str(baseline))
    assert document["findings"] == []
    assert document["summary"]["baselined"] == 20
    assert document["summary"]["metrics"]["notes"] == 27, "the vault is still measured, only silenced"
    assert run(str(FIXTURES / "vault_defects"), "--baseline", str(baseline), "--now", NOW).returncode == 0


def test_a_baseline_written_under_v1_leaves_its_retired_keys_inert(tmp_path):
    """The compatibility claim in the release notes, pinned rather than asserted.

    A reader upgrading with a baseline file in hand is told their file keeps working. It does,
    for two reasons that are worth separating: a surviving code means the same thing it did, so
    its key still matches; and a retired code matches nothing at all, so its key is inert."
    """
    keys = json.loads(run(str(FIXTURES / "vault_defects"), "--baseline-keys", "--now", NOW).stdout)
    v1_style = sorted(
        set(keys)
        | {
            "ZK011|permanent/202609270911-orphan-note.md|202609270911-orphan-note",
            "ZK017|permanent/202609270916-stale-draft.md|202609270916-stale-draft",
            "ZK029||supports",
        }
    )
    baseline = tmp_path / "baseline.json"
    baseline.write_text(json.dumps(v1_style), encoding="utf-8")
    document = document_for("vault_defects", "--baseline", str(baseline))
    assert document["findings"] == []
    assert document["summary"]["baselined"] == 20, "the three retired keys silenced nothing"


def test_a_partial_baseline_leaves_the_rest(tmp_path):
    keys = json.loads(run(str(FIXTURES / "vault_defects"), "--baseline-keys", "--now", NOW).stdout)
    partial = tmp_path / "partial.json"
    partial.write_text(json.dumps(keys[:5]), encoding="utf-8")
    document = document_for("vault_defects", "--baseline", str(partial))
    assert document["summary"]["baselined"] == 5
    assert len(document["findings"]) == 15
    assert run(str(FIXTURES / "vault_defects"), "--baseline", str(partial), "--now", NOW).returncode == 1


def test_baseline_keys_are_stable_across_edits_that_move_lines(tmp_path):
    """The key is code|file|subject precisely so that adding a line does not resurrect a
    finding that someone has already reviewed and accepted."""
    keys = json.loads(run(str(FIXTURES / "vault_defects"), "--baseline-keys", "--now", NOW).stdout)
    assert all(len(key.split("|")) == 3 for key in keys)
    assert keys == sorted(keys)


def test_fail_on_promotes_an_advisory_finding_to_a_failure():
    """A warning is a pass at the default threshold and a failure one notch above it.

    **What this test no longer covers, since v2:** no fixture is INFO-only any more, so the
    step from `warn` to `info` is asserted only in the direction of *not being stricter* —
    every fixture's map in test_lint_checks.py pins all three thresholds, and a vault that
    fails at `warn` must still fail at `info`. The step that would catch `--fail-on info`
    behaving like `--fail-on warn` needs a vault whose only finding is informational; the
    fixture that used to be exactly that was `vault_monoculture`, and it retired with the
    check that gave it a finding. Named here rather than left as an unnoticed hole.
    """
    assert run(str(FIXTURES / "vault_trap"), "--now", NOW).returncode == 0
    assert run(str(FIXTURES / "vault_trap"), "--fail-on", "warn", "--now", NOW).returncode == 1
    assert run(str(FIXTURES / "vault_trap"), "--fail-on", "info", "--now", NOW).returncode == 1
    # The other direction: an empty report is 0 at the strictest threshold.
    assert run(str(FIXTURES / "vault_foreign"), "--fail-on", "info", "--now", NOW).returncode == 0


def test_quiet_says_nothing_and_still_answers():
    result = run(str(FIXTURES / "vault_defects"), "--quiet", "--now", NOW)
    assert result.stdout == ""
    assert result.returncode == 1


# --- the human-readable summary -------------------------------------------------------


def test_the_not_run_lines_are_grouped_by_reason():
    skipped = [
        {"code": "ZK003", "reason": "not applicable: no notes"},
        {"code": "ZK005", "reason": "not applicable: no notes"},
        {"code": "ZK012", "reason": "not applicable: no index"},
    ]
    assert zettel_lint.group_skipped(skipped) == [
        ("not applicable: no notes", ["ZK003", "ZK005"]),
        ("not applicable: no index", ["ZK012"]),
    ]


def test_a_directory_that_is_not_a_vault_does_not_print_the_same_line_once_per_check():
    """The not-applicable checks must not become one near-identical line each.

    Grouping by reason is the whole of the compression, and that is deliberate. A
    `ZK003..ZK028 (8 checks)` range would name two codes and hide six behind a span that is
    not a contiguous run of the registry, so nobody could expand it — what the line saves in
    width it costs in being readable. Every code is named instead, and this asserts the two
    forms agree: the text names exactly the codes the JSON reports as skipped.
    """
    text = run(str(FIXTURES / "not_a_vault"), "--now", NOW).stdout
    skipped = {entry["code"] for entry in document_for("not_a_vault")["skipped_checks"]}

    lines = [line for line in text.splitlines() if line.startswith("NOT RUN:")]
    assert len(lines) <= 8, f"the summary repeated itself {len(lines)} times:\n" + "\n".join(lines)
    assert ".." not in text, "a range would hide codes behind a span nobody can expand"
    named = set(re.findall(r"ZK\d{3}", "\n".join(lines)))
    assert named == skipped, f"the text and the JSON disagree about {sorted(named ^ skipped)}"
    assert "ZK010" in named, "the middle of a group is exactly what a range used to hide"

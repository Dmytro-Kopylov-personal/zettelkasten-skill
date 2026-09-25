"""The differential oracle for the hand-rolled YAML subset.

A parser that agrees with nothing is not a parser. So for every document in the corpus
below, the real `yaml.safe_load` is run beside `parse_yaml_subset` and the two must agree
— on the values, down to their types, and on whether the document parses at all.

Divergence is allowed in exactly one direction, and never silently: `WE_ARE_STRICTER`
lists the constructs PyYAML accepts and this parser deliberately rejects, each named and
each asserted to be a case PyYAML really does accept. Anything else that diverges is a
bug in one of them, and this module is where it gets caught.

PyYAML is not installed on this machine's system python (V5 in docs/design.md), so the
whole module is skipped — never faked — when it is absent. That is why the suite runs
under `uv run --with pytest --with pyyaml`.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import sys

import pytest
from conftest import FIXTURES, REPO

sys.path.insert(0, str(REPO / "skill" / "scripts"))
import zettel_lint  # noqa: E402

yaml = pytest.importorskip("yaml", reason="PyYAML is what this module diffs against")

parse = zettel_lint.parse_yaml_subset


def pyyaml_mapping(text: str) -> tuple[dict | None, bool]:
    """(mapping, parsed). A non-mapping is a parse failure for frontmatter purposes."""
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError:
        return None, False
    if not isinstance(loaded, dict):
        return None, False
    return loaded, True


# --- the corpus -------------------------------------------------------------------

MUST_MATCH = {
    "note skeleton": """
id: 202609261430
title: Attention budget is a scarce resource
type: permanent
status: seed
created: 2026-09-26
updated: 2026-09-26
confidence: medium
""",
    "flow list of tags": "tags: [cognition, productivity]\n",
    "empty flow list": "tags: []\n",
    "block list of sources": """
sources:
  - raw/articles/karpathy-llm-wiki-2026.md
  - raw/papers/attention-2001.pdf
""",
    "list of single-key maps": """
links:
  - target: 202609251200-spaced-repetition
    verb: supports
  - target: 202609240900-working-memory-limits
    verb: extends
""",
    "double-quoted scalar with a colon": 'title: "Attention: a scarce resource"\n',
    "single-quoted scalar with an escaped quote": "title: 'It''s a scarce resource'\n",
    "quoted value that looks like a link": 'title: "[[not a link]]"\n',
    "quoted hash is not a comment": 'title: "a # b"\n',
    "trailing comment": "status: seed # not a draft yet\n",
    "key with a null value": "confidence:\n",
    "key with a tilde null": "confidence: ~\n",
    "yaml 1.1 booleans": "archived: no\npinned: yes\n",
    "quoted number stays a string": 'id: "202609261430"\n',
    "underscored integer": "count: 1_000\n",
    "plain float": "score: 1.5\n",
    "float with an explicit exponent sign": "score: 1.0e+3\n",
    "leading-dot float": "ratio: .5\n",
    "url is a plain scalar": "source_url: https://example.com/a:b?c=d\n",
    "empty mapping section is null": "links:\ntags: [a]\n",
    "blank lines and comment lines": """
# the frontmatter of a note

id: 202609261430

# status of the note
status: seed

""",
    "windows line endings": "id: 202609261430\r\nstatus: seed\r\n",
    "quoted key-like value": 'title: "key: value"\n',
    "date and datetime": "created: 2026-09-26\nstamped: 2026-09-26 14:30:00\n",
    "negative and signed numbers": "delta: -3\nweight: +2.5\n",
    "single item block list": "sources:\n  - raw/notes/one.md\n",
}

WE_ARE_STRICTER = {
    # PyYAML parses each of these; the linter refuses to guess. Every entry is asserted
    # below to be something PyYAML really does accept, so this list cannot quietly
    # become a list of documents that were broken anyway.
    "nested mappings": "metadata:\n  hermes:\n    tags: [a, b]\n",
    "block scalar": "description: |\n  two\n  lines\n",
    "folded block scalar": "description: >\n  two\n  lines\n",
    "anchor": "confidence: &medium medium\n",
    "alias": "a: &x medium\nb: *x\n",
    "flow mapping": "metadata: {a: 1}\n",
    "duplicate key": "status: seed\nstatus: evergreen\n",
}

BOTH_REJECT = {
    "tab indentation": "tags:\n\t- a\n",
    "tab inside a value": "title: a\tb\n",
    "unclosed double quote": 'title: "abc\n',
    "unclosed single quote": "title: 'abc\n",
    "unquoted colon in a scalar": "title: Attention: a scarce resource\n",
    "no colon at all": "just some text\n",
    "a list where a mapping belongs": "- a\n- b\n",
    "flow list that never closes": "tags: [a, b\n",
}


@pytest.mark.parametrize("name", sorted(MUST_MATCH), ids=sorted(MUST_MATCH))
def test_the_parser_matches_pyyaml(name):
    text = MUST_MATCH[name]
    expected, pyyaml_parsed = pyyaml_mapping(text)
    assert pyyaml_parsed, f"{name}: the corpus assumed PyYAML accepts this"

    data, error, line = parse(text)
    assert error is None, f"{name}: parse failed at line {line}: {error}"
    assert data == expected, f"{name}: {data!r} != {expected!r}"


@pytest.mark.parametrize("name", sorted(WE_ARE_STRICTER), ids=sorted(WE_ARE_STRICTER))
def test_the_parser_is_deliberately_stricter_than_pyyaml(name):
    text = WE_ARE_STRICTER[name]
    _, pyyaml_parsed = pyyaml_mapping(text)
    assert pyyaml_parsed, (
        f"{name}: PyYAML no longer accepts this, so 'stricter' is the wrong label — "
        f"move it to BOTH_REJECT"
    )

    data, error, line = parse(text)
    assert error is not None, f"{name}: the parser accepted a construct it should refuse"
    assert data is None, "a failed parse must not produce data"
    assert isinstance(line, int) and line >= 1, f"{name}: no line number for {error!r}"


@pytest.mark.parametrize("name", sorted(BOTH_REJECT), ids=sorted(BOTH_REJECT))
def test_both_parsers_reject(name):
    text = BOTH_REJECT[name]
    _, pyyaml_parsed = pyyaml_mapping(text)
    assert not pyyaml_parsed, f"{name}: the corpus assumed PyYAML rejects this"

    data, error, line = parse(text)
    assert error is not None, f"{name}: the parser accepted malformed YAML"
    assert data is None
    assert isinstance(line, int) and line >= 1


def test_parse_failure_reports_the_right_line():
    _, error, line = parse("id: 202609261430\nstatus: seed\ntags:\n\t- a\n")
    assert line == 4, (line, error)


# The line each construct is reported on, pinned exactly. A finding that names the wrong
# line is worse than no finding: it sends the reader to the wrong place in the file.
EXPECTED_ERROR_LINE = {
    "nested mappings": 2,
    "block scalar": 1,
    "folded block scalar": 1,
    "anchor": 1,
    "alias": 1,
    "flow mapping": 1,
    "duplicate key": 2,
    "tab indentation": 2,
    "tab inside a value": 1,
    "unclosed double quote": 1,
    "unclosed single quote": 1,
    "unquoted colon in a scalar": 1,
    "no colon at all": 1,
    "a list where a mapping belongs": 1,
    "flow list that never closes": 1,
}


@pytest.mark.parametrize("name", sorted(EXPECTED_ERROR_LINE), ids=sorted(EXPECTED_ERROR_LINE))
def test_each_rejected_construct_is_reported_on_its_own_line(name):
    text = WE_ARE_STRICTER.get(name) or BOTH_REJECT[name]
    _, error, line = parse(text)
    assert error is not None, f"{name}: accepted"
    assert line == EXPECTED_ERROR_LINE[name], f"{name}: reported line {line} for {error!r}"


def test_the_line_table_covers_every_rejected_construct():
    """Control: a new rejected construct must not silently go unpinned."""
    assert set(EXPECTED_ERROR_LINE) == set(WE_ARE_STRICTER) | set(BOTH_REJECT)


def test_an_error_result_is_never_an_empty_mapping():
    """The whole point: Hermes' fallback split(':') makes every check pass vacuously."""
    data, error, _ = parse("name: [unclosed\n")
    assert data is None and error is not None


# --- the note format the skill actually writes ------------------------------------

NOTE_FRONTMATTER = """id: 202609261430
title: Attention budget is a scarce resource
type: permanent
status: seed
created: 2026-09-26
updated: 2026-09-26
sources:
  - raw/articles/karpathy-llm-wiki-2026.md
confidence: medium
tags: [cognition, productivity]
links:
  - target: 202609251200-spaced-repetition
    verb: supports
  - target: 202609240900-working-memory-limits
    verb: extends
"""


def test_the_documented_note_format_parses_the_same_way_twice():
    expected, parsed = pyyaml_mapping(NOTE_FRONTMATTER)
    assert parsed
    data, error, line = parse(NOTE_FRONTMATTER)
    assert error is None, error
    assert data == expected

    assert data["id"] == 202609261430
    assert data["created"] == dt.date(2026, 9, 26)
    assert data["tags"] == ["cognition", "productivity"]
    assert data["links"][0] == {"target": "202609251200-spaced-repetition", "verb": "supports"}
    assert data["sources"] == ["raw/articles/karpathy-llm-wiki-2026.md"]


# --- every fixture block is swept in as well ---------------------------------------


def manifest_parse_failures() -> set[str]:
    """Fixture paths their own `expected.json` declares as ZK002.

    The sweep asks the manifest, not the directory name. `vault_hostile` holds files that
    are meant to fail parsing *and* files that are meant to succeed (the CRLF control), so
    "this file is in the hostile fixture" answers the wrong question.
    """
    declared: set[str] = set()
    if not FIXTURES.exists():
        return declared
    for path in sorted(FIXTURES.glob("*/expected.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for code, file, _subject in data["findings"]:
            if code == "ZK002":
                declared.add(f"{path.parent.name}/{file}")
    return declared


#: Fixture files whose ZK002 this sweep cannot reproduce, each with the reason. They are
#: still asserted by `tests/test_lint_checks.py`, which compares the reported ZK002 set with
#: the manifest; what is lost here is only the second opinion from PyYAML.
UNSWEEPABLE = {
    "vault_hostile/permanent/202609280906-no-frontmatter.md": "there is no frontmatter block to hand to either parser",
    "vault_hostile/permanent/202609280907-byte-order-mark.md": "the fence is not at offset 0, so the split finds nothing",
    "vault_hostile/permanent/202609280909-latin-1.md": "the bytes are not valid UTF-8, so a re-decode is not the same document",
}


def fixture_frontmatters() -> list[tuple[str, str]]:
    """(name, frontmatter text) for every fixture file that has a readable frontmatter."""
    if not FIXTURES.exists():
        return []
    cases = []
    for path in sorted(FIXTURES.rglob("*.md")):
        if path.name in {"MANIFEST.md", "README.md"}:
            continue
        raw = path.read_bytes()
        name = str(path.relative_to(FIXTURES))
        if name in UNSWEEPABLE:
            continue
        frontmatter, _ = zettel_lint.split_frontmatter_bytes(raw)
        if not frontmatter:
            continue
        try:
            cases.append((name, frontmatter.decode("utf-8")))
        except UnicodeDecodeError:
            continue
    return cases


def test_fixtures_exist_to_sweep():
    if not FIXTURES.exists():
        pytest.skip("no fixtures yet")
    assert fixture_frontmatters(), "the sweep found nothing to compare"


def test_every_declared_parse_failure_is_either_swept_or_named():
    """Closed loop on the exceptions above.

    A fixture file added to a manifest as unparseable must either be swept here (so PyYAML
    gets a say) or appear in `UNSWEEPABLE` with a reason. Otherwise a new hostile file could
    be declared in a manifest and quietly never be examined by this module at all.
    """
    swept = {name for name, _ in fixture_frontmatters()}
    declared = manifest_parse_failures()
    # Every declared failure is swept or explained...
    assert declared <= swept | set(UNSWEEPABLE), (
        f"declared but neither swept nor explained: {sorted(declared - swept - set(UNSWEEPABLE))}"
    )
    # ...and every exemption is declared, so the list cannot become a place to hide a file
    # from both this module and the manifest.
    assert set(UNSWEEPABLE) <= declared, (
        f"exempted from the sweep but not declared as a parse failure: "
        f"{sorted(set(UNSWEEPABLE) - declared)}"
    )
    # The sweep is not only parse failures: valid fixtures are swept too, which is the
    # whole point of running both parsers over them.
    assert swept - declared, "the sweep found nothing but unparseable files"


@pytest.mark.parametrize(
    "name, text", fixture_frontmatters(), ids=[case[0] for case in fixture_frontmatters()]
)
def test_every_fixture_frontmatter_agrees_with_pyyaml(name, text):
    expected, pyyaml_parsed = pyyaml_mapping(text)
    data, error, line = parse(text)
    if name in manifest_parse_failures():
        # The manifest says this file cannot be parsed, so the parser must refuse it — and
        # must say where. PyYAML's verdict is deliberately not asserted here: these files
        # include constructs PyYAML accepts (block scalars, anchors, duplicate keys) and
        # constructs it rejects (tabs, unclosed quotes), and which side each is on is
        # already pinned, by name, in WE_ARE_STRICTER and BOTH_REJECT above.
        assert error is not None, f"{name}: the manifest expects ZK002, but the parser read it"
        assert isinstance(line, int) and line >= 1, f"{name}: a refusal with no line number"
        return
    assert error is None, f"{name}: line {line}: {error}"
    assert data == expected, f"{name}: {data!r} != {expected!r}"

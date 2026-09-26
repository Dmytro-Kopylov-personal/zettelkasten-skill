"""The committed goldens: byte-exact against render(), and agreeing with a second opinion.

`tests/golden/*.SKILL.md` is the only committed copy of a rendered skill. It is both the
reviewable artifact and the byte-exact oracle, which is why `--check` diffs against it
and why the shared-body invariant below reads from it rather than from the template.
"""

from __future__ import annotations

import json
import re

import pytest
from conftest import GOLDEN, REPO, strip_seams
from support import platform_rules

import render

PLATFORMS = sorted(render.PLATFORMS)

# Peer skills (llm-wiki, obsidian, hermes-agent-skill-authoring) sit at 8-14k chars.
MIN_CHARS, MAX_CHARS = 8_000, 16_000
# V2: Hermes truncates the catalog line to `desc[:57] + "..."`.
HERMES_VISIBLE_DESCRIPTION_CHARS = 53


def golden(platform: str) -> str:
    return (GOLDEN / f"{platform}.SKILL.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("platform", PLATFORMS)
def test_golden_is_the_current_render(platform):
    assert golden(platform) == render.render(platform)


@pytest.mark.parametrize("platform", PLATFORMS)
def test_golden_validates_clean_under_both_implementations(platform):
    text = golden(platform)
    assert render.validate(platform, text) == []
    assert platform_rules.check(platform, text) == []


def test_only_the_seams_differ_between_platforms():
    """The body was never forked per platform — only the frontmatter and env block."""
    bodies = {platform: strip_seams(golden(platform)) for platform in PLATFORMS}
    reference = bodies["claude"]
    for platform, body in bodies.items():
        assert body == reference, f"{platform}'s shared body drifted from claude's"


def test_the_seams_really_are_different():
    """Control for the test above: if every render were identical, it would pass vacuously."""
    assert len({golden(p) for p in PLATFORMS}) == len(PLATFORMS)
    assert len({golden(p).split("---\n")[1] for p in PLATFORMS}) == len(PLATFORMS)


@pytest.mark.parametrize("platform", PLATFORMS)
def test_golden_sits_in_the_peer_size_band(platform):
    text = golden(platform)
    assert MIN_CHARS <= len(text) <= MAX_CHARS, f"{platform}: {len(text)} chars"


def test_hermes_golden_is_far_below_the_hard_cap():
    """MAX_SKILL_CONTENT_CHARS = 100_000; the headroom is deliberate, not accidental."""
    assert len(golden("hermes")) < 20_000


def test_copilot_body_stays_under_the_third_party_cap():
    _, body = render.split_frontmatter(golden("copilot"))
    assert len(body.splitlines()) < render.COPILOT_MAX_BODY_LINES


def test_hermes_description_survives_catalog_truncation():
    """V2: the truncated description *is* the discovery surface in Hermes."""
    doc = platform_rules.parse(golden("hermes"))
    visible = platform_rules.description(doc)[:HERMES_VISIBLE_DESCRIPTION_CHARS].lower()
    for trigger in ("ingest", "query", "lint", "init", "zettelkasten"):
        assert trigger in visible, f"{trigger!r} is not visible in {visible!r}"


# --- two implementations, one corpus ----------------------------------------------

GOOD = {
    "hermes": "name: zettelkasten\ndescription: A description.\nplatforms: [linux, macos, windows]",
    "claude": "name: zettelkasten\ndescription: A description.\nlicense: MIT",
    "copilot": "name: zettelkasten\ndescription: A description.",
}

LONG_DESCRIPTION = "d" * 1025

BAD: list[tuple[str, str, str]] = [
    # V1: the spec's own example — an agent name in an OS gate.
    ("agent-names-in-platforms", "hermes",
     "name: zettelkasten\ndescription: d\nplatforms: [copilot, hermes]"),
    ("no-platforms", "hermes", "name: zettelkasten\ndescription: d"),
    ("non-os-platform", "hermes", "name: zettelkasten\ndescription: d\nplatforms: [copilot]"),
    ("claude-version-key", "claude", "name: zettelkasten\ndescription: d\nversion: 1.0.0"),
    ("claude-author-key", "claude", "name: zettelkasten\ndescription: d\nauthor: someone"),
    ("claude-angle-brackets", "claude", "name: zettelkasten\ndescription: has <tag>"),
    ("claude-platforms-key", "claude",
     "name: zettelkasten\ndescription: d\nplatforms: [linux]"),
    ("copilot-name-mismatch", "copilot", "name: zettel\ndescription: d"),
    ("copilot-angle-brackets", "copilot", "name: zettelkasten\ndescription: has <tag>"),
    ("uppercase-name", "hermes", "name: Zettelkasten\ndescription: d\nplatforms: [linux]"),
    ("name-with-space", "hermes", "name: zettel kasten\ndescription: d\nplatforms: [linux]"),
    ("name-too-long", "hermes",
     "name: " + "a" * 65 + "\ndescription: d\nplatforms: [linux]"),
    ("description-too-long", "hermes",
     "name: zettelkasten\ndescription: " + LONG_DESCRIPTION + "\nplatforms: [linux]"),
    ("no-name", "hermes", "description: d\nplatforms: [linux]"),
    ("no-description", "hermes", "name: zettelkasten\nplatforms: [linux]"),
    ("empty-description", "hermes", "name: zettelkasten\ndescription: ''\nplatforms: [linux]"),
]


def build(platform: str, frontmatter: str, body: str = "The idea, stated plainly.\n") -> str:
    return f"---\n{frontmatter.strip()}\n---\n\n{body}\n"


@pytest.mark.parametrize("platform", PLATFORMS)
def test_the_two_implementations_agree_on_good_documents(platform):
    text = golden(platform)
    assert not render.validate(platform, text)
    assert not platform_rules.check(platform, text)


@pytest.mark.parametrize(
    "label, platform, frontmatter",
    BAD,
    ids=[case[0] for case in BAD],
)
def test_the_two_implementations_agree_on_bad_documents(label, platform, frontmatter):
    text = build(platform, frontmatter)
    mine = render.validate(platform, text)
    theirs = platform_rules.check(platform, text)
    assert bool(mine) == bool(theirs), f"{label}: render={mine} rules={theirs}"
    assert mine, f"{label} was not flagged by either implementation"


def test_agreement_extends_to_body_level_defects():
    cases = {
        "empty-body": ("hermes", GOOD["hermes"], "   \n"),
        "copilot-too-many-lines": (
            "copilot",
            GOOD["copilot"],
            "\n".join(f"line {i}" for i in range(render.COPILOT_MAX_BODY_LINES + 1)),
        ),
    }
    for label, (platform, frontmatter, body) in cases.items():
        text = build(platform, frontmatter, body)
        mine, theirs = render.validate(platform, text), platform_rules.check(platform, text)
        assert bool(mine) == bool(theirs), f"{label}: render={mine} rules={theirs}"
        assert mine, f"{label} was not flagged"


@pytest.mark.parametrize(
    "label, text",
    [
        ("no-frontmatter", "# A heading and nothing else\n"),
        ("unclosed-fence", "---\nname: zettelkasten\ndescription: d\n\nbody\n"),
    ],
)
def test_agreement_extends_to_malformed_documents(label, text):
    for platform in PLATFORMS:
        mine, theirs = render.validate(platform, text), platform_rules.check(platform, text)
        assert bool(mine) == bool(theirs), f"{label}/{platform}: render={mine} rules={theirs}"
        assert mine, f"{label}/{platform} was not flagged"


def test_the_corpus_is_not_all_bad():
    """Control: an implementation that flags everything would pass the tests above."""
    for platform in PLATFORMS:
        assert render.validate(platform, render.render(platform)) == []


def test_golden_files_live_where_the_renderer_expects_them():
    for platform in PLATFORMS:
        assert GOLDEN == REPO / "tests" / "golden"
        assert (GOLDEN / f"{platform}.SKILL.md").is_file()


# --- adopting a new golden ----------------------------------------------------------
#
# `--update-goldens` is the one path that can make a failing `--check` pass, which is
# exactly the shape of a tool that gets used to hide a regression. So it is tested for
# what it must not do as well as what it must: it writes the render, byte for byte, and
# it refuses to adopt one that fails validation.


def test_adopting_a_golden_writes_the_render_byte_for_byte(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "GOLDEN", tmp_path)
    assert render.main(["--update-goldens"]) == 0
    for platform in PLATFORMS:
        assert (tmp_path / f"{platform}.SKILL.md").read_text(encoding="utf-8") == render.render(
            platform
        )


def test_adopting_twice_changes_nothing_the_second_time(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(render, "GOLDEN", tmp_path)
    render.main(["--update-goldens"])
    capsys.readouterr()
    assert render.main(["--update-goldens"]) == 0
    assert capsys.readouterr().out.count("unchanged") == len(PLATFORMS)


def test_a_golden_that_fails_validation_is_never_adopted(tmp_path, monkeypatch, capsys):
    """The control on the control: `--check` failing must not be repairable by adopting a
    render the validator rejects."""
    monkeypatch.setattr(render, "GOLDEN", tmp_path)

    def broken(platform: str) -> str:
        return "---\nname: zettelkasten\ndescription: d\n---\n\n   \n"

    monkeypatch.setattr(render, "render", broken)
    assert render.main(["--update-goldens"]) == 1
    assert list(tmp_path.glob("*.SKILL.md")) == [], "an invalid render was written as a golden"
    assert "FAILED validation" in capsys.readouterr().err


def test_the_adopted_golden_is_the_one_check_then_accepts(tmp_path, monkeypatch):
    """The round trip: adopt, then check against the adopted copy, in a directory that has
    never held a golden before."""
    monkeypatch.setattr(render, "GOLDEN", tmp_path)
    assert render.main(["--update-goldens"]) == 0
    assert render.main(["--check"]) == 0


# --- the Claude Code plugin payload ---------------------------------------------------
#
# This repo is also a Claude Code plugin, so `skill/SKILL.md` is committed: a plugin whose
# SKILL.md is gitignored installs as zero skills, silently. That puts a second copy of a
# render back into the tree, which is the thing the golden-as-single-oracle design exists to
# avoid — so the copy is not left to discipline. It is asserted byte-identical to the golden
# it came from, and the manifest is asserted to point at where the skill actually is.


def plugin_manifest() -> dict:
    return json.loads((REPO / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))


def marketplace_manifest() -> dict:
    return json.loads(
        (REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )


def test_the_plugin_payload_is_the_claude_golden_byte_for_byte():
    """The only reason this file is committed is that a plugin must ship one."""
    assert (REPO / "skill" / "SKILL.md").read_text(encoding="utf-8") == golden("claude")


def test_the_plugin_points_at_a_directory_that_really_holds_the_skill():
    """V7: `claude plugin validate` never opens a path named by `skills`, so a wrong value
    here passes validation and installs nothing. Resolve it instead of trusting it."""
    declared = plugin_manifest()["skills"]
    assert declared, "no skills declared — the default skills/ directory does not exist here"
    for entry in declared:
        # A bare "skill" is a load failure, not a style preference.
        assert entry.startswith("./"), f"{entry!r} is not ./-relative"
        target = (REPO / entry).resolve()
        assert (target / "SKILL.md").is_file(), f"{entry!r} holds no SKILL.md"


def test_every_declared_skill_would_actually_load():
    """V9: a skill with no description does not load at all — the plugin registers and the
    skill is simply absent from the loader's array."""
    for entry in plugin_manifest()["skills"]:
        text = ((REPO / entry).resolve() / "SKILL.md").read_text(encoding="utf-8")
        doc = platform_rules.parse(text)
        assert platform_rules.description(doc).strip(), f"{entry}: empty description, will not load"
        assert render.validate("claude", text) == [], f"{entry} fails the claude contract"


def test_the_marketplace_entry_resolves_to_the_plugin_root():
    """`/plugin install <plugin>@<marketplace>` needs both names; the source must resolve."""
    plugin, market = plugin_manifest(), marketplace_manifest()
    assert market["name"], "a marketplace install is addressed by this name"
    entries = [p for p in market["plugins"] if p["name"] == plugin["name"]]
    assert len(entries) == 1, f"expected exactly one entry named {plugin['name']!r}"
    source = entries[0]["source"]
    assert source.startswith("./"), f"{source!r} is not ./-relative"
    assert (REPO / source).resolve() == REPO, "the entry does not point at this plugin"
    assert (REPO / source / ".claude-plugin" / "plugin.json").is_file()


def test_the_version_is_declared_once_and_repeated_only_where_it_must_be():
    """Three hand-maintained strings, one release.

    The plugin manifest and the two platform frontmatter fragments each carry the skill's
    version, and nothing else ties them together — so a bump that updates two of them ships
    a Hermes frontmatter disagreeing with the plugin it came from, silently, because no
    consumer reads both.

    Read with a line pattern rather than a parser: Claude's frontmatter nests the key under
    `metadata`, and the linter's parser rejects nested mappings by design because it reads
    *notes* rather than skill frontmatter. Each pattern is asserted to match, so a
    reformatting fails here instead of matching nothing and comparing equal to nothing.
    """
    claude = (REPO / "src" / "fragments" / "frontmatter.claude.yaml").read_text(encoding="utf-8")
    hermes = (REPO / "src" / "fragments" / "frontmatter.hermes.yaml").read_text(encoding="utf-8")

    found = {}
    for name, text, pattern in (
        ("claude", claude, re.compile(r"^  version:[ \t]*(\S+)$", flags=re.MULTILINE)),
        ("hermes", hermes, re.compile(r"^version:[ \t]*(\S+)$", flags=re.MULTILINE)),
    ):
        match = pattern.search(text)
        assert match, f"the {name} fragment declares no version"
        found[name] = match.group(1).strip("'\"")

    plugin = plugin_manifest()["version"]
    assert set(found.values()) == {plugin}, f"{found} disagrees with plugin.json at {plugin}"


def test_the_marketplace_entry_does_not_silently_disagree_about_the_version():
    """plugin.json wins at install time, so an entry version that differs is ignored rather
    than reported — the divergence this asserts against."""
    plugin, market = plugin_manifest(), marketplace_manifest()
    entry = next(p for p in market["plugins"] if p["name"] == plugin["name"])
    assert entry.get("version", plugin["version"]) == plugin["version"]

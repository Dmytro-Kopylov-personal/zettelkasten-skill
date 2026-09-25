"""The committed goldens: byte-exact against render(), and agreeing with a second opinion.

`tests/golden/*.SKILL.md` is the only committed copy of a rendered skill. It is both the
reviewable artifact and the byte-exact oracle, which is why `--check` diffs against it
and why the shared-body invariant below reads from it rather than from the template.
"""

from __future__ import annotations

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

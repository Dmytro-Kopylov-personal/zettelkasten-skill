"""Conformance against the platforms' own validators, run for real or skipped loudly.

`support/real_validators.py` loads Hermes' `_validate_frontmatter`/`_validate_content_size`
and Anthropic's `quick_validate.py` out of their installed sources. Each test here carries
its own negative control, so a validator that has quietly stopped rejecting anything
fails the suite instead of blessing it.
"""

from __future__ import annotations

import pytest
from conftest import GOLDEN
from support import platform_rules, real_validators

import render

PLATFORMS = sorted(render.PLATFORMS)


def test_hermes_validator_accepts_the_hermes_render():
    text = (GOLDEN / "hermes.SKILL.md").read_text(encoding="utf-8")
    problems, reason = real_validators.check_hermes(text)
    if reason:
        pytest.skip(reason)
    assert problems == []


def test_hermes_validator_rejects_what_it_should():
    """Control: proves the adapter runs the validator rather than a no-op."""
    problems, reason = real_validators.check_hermes("---\nname: zettelkasten\n---\n\nbody\n")
    if reason:
        pytest.skip(reason)
    assert problems and "description" in problems[0]

    empty_body, _ = real_validators.check_hermes("---\nname: z\ndescription: d\n---\n\n \n")
    assert empty_body and "content after the frontmatter" in empty_body[0]


def test_claude_validator_accepts_the_claude_render(tmp_path):
    skill_dir = tmp_path / "zettelkasten"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        (GOLDEN / "claude.SKILL.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    problems, reason = real_validators.check_claude(skill_dir)
    if reason:
        pytest.skip(reason)
    assert problems == []


def test_claude_validator_rejects_what_it_should(tmp_path):
    skill_dir = tmp_path / "zettelkasten"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: zettelkasten\ndescription: d\nversion: 1.0.0\n---\n\nbody\n", encoding="utf-8"
    )
    problems, reason = real_validators.check_claude(skill_dir)
    if reason:
        pytest.skip(reason)
    assert problems and "Unexpected key" in problems[0]


@pytest.mark.parametrize("platform", PLATFORMS)
def test_the_local_rules_agree_with_the_real_validators_for_claude(platform, tmp_path):
    """Where both layers can speak, they must not contradict each other."""
    text = (GOLDEN / f"{platform}.SKILL.md").read_text(encoding="utf-8")
    local = render.validate(platform, text)
    assert local == []
    assert platform_rules.check(platform, text) == []

    if platform != "claude":
        return
    skill_dir = tmp_path / "zettelkasten"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(text, encoding="utf-8")
    problems, reason = real_validators.check_claude(skill_dir)
    if reason:
        pytest.skip(reason)
    assert problems == []

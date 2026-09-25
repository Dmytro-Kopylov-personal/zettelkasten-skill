"""The renderer: composition, failure modes, and the CLI's exit codes."""

from __future__ import annotations

import pytest

import render

PLATFORMS = sorted(render.PLATFORMS)


def doc(frontmatter: str, body: str = "The idea, stated in one sentence.\n") -> str:
    return f"---\n{frontmatter.strip()}\n---\n\n{body}"


GOOD_FRONTMATTER = {
    "hermes": "name: zettelkasten\ndescription: A description.\nplatforms: [linux, macos, windows]",
    "claude": "name: zettelkasten\ndescription: A description.\nlicense: MIT",
    "copilot": "name: zettelkasten\ndescription: A description.",
}


# --- composition ------------------------------------------------------------------


@pytest.mark.parametrize("platform", PLATFORMS)
def test_render_is_deterministic(platform):
    assert render.render(platform) == render.render(platform)


@pytest.mark.parametrize("platform", PLATFORMS)
def test_render_starts_with_the_fence_at_byte_zero(platform):
    assert render.render(platform).startswith("---\n")


@pytest.mark.parametrize("platform", PLATFORMS)
def test_render_leaves_no_placeholder(platform):
    assert "{{" not in render.render(platform)


@pytest.mark.parametrize("platform", PLATFORMS)
def test_render_validates_clean(platform):
    assert render.validate(platform, render.render(platform)) == []


def test_unknown_platform_raises():
    with pytest.raises(render.RenderError, match="unknown platform"):
        render.render("cursor")


def test_missing_fragment_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(render, "FRAGMENTS", tmp_path)
    with pytest.raises(render.RenderError, match="missing fragment"):
        render.render("hermes")


def test_unfilled_placeholder_raises(monkeypatch, tmp_path):
    (tmp_path / "SKILL.template.md").write_text(
        "{{FRONTMATTER}}\n\n# Title\n\n{{TYPO}}\n", encoding="utf-8"
    )
    monkeypatch.setattr(render, "SRC", tmp_path)
    with pytest.raises(render.RenderError, match="unfilled placeholder"):
        render.render("hermes")


def test_template_must_still_contain_every_placeholder(monkeypatch, tmp_path):
    (tmp_path / "SKILL.template.md").write_text("{{FRONTMATTER}}\n\n# Title\n", encoding="utf-8")
    monkeypatch.setattr(render, "SRC", tmp_path)
    with pytest.raises(render.RenderError, match="ENVIRONMENT"):
        render.render("hermes")


# --- validation -------------------------------------------------------------------


def test_valid_documents_pass_every_platform():
    for platform in PLATFORMS:
        assert render.validate(platform, doc(GOOD_FRONTMATTER[platform])) == []


@pytest.mark.parametrize(
    "platform, frontmatter, expected",
    [
        # V1: the spec's own example. Hermes reads `platforms` as an OS gate, so an
        # agent name here hides the skill entirely and silently.
        ("hermes", "name: zettelkasten\ndescription: d\nplatforms: [copilot, hermes]", "OS gate"),
        ("hermes", "name: zettelkasten\ndescription: d", "'platforms'"),
        ("claude", "name: zettelkasten\ndescription: d\nversion: 1.0.0", "allowlist"),
        ("claude", "name: zettelkasten\ndescription: d\nauthor: someone", "allowlist"),
        ("copilot", "name: zettelkasten-md\ndescription: d", "directory name"),
        ("copilot", "name: zettelkasten\ndescription: d<script>", "'<'"),
        ("hermes", "name: Zettelkasten\ndescription: d\nplatforms: [linux]", "must match"),
        ("hermes", "name: zettelkasten\ndescription: " + "d" * 1025 + "\nplatforms: [linux]", "1024"),
        ("hermes", "description: d\nplatforms: [linux]", "no 'name'"),
        ("hermes", "name: zettelkasten\nplatforms: [linux]", "no 'description'"),
    ],
)
def test_validation_catches_each_rule(platform, frontmatter, expected):
    problems = render.validate(platform, doc(frontmatter))
    assert any(expected in problem for problem in problems), problems


def test_empty_body_is_rejected():
    assert "empty" in " ".join(render.validate("hermes", "---\nname: z\ndescription: d\n---\n\n  \n"))


def test_unclosed_frontmatter_is_rejected():
    assert render.validate("hermes", "---\nname: zettelkasten\ndescription: d\nbody\n")


def test_no_frontmatter_is_rejected():
    assert render.validate("hermes", "# Just a heading\n")


def test_long_name_is_rejected():
    problems = render.validate("claude", doc("name: " + "a" * 65 + "\ndescription: d"))
    assert any("64" in problem for problem in problems), problems


def test_copilot_body_line_cap_is_the_only_line_limit():
    body = "\n".join(f"line {i}" for i in range(render.COPILOT_MAX_BODY_LINES - 1))
    assert render.validate("copilot", doc(GOOD_FRONTMATTER["copilot"], body)) == []
    over = "\n".join(f"line {i}" for i in range(render.COPILOT_MAX_BODY_LINES + 1))
    assert any("500" in p for p in render.validate("copilot", doc(GOOD_FRONTMATTER["copilot"], over)))


# --- CLI --------------------------------------------------------------------------


def test_no_arguments_is_a_usage_error():
    assert render.main([]) == 2


def test_out_alone_is_a_target_not_a_usage_error(tmp_path):
    """Regression: `--out` was left out of the 'no target given' guard."""
    assert render.main(["--out", str(tmp_path)]) == 0
    for platform in PLATFORMS:
        assert (tmp_path / platform / "SKILL.md").is_file()


def test_out_with_a_single_platform_writes_only_that_one(tmp_path):
    assert render.main(["--platform", "claude", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "claude" / "SKILL.md").is_file()
    assert not (tmp_path / "hermes").exists()


def test_unknown_platform_is_a_usage_error():
    with pytest.raises(SystemExit) as excinfo:
        render.main(["--platform", "cursor"])
    assert excinfo.value.code == 2


def test_check_passes_against_the_committed_goldens(capsys):
    assert render.main(["--check"]) == 0
    assert capsys.readouterr().out.count("ok") == len(PLATFORMS)


def test_check_fails_loudly_on_a_tampered_golden(monkeypatch, tmp_path, capsys):
    for platform in PLATFORMS:
        text = render.render(platform)
        if platform == "copilot":
            text = text.replace("Zettelkasten Vault Maintainer", "Tampered")
        (tmp_path / f"{platform}.SKILL.md").write_text(text, encoding="utf-8")
    monkeypatch.setattr(render, "GOLDEN", tmp_path)

    assert render.main(["--check"]) == 1
    captured = capsys.readouterr()
    assert "Tampered" in captured.err
    assert "copilot" in captured.err


def test_check_fails_when_a_golden_is_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(render, "GOLDEN", tmp_path)
    assert render.main(["--check"]) == 1
    assert "no golden" in capsys.readouterr().err

"""The installer, through a fake home.

Two properties matter, and they pull in opposite directions. The install must be
**idempotent** — running it twice changes nothing, so it can be put in a script and run
without thinking — and it must be **unable to silently clobber** a file it did not write,
because the tree it writes into is one an OS-level backup also writes to, where a hand edit
looks exactly like a stale render.

So both halves are tested with the same instrument: the tree is hashed before and after. A
second install must leave the hash unchanged; a refused install must leave it unchanged too.

Every invocation goes through `--target-root` under `tmp_path`. The real home directory is
never read or written — a test that installed into `~/.hermes` would pass on the author's
machine and destroy a skills tree on the author's machine, which is the same place.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO

sys.path.insert(0, str(REPO / "src"))
import render  # noqa: E402

SCRIPT = REPO / "install.sh"
PLATFORMS = sorted(render.PLATFORMS)

#: The five platform roots, relative to the fake home.
ROOTS = {
    "hermes": ".hermes/skills/research",
    "claude": ".claude/skills",
    "copilot": ".copilot/skills",
}


def fake_home(tmp_path, *platforms: str) -> Path:
    home = tmp_path / "home"
    for platform in platforms or tuple(ROOTS):
        (home / ROOTS[platform]).mkdir(parents=True, exist_ok=True)
    return home


def run(
    home: Path,
    *args: str,
    expect: int | None = 0,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    result = subprocess.run(
        ["bash", str(SCRIPT), *args, "--target-root", str(home)],
        capture_output=True,
        text=True,
        cwd=str(REPO),
        env=env,
    )
    if expect is not None:
        assert result.returncode == expect, (
            f"exit {result.returncode}, expected {expect}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return result


def install(
    home: Path,
    *args: str,
    platform: str = "hermes",
    expect: int | None = 0,
) -> subprocess.CompletedProcess:
    return run(home, "--platform", platform, *args, expect=expect)


def tree(root: Path) -> dict[str, str]:
    """Every file under root, by digest — the whole-tree answer to "did anything change"."""
    if not root.exists():
        return {}
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def skill_dir(home: Path, platform: str = "hermes") -> Path:
    return home / ROOTS[platform] / "zettelkasten"


def state_dir(home: Path) -> Path:
    return home / ".local" / "state" / "zettelkasten-skill"


def manifest(home: Path, platform: str = "hermes") -> dict[str, str]:
    text = (state_dir(home) / f"manifest.{platform}.txt").read_text(encoding="utf-8")
    entries = {}
    for line in text.splitlines():
        digest, _, rel = line.partition("  ")
        assert len(digest) == 64, f"not a digest: {line!r}"
        entries[rel] = digest
    return entries


# --- what lands, and where ---------------------------------------------------------------


@pytest.mark.parametrize("platform", PLATFORMS)
def test_the_install_puts_the_whole_payload_where_the_platform_expects_it(tmp_path, platform):
    home = fake_home(tmp_path, platform)
    install(home, platform=platform)

    target = skill_dir(home, platform)
    assert (target / "SKILL.md").is_file()
    assert list((target / "references").glob("*.md"))
    assert list((target / "templates").glob("*.md"))
    assert list((target / "scripts").glob("*.py"))
    assert not list(target.rglob("__pycache__")), "a bytecode cache was shipped"


def test_the_installed_skill_is_the_current_render(tmp_path):
    """The seal between install and render: the file that lands is `render.render()`'s
    output, byte for byte. If this fails, an install can ship a skill no test has read."""
    home = fake_home(tmp_path)
    install(home)
    assert (skill_dir(home) / "SKILL.md").read_text(encoding="utf-8") == render.render("hermes")


def test_the_installed_payload_is_byte_identical_to_the_repo(tmp_path):
    """References, templates and scripts are copied, not regenerated, and a stale copy
    would be invisible to every other test in this suite."""
    home = fake_home(tmp_path)
    install(home)
    for part in ("references", "templates", "scripts"):
        for source in sorted((REPO / "skill" / part).rglob("*")):
            if source.is_file() and "__pycache__" not in source.parts:
                installed = skill_dir(home) / part / source.relative_to(REPO / "skill" / part)
                assert installed.read_bytes() == source.read_bytes(), f"{part}/{source.name}"


def test_the_manifest_records_a_digest_for_every_file_it_installed(tmp_path):
    home = fake_home(tmp_path)
    install(home)
    entries = manifest(home)
    installed = {
        str(path.relative_to(skill_dir(home))): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(skill_dir(home).rglob("*"))
        if path.is_file() and ".bak." not in path.name
    }
    assert entries == installed
    assert len(entries) == 11, sorted(entries)


def test_the_manifest_lives_outside_every_skills_tree(tmp_path):
    """Inside the skill directory it would be copied into a vault by the backup, and would
    then look exactly like a skill resource."""
    home = fake_home(tmp_path)
    install(home)
    for platform_root in ROOTS.values():
        assert not list((home / platform_root).rglob("*manifest*"))
    assert (state_dir(home) / "manifest.hermes.txt").is_file()


def test_the_installed_linter_actually_runs(tmp_path):
    """An end-to-end check of what was copied: the shipped script, invoked the way the skill
    invokes it, over a fixture vault. A payload that is present but broken passes every test
    above and fails the user on first use."""
    home = fake_home(tmp_path)
    install(home)
    linter = skill_dir(home) / "scripts" / "zettel_lint.py"
    result = subprocess.run(
        [sys.executable, "-I", str(linter), str(REPO / "tests" / "fixtures" / "vault_clean"),
         "--now", "2026-09-28"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# --- idempotency --------------------------------------------------------------------------


def test_a_second_install_changes_nothing_at_all(tmp_path):
    home = fake_home(tmp_path)
    install(home)
    before = tree(home)
    result = install(home)
    assert tree(home) == before
    assert "0 written" in result.stdout and "11 unchanged" in result.stdout


def test_a_second_install_writes_no_backup(tmp_path):
    home = fake_home(tmp_path)
    install(home)
    install(home)
    assert not list(skill_dir(home).glob("**/*.bak.*"))


# --- the file we did not write ------------------------------------------------------------


def test_a_hand_edited_file_is_backed_up_and_then_replaced(tmp_path):
    """The case that makes the installer safe to run over a tree someone has edited."""
    home = fake_home(tmp_path)
    install(home)
    edited = skill_dir(home) / "references" / "note-format.md"
    edited.write_text("a hand edit that must not vanish\n", encoding="utf-8")

    result = install(home)
    assert "backed up" in result.stdout
    backups = list((skill_dir(home) / "references").glob("note-format.md.bak.*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "a hand edit that must not vanish\n"
    assert edited.read_text(encoding="utf-8") == (
        REPO / "skill" / "references" / "note-format.md"
    ).read_text(encoding="utf-8")


def test_an_unmanaged_file_where_the_manifest_is_missing_stops_the_install(tmp_path):
    """Case 5. No manifest means no claim of ownership, so a differing file is someone
    else's and the whole install stops rather than overwriting one file and carrying on."""
    home = fake_home(tmp_path)
    target = skill_dir(home)
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("someone else's skill\n", encoding="utf-8")

    result = install(home, expect=4)
    assert "refusing to overwrite" in result.stderr
    assert "SKILL.md" in result.stderr
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "someone else's skill\n"
    assert tree(target) == {"SKILL.md": hashlib.sha256(b"someone else's skill\n").hexdigest()}
    assert not (state_dir(home) / "manifest.hermes.txt").exists(), (
        "a refused install must not leave a manifest claiming ownership"
    )


def test_a_file_the_manifest_does_not_list_stops_the_install(tmp_path):
    """The manifest exists, so ownership is known — and this file is not ours."""
    home = fake_home(tmp_path)
    install(home)
    (skill_dir(home) / "references" / "note-format.md").write_text("not ours\n", encoding="utf-8")
    (state_dir(home) / "manifest.hermes.txt").write_text(
        "\n".join(
            line
            for line in (state_dir(home) / "manifest.hermes.txt").read_text().splitlines()
            if "note-format" not in line
        )
        + "\n",
        encoding="utf-8",
    )

    result = install(home, expect=4)
    assert "references/note-format.md" in result.stderr
    assert (skill_dir(home) / "references" / "note-format.md").read_text() == "not ours\n"


def test_a_manifest_that_is_gone_is_adopted_when_the_files_still_match(tmp_path):
    """Case 4: the files prove ownership. Re-recording them is the whole repair."""
    home = fake_home(tmp_path)
    install(home)
    before = tree(skill_dir(home))
    (state_dir(home) / "manifest.hermes.txt").unlink()

    result = install(home)
    assert "adopted: 11 file(s)" in result.stdout
    assert tree(skill_dir(home)) == before
    assert manifest(home)


def test_force_does_not_override_a_refusal(tmp_path):
    """There is deliberately no escape hatch for case 5: the remedy is to move the file,
    which is a decision a person makes, not a flag that a script can carry."""
    home = fake_home(tmp_path)
    target = skill_dir(home)
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("someone else's\n", encoding="utf-8")
    install(home, "--force", expect=4)


# --- the paths that lead to the other exit codes -------------------------------------------


def test_a_missing_skills_root_exits_3_and_force_creates_it(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    result = install(home, platform="claude", expect=3)
    assert "does not exist" in result.stderr
    assert not skill_dir(home, "claude").exists()

    install(home, "--force", platform="claude")
    assert (skill_dir(home, "claude") / "SKILL.md").is_file()


def test_a_single_existing_root_is_detected_without_being_named(tmp_path):
    home = fake_home(tmp_path, "hermes")
    result = run(home, "--dry-run")
    assert "hermes" in result.stdout
    assert str(skill_dir(home, "hermes")) in result.stdout


def test_two_existing_roots_are_ambiguous_and_say_so(tmp_path):
    home = fake_home(tmp_path, "hermes", "claude")
    result = run(home, "--dry-run", expect=2)
    assert "several skills roots" in result.stderr
    assert "--platform" in result.stderr


def test_an_unknown_platform_is_a_usage_error(tmp_path):
    home = fake_home(tmp_path)
    result = run(home, "--platform", "obsidian", expect=2)
    assert "hermes, claude or copilot" in result.stderr


def test_project_root_only_applies_to_copilot(tmp_path):
    home = fake_home(tmp_path)
    result = run(home, "--platform", "hermes", "--project-root", str(tmp_path), expect=2)
    assert "only applies to --platform copilot" in result.stderr


def test_copilot_installs_into_a_project_tree_when_told_to(tmp_path):
    """The work-machine case: a repository-scoped skills directory rather than a personal
    one, which is what a corporate checkout needs."""
    home = fake_home(tmp_path, "copilot")
    project = tmp_path / "work-repo"
    project.mkdir()
    run(home, "--platform", "copilot", "--project-root", str(project), "--force")
    assert (project / ".github" / "skills" / "zettelkasten" / "SKILL.md").is_file()
    assert not (home / ".copilot" / "skills" / "zettelkasten" / "SKILL.md").exists()


def test_help_exits_zero_and_names_every_flag(tmp_path):
    home = fake_home(tmp_path)
    result = run(home, "--help")
    for flag in ("--platform", "--project-root", "--target-root", "--dry-run", "--force"):
        assert flag in result.stdout


def test_an_unknown_argument_is_a_usage_error(tmp_path):
    home = fake_home(tmp_path)
    assert "unknown argument" in run(home, "--frobnicate", expect=2).stderr


# --- the dry run ---------------------------------------------------------------------------


def test_a_dry_run_writes_nothing_including_the_manifest(tmp_path):
    """The dry run is how someone checks what an install would do to a tree they care
    about. A dry run that leaves a manifest behind has already changed the answer to the
    question it was asked."""
    home = fake_home(tmp_path)
    result = install(home, "--dry-run")
    assert "would write:   11" in result.stdout
    assert tree(home) == {}
    assert not state_dir(home).exists()


def test_a_dry_run_over_an_existing_install_reports_no_writes(tmp_path):
    home = fake_home(tmp_path)
    install(home)
    before = tree(home)
    result = install(home, "--dry-run")
    assert "would write:   0" in result.stdout
    assert "unchanged:     11" in result.stdout
    assert tree(home) == before


def test_a_dry_run_says_when_it_would_refuse(tmp_path):
    home = fake_home(tmp_path)
    target = skill_dir(home)
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("someone else's\n", encoding="utf-8")
    assert "refusing to overwrite" in install(home, "--dry-run", expect=4).stderr


# --- the home directory is not a test fixture ----------------------------------------------


def test_the_installer_does_not_consult_the_home_directory_when_told_not_to(tmp_path):
    """`--target-root` must rebase *everything*, not just the skills tree. So the install is
    run with a home directory that does not exist: if any path were still derived from
    `$HOME`, this would fail rather than quietly writing somewhere the test cannot see."""
    home = fake_home(tmp_path)
    poisoned = dict(os.environ, HOME="/nonexistent-home-for-this-test")
    result = run(home, "--platform", "hermes", env=poisoned)
    assert "0 written" not in result.stdout and "11 written" in result.stdout
    assert (skill_dir(home) / "SKILL.md").is_file()
    assert (state_dir(home) / "manifest.hermes.txt").is_file()
    assert not os.path.exists("/nonexistent-home-for-this-test")


def test_the_installer_is_executable_and_has_no_shell_syntax_errors():
    assert os.access(SCRIPT, os.X_OK), "install.sh is not executable"
    result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


# --- three places know where the skill lands ------------------------------------------------


def test_the_installer_roots_are_the_roots_this_module_uses():
    """`ROOTS` here, the `platform_root` cases in the script, and the path the Hermes
    environment fragment tells the agent to run — three copies of one fact. The first two
    are compared by the tests above only because they happened to agree; this says so."""
    text = SCRIPT.read_text(encoding="utf-8")
    for platform, root in ROOTS.items():
        assert f"/{root}" in text, f"install.sh does not install {platform} into {root}"


def test_the_hermes_fragment_runs_the_linter_where_the_installer_puts_it():
    """The fragment hardcodes the invocation, so it can drift from the installer. It is the
    one path in the shipped skill that is absolute, and a wrong one fails at the worst
    moment — when the agent is trying to check its own work.

    Asserted in two halves, because the fragment writes the path as
    `${HERMES_HOME:-$HOME/.hermes}` followed by the rest: the home it expands to must be the
    one the installer uses, and the suffix must be the one the payload is copied to.
    """
    fragment = (REPO / "src" / "fragments" / "environment.hermes.md").read_text(encoding="utf-8")
    assert "${HERMES_HOME:-$HOME/.hermes}" in fragment, (
        "the path is not expressed relative to the Hermes home, so it only works on one machine"
    )
    home, _, inside = ROOTS["hermes"].partition("/")
    assert home == ".hermes"
    suffix = f"/{inside}/zettelkasten/scripts/zettel_lint.py"
    assert suffix in fragment, f"the fragment does not point at {suffix}"
    assert "/Users/" not in fragment, "an absolute path from the author's machine was shipped"


def test_nothing_in_the_installer_writes_to_raw_or_permanent():
    """`raw/` is immutable and `permanent/` is the agent's to write, propose-first. The
    installer touches neither, and the check is textual so that it holds for the script as
    authored rather than for the paths one test happened to exercise."""
    text = SCRIPT.read_text(encoding="utf-8")
    for forbidden in ("raw/", "permanent/", "inbox/"):
        assert forbidden not in text, f"the installer mentions {forbidden}"


def test_the_tree_hash_would_notice_a_change(tmp_path):
    """Control for every "nothing changed" assertion above: if `tree()` returned a constant,
    all of them would pass forever."""
    home = fake_home(tmp_path)
    install(home)
    before = tree(skill_dir(home))
    (skill_dir(home) / "SKILL.md").write_text("different\n", encoding="utf-8")
    assert tree(skill_dir(home)) != before
    shutil.rmtree(skill_dir(home))
    assert tree(skill_dir(home)) == {}

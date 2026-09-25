"""Design invariants that hold no matter what the renderer does.

The denylist is the mechanical form of the decision "no tool names in the shared body".
It scans the *sources* — the template and the shipped `references/` and `templates/` —
so a leak is caught at authoring time with a line number, rather than discovered later in
a render.

The per-platform environment blocks are deliberately NOT scanned: naming the platform's
own tools is exactly their job, and a predicate that flagged them would be turned off
within a week. Prose that merely resembles a tool name ("read the file", "create a note")
must also survive, which is what the negative control pins down.
"""

from __future__ import annotations

import re

import pytest
from conftest import FIXTURES, REPO
from support import platform_rules

# Distinctive enough that they never occur in English prose, so they are flagged bare.
SNAKE_TOOL_NAMES = (
    "read_file",
    "write_file",
    "search_files",
    "patch_file",
    "list_files",
    "run_command",
    "execute_code",
    "web_extract",
    "web_search",
    "skill_view",
    "delegate_task",
    "todo_write",
)

# Short, common-word tool names: flagged only inside backticks. `patch`, `terminal` and
# `memory` are ordinary English words, and a bare-word predicate for them would fire on
# "open a terminal" — the false positive that gets a check like this disabled.
BACKTICKED_TOOL_NAMES = (
    "Read",
    "Write",
    "Edit",
    "Glob",
    "Grep",
    "Bash",
    "Task",
    "WebFetch",
    "WebSearch",
    "NotebookEdit",
    "view",
    "create",
    "str_replace",
    "terminal",
    "patch",
    "memory",
    "todo",
    "ls",
    "cat",
    "find",
    "grep",
)

# Claude Code substitutes these before the skill ever reaches another agent, so in a
# shared body they would arrive verbatim as literal noise. Both the bare and the braced
# spellings count: `${CLAUDE_SKILL_DIR}` is how they are actually written, and a check
# for the bare form alone misses it.
CLAUDE_ONLY_SUBSTITUTIONS = re.compile(r"\$\{?(CLAUDE_[A-Z_]+|ARGUMENTS)\}")
INLINE_BANG = re.compile(r"!`")

SHARED_SOURCES = (
    REPO / "src" / "SKILL.template.md",
    REPO / "skill" / "references",
    REPO / "skill" / "templates",
)


def shared_files() -> list:
    files = []
    for source in SHARED_SOURCES:
        if source.is_file():
            files.append(source)
        elif source.is_dir():
            files.extend(sorted(source.rglob("*.md")))
    return files


def violations(text: str) -> list[tuple[int, str, str]]:
    found = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for token in SNAKE_TOOL_NAMES:
            if re.search(rf"(?<![\w-]){re.escape(token)}(?![\w-])", line):
                found.append((lineno, "tool-name-snake", token))
        for token in BACKTICKED_TOOL_NAMES:
            if f"`{token}`" in line:
                found.append((lineno, "tool-name-backticked", token))
        substitution = CLAUDE_ONLY_SUBSTITUTIONS.search(line)
        if substitution:
            found.append((lineno, "claude-substitution", substitution.group(0)))
        if INLINE_BANG.search(line):
            found.append((lineno, "inline-bang", "!`"))
    return found


def test_the_shared_sources_exist():
    assert (REPO / "src" / "SKILL.template.md").is_file()
    assert shared_files(), "no shared sources found to scan"


def test_no_tool_names_in_the_shared_body():
    for path in shared_files():
        found = violations(path.read_text(encoding="utf-8"))
        assert not found, "\n".join(
            f"{path.relative_to(REPO)}:{line}: {kind}: {token!r}" for line, kind, token in found
        )


POSITIVE_CONTROL = (
    "Call `read_file`, then `Read` the note. Use ${CLAUDE_SKILL_DIR} and $ARGUMENTS. Run !`ls`.\n"
)
NEGATIVE_CONTROL = (
    "Read the source and write the note.\n"
    "The user edits the note before you create a note.\n"
    "Open a terminal and apply the patch; a patch of grass is not a memory of one.\n"
    "Search the vault, then edit the index and list the todos.\n"
)


def test_the_denylist_has_a_positive_control():
    kinds = {kind for _, kind, _ in violations(POSITIVE_CONTROL)}
    assert kinds == {
        "tool-name-snake",
        "tool-name-backticked",
        "claude-substitution",
        "inline-bang",
    }, kinds


def test_the_denylist_has_a_negative_control():
    assert violations(NEGATIVE_CONTROL) == []


def test_the_denylist_would_flag_a_platform_environment_block():
    """Control in the other direction.

    The env blocks name their own platform's tools, which is their job — but the same
    text in the shared body would be a leak, so the predicates must catch it there. Each
    fragment exercises a different predicate, which is why both are checked.
    """
    hermes = violations(
        (REPO / "src" / "fragments" / "environment.hermes.md").read_text(encoding="utf-8")
    )
    assert {"tool-name-snake", "tool-name-backticked"} <= {kind for _, kind, _ in hermes}

    claude = violations(
        (REPO / "src" / "fragments" / "environment.claude.md").read_text(encoding="utf-8")
    )
    assert "claude-substitution" in {kind for _, kind, _ in claude}


def test_hermes_platforms_is_an_os_gate_not_an_agent_gate():
    """V1: `platforms: [copilot, hermes]` hides the skill in Hermes, silently."""
    fragment = (REPO / "src" / "fragments" / "frontmatter.hermes.yaml").read_text(encoding="utf-8")
    doc = platform_rules.parse(fragment)
    declared = platform_rules.declared_platforms(doc)
    assert declared, "the Hermes fragment declares no platforms at all"
    assert declared <= {"linux", "macos", "windows"}, declared


def test_hermes_description_front_loads_the_trigger_verbs():
    """V2: Hermes shows `description[:57] + "..."` in the catalog, and nothing else."""
    fragment = (REPO / "src" / "fragments" / "frontmatter.hermes.yaml").read_text(encoding="utf-8")
    visible = platform_rules.description(platform_rules.parse(fragment))[:53].lower()
    for trigger in ("ingest", "query", "lint", "init", "zettelkasten"):
        assert trigger in visible, f"{trigger!r} is not in the visible head {visible!r}"


def test_the_description_is_a_single_sentence_trigger_list():
    """It is one line in YAML: a newline in it would break the fragment's frontmatter."""
    fragment = (REPO / "src" / "fragments" / "frontmatter.hermes.yaml").read_text(encoding="utf-8")
    doc = platform_rules.parse(fragment)
    assert "\n" not in platform_rules.description(doc)
    assert len(platform_rules.description(doc)) <= 1024


WRITE_PATTERNS = (
    (re.compile(r"""open\s*\([^)]*["'][wax]"""), "open() for writing"),
    (re.compile(r"\.write_text\(|\.write_bytes\("), "Path.write_text/write_bytes"),
    (re.compile(r"\bos\.(remove|unlink|rename|replace|makedirs|mkdir|chmod|truncate)\b"), "os mutation"),
    (re.compile(r"\bshutil\.(rmtree|move|copy|copyfile)\b"), "shutil mutation"),
    # Unqualified `.rename(`/`.replace(` are deliberately absent: `str.replace` is string
    # handling, and a predicate that flags it would be turned off within a week. The
    # runtime tree-hash test covers what this leaves out.
    (re.compile(r"\.(unlink|touch|mkdir|rmdir)\("), "Path mutation"),
    (re.compile(r"\b(mkstemp|mkdtemp|NamedTemporaryFile)\b"), "temporary file creation"),
)


def write_violations(text: str) -> list[tuple[int, str]]:
    found = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern, label in WRITE_PATTERNS:
            if pattern.search(line):
                found.append((lineno, label))
    return found


def bundled_scripts() -> list:
    scripts = REPO / "skill" / "scripts"
    return sorted(scripts.glob("*.py")) if scripts.is_dir() else []


def test_bundled_scripts_exist():
    assert bundled_scripts(), "no bundled scripts found to check"


def test_no_bundled_script_has_a_write_path():
    """The script verifies; the agent writes. There is no --fix, on purpose."""
    for path in bundled_scripts():
        found = write_violations(path.read_text(encoding="utf-8"))
        assert not found, "\n".join(
            f"{path.relative_to(REPO)}:{line}: {label}" for line, label in found
        )


def test_the_write_path_check_has_a_positive_control():
    control = 'p = Path("/tmp/x")\np.write_text("hi")\nopen("/tmp/y", "w").write("z")\np.unlink()\n'
    labels = {label for _, label in write_violations(control)}
    assert len(labels) >= 3, labels


def test_the_write_path_check_has_a_negative_control():
    """Reading, printing and string manipulation must not trip it."""
    control = (
        "text = path.read_text()\n"
        'sys.stdout.write("ok\\n")\n'
        "print(json.dumps(data))\n"
        "cleaned = text.replace('a', 'b')\n"
        "root.mkdir  # bound, not called\n"
        "os.path.join(root, name)\n"
    )
    assert write_violations(control) == []


def test_no_fixture_is_named_skill_md():
    """Hermes walks the skills tree recursively; a fixture SKILL.md would register."""
    if not FIXTURES.exists():
        pytest.skip("no fixtures yet")
    offenders = [p for p in FIXTURES.rglob("SKILL.md")]
    assert not offenders, f"fixtures must not contain SKILL.md: {offenders}"

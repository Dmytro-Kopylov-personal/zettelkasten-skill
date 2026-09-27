#!/usr/bin/env python3
"""Render a per-platform SKILL.md from the shared template and platform fragments.

The repo keeps one capability-language body and three thin platform fragments. This
script is the only thing that combines them, so a platform-specific detail can never
leak into the shared body by accident, and an unfilled placeholder is a loud failure
rather than a silently truncated file.

Stdlib only, on purpose: it runs on machines where pytest and PyYAML are absent.

    python3 src/render.py --list
    python3 src/render.py --platform hermes --out dist
    python3 src/render.py --check          # CI: diff every render against tests/golden/

Exit codes: 0 ok, 1 render or validation failure, 2 usage error.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
FRAGMENTS = SRC / "fragments"
GOLDEN = REPO / "tests" / "golden"

PLACEHOLDERS = ("FRONTMATTER", "ENVIRONMENT")

# Hermes reads `platforms:` as an OS gate (PLATFORM_MAP in agent/skill_utils.py), not as
# an agent gate. A value like [copilot, hermes] silently hides the skill from every
# platform while looking perfectly reasonable. Anything outside this set is an error.
KNOWN_OSES = frozenset({"linux", "macos", "windows"})

# Anthropic's skill spec allowlist. `quick_validate.py` (installed locally by
# skill-creator) treats any other key as a hard failure, so the Claude render must stay
# inside it even though Claude Code itself ignores unknown keys silently.
CLAUDE_ALLOWED_KEYS = frozenset(
    {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
)

MAX_DESCRIPTION_CHARS = 1024

# Copilot's docs state no body limit; this cap is third-party `awesome-copilot`
# guidance, kept as a budget with wide margin rather than a platform rule. The
# shared body sits far below it, and no load failure from exceeding it is on record.
COPILOT_MAX_BODY_LINES = 500

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class RenderError(Exception):
    """A fragment is missing or a placeholder was left unfilled."""


@dataclass(frozen=True)
class PlatformSpec:
    name: str
    frontmatter: str
    environment: str

    @property
    def frontmatter_path(self) -> Path:
        return FRAGMENTS / self.frontmatter

    @property
    def environment_path(self) -> Path:
        return FRAGMENTS / self.environment


PLATFORMS: dict[str, PlatformSpec] = {
    "hermes": PlatformSpec("hermes", "frontmatter.hermes.yaml", "environment.hermes.md"),
    "claude": PlatformSpec("claude", "frontmatter.claude.yaml", "environment.claude.md"),
    "copilot": PlatformSpec("copilot", "frontmatter.copilot.yaml", "environment.copilot.md"),
}


def _display(path: Path) -> str:
    """Repo-relative when possible, absolute otherwise. Never raises in a diagnostic."""
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def _read(path: Path) -> str:
    if not path.is_file():
        raise RenderError(f"missing fragment: {_display(path)}")
    return path.read_text(encoding="utf-8")


def render(platform: str) -> str:
    """Compose the SKILL.md for one platform. Pure: no timestamps, no environment."""
    if platform not in PLATFORMS:
        raise RenderError(f"unknown platform {platform!r}; known: {', '.join(PLATFORMS)}")
    spec = PLATFORMS[platform]

    template = _read(SRC / "SKILL.template.md")
    frontmatter = _read(spec.frontmatter_path).strip("\n")
    environment = _read(spec.environment_path).strip("\n")

    out = template.replace("{{FRONTMATTER}}", frontmatter, 1)
    out = out.replace("{{ENVIRONMENT}}", environment, 1)

    leftover = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if leftover:
        raise RenderError(f"unfilled placeholder(s) in {platform}: {', '.join(sorted(set(leftover)))}")
    for placeholder in PLACEHOLDERS:
        if f"{{{{{placeholder}}}}}" not in template:
            raise RenderError(f"template no longer contains {{{{{placeholder}}}}}")

    return out.rstrip("\n") + "\n"


def split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter text without fences, body). Raises on malformed fences."""
    if not text.startswith("---\n"):
        raise RenderError("SKILL.md must start with '---' at byte 0")
    match = re.search(r"\n---\s*\n", text[3:])
    if not match:
        raise RenderError("frontmatter is not closed with a '---' line")
    end = match.end() + 3
    return text[3 : match.start() + 3], text[end:]


def _frontmatter_keys(frontmatter: str) -> list[str]:
    return re.findall(r"^([A-Za-z][A-Za-z0-9_-]*):", frontmatter, flags=re.MULTILINE)


def _scalar(frontmatter: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:[ \t]*(.*)$", frontmatter, flags=re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1]
    return value


def validate(platform: str, text: str) -> list[str]:
    """Platform-generic conformance rules. Empty list means loadable.

    Fail-closed by design: `install.sh` refuses to deploy a render that does not pass.
    Design-specific invariants (trigger wording, the shared-body equivalence) live in
    tests/, not here.
    """
    problems: list[str] = []
    try:
        frontmatter, body = split_frontmatter(text)
    except RenderError as exc:
        return [str(exc)]

    if not body.strip():
        problems.append("body is empty after the frontmatter")

    name = _scalar(frontmatter, "name")
    if not name:
        problems.append("frontmatter has no 'name'")
    elif not NAME_RE.match(name):
        problems.append(f"name {name!r} must match {NAME_RE.pattern}")
    elif len(name) > 64:
        problems.append(f"name is {len(name)} chars (max 64)")

    description = _scalar(frontmatter, "description")
    if not description:
        problems.append("frontmatter has no 'description'")
    elif len(description) > MAX_DESCRIPTION_CHARS:
        problems.append(f"description is {len(description)} chars (max {MAX_DESCRIPTION_CHARS})")

    if platform == "hermes":
        raw = _scalar(frontmatter, "platforms")
        if raw is None:
            problems.append("hermes render must declare 'platforms'")
        else:
            declared = {p.strip() for p in raw.strip("[]").split(",") if p.strip()}
            unknown = declared - KNOWN_OSES
            if unknown:
                problems.append(
                    "'platforms' is an OS gate in Hermes, not an agent gate; "
                    f"unexpected value(s) {sorted(unknown)} would hide the skill entirely. "
                    f"Expected a subset of {sorted(KNOWN_OSES)}."
                )

    if platform == "claude":
        extra = [k for k in _frontmatter_keys(frontmatter) if k not in CLAUDE_ALLOWED_KEYS]
        if extra:
            problems.append(
                f"keys outside Anthropic's allowlist (quick_validate fails on these): {sorted(extra)}"
            )

    # Anthropic's quick_validate.py rejects angle brackets in a description, and a test
    # asserts it. No Copilot document states a rule either way; the same restriction covers
    # both so one description serves every platform. Hermes does not care.
    if platform in ("claude", "copilot") and description and any(c in description for c in "<>"):
        problems.append("description must not contain '<' or '>'")

    if platform == "copilot":
        if name and name != "zettelkasten":
            problems.append(
                f"Copilot resolves the skill by directory name, so 'name' must equal "
                f"'zettelkasten'; got {name!r}"
            )
        body_lines = len(body.splitlines())
        if body_lines > COPILOT_MAX_BODY_LINES:
            problems.append(
                f"body is {body_lines} lines (awesome-copilot guidance caps this at "
                f"{COPILOT_MAX_BODY_LINES}, though VS Code documents no limit)"
            )

    return problems


def _describe(platform: str, text: str) -> str:
    _, body = split_frontmatter(text)
    return (
        f"{platform:8s} {len(text):6d} chars  "
        f"{len(text.splitlines()):4d} lines  "
        f"body {len(body.splitlines()):4d} lines"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--platform", choices=sorted(PLATFORMS), help="render one platform")
    parser.add_argument("--out", type=Path, help="write renders to this directory")
    parser.add_argument("--check", action="store_true", help="diff renders against tests/golden/")
    parser.add_argument(
        "--update-goldens",
        action="store_true",
        help="adopt the current renders as the golden oracle (then read `git diff tests/golden/`)",
    )
    parser.add_argument("--list", action="store_true", help="list platforms with sizes")
    args = parser.parse_args(argv)

    if not (args.platform or args.check or args.list or args.out or args.update_goldens):
        parser.print_help()
        return 2

    targets = [args.platform] if args.platform else sorted(PLATFORMS)
    failed = False

    for platform in targets:
        try:
            text = render(platform)
        except RenderError as exc:
            print(f"render failed for {platform}: {exc}", file=sys.stderr)
            return 1

        problems = validate(platform, text)
        if problems:
            failed = True
            print(f"{platform}: FAILED validation", file=sys.stderr)
            for problem in problems:
                print(f"  - {problem}", file=sys.stderr)
            continue

        if args.list:
            print(_describe(platform, text))

        if args.out:
            args.out.mkdir(parents=True, exist_ok=True)
            destination = args.out / platform / "SKILL.md"
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text, encoding="utf-8")
            print(f"wrote {destination}")

        if args.update_goldens:
            golden = GOLDEN / f"{platform}.SKILL.md"
            golden.parent.mkdir(parents=True, exist_ok=True)
            before = golden.read_text(encoding="utf-8") if golden.is_file() else None
            golden.write_text(text, encoding="utf-8")
            state = "unchanged" if before == text else "updated"
            print(f"{platform}: {state} ({_display(golden)})")

        if args.check:
            golden = GOLDEN / f"{platform}.SKILL.md"
            if not golden.is_file():
                print(f"{platform}: no golden at {_display(golden)}", file=sys.stderr)
                failed = True
                continue
            expected = golden.read_text(encoding="utf-8")
            if expected == text:
                print(f"{platform}: ok")
            else:
                failed = True
                diff = difflib.unified_diff(
                    expected.splitlines(keepends=True),
                    text.splitlines(keepends=True),
                    fromfile=f"tests/golden/{platform}.SKILL.md",
                    tofile=f"render({platform})",
                )
                sys.stderr.writelines(diff)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

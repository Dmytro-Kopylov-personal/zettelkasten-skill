"""Platform conformance rules, implemented independently of src/render.py.

This module deliberately does not import the renderer. It exists so that two separate
implementations can be run over the same corpus: agreement between them is what makes
the renderer's validation trustworthy, the same way a hand-rolled YAML subset is
trusted only because PyYAML is run beside it.

Where the two disagree on some document, one of them has a bug, and the differential
test says so instead of letting a single implementation quietly be both the ruler and
the thing being measured.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

KNOWN_OSES = {"linux", "macos", "windows"}
CLAUDE_ALLOWED_KEYS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
    "compatibility",
}
MAX_NAME_CHARS = 64
MAX_DESCRIPTION_CHARS = 1024
MAX_HERMES_TOTAL_CHARS = 100_000
# Third-party (awesome-copilot) guidance; VS Code's own docs state no body limit.
COPILOT_MAX_BODY_LINES = 500

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class RuleError(Exception):
    pass


@dataclass(frozen=True)
class Document:
    frontmatter: dict[str, str]
    keys: list[str]
    body: str


def parse(text: str) -> Document:
    """Line-based frontmatter reader. Deliberately not the renderer's implementation."""
    if not text.startswith("---\n"):
        raise RuleError("does not start with '---' at byte 0")

    lines = text.split("\n")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            header, body = lines[1:index], "\n".join(lines[index + 1 :])
            break
    else:
        raise RuleError("frontmatter fence is never closed")

    fields: dict[str, str] = {}
    keys: list[str] = []
    for line in header:
        match = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):(.*)$", line)
        if match:
            keys.append(match.group(1))
            fields[match.group(1)] = match.group(2).strip()
    return Document(frontmatter=fields, keys=keys, body=body)


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def description(doc: Document) -> str:
    return _unquote(doc.frontmatter.get("description", ""))


def declared_platforms(doc: Document) -> set[str]:
    raw = doc.frontmatter.get("platforms", "")
    return {item.strip() for item in raw.strip("[]").split(",") if item.strip()}


def check(platform: str, text: str) -> list[str]:
    """Return a list of problems. Empty means loadable on that platform."""
    try:
        doc = parse(text)
    except RuleError as exc:
        return [str(exc)]

    problems: list[str] = []
    name = _unquote(doc.frontmatter.get("name", ""))
    desc = description(doc)

    if not name:
        problems.append("no name")
    elif not NAME_RE.match(name) or len(name) > MAX_NAME_CHARS:
        problems.append(f"name {name!r} is not a valid skill name")
    if not desc:
        problems.append("no description")
    elif len(desc) > MAX_DESCRIPTION_CHARS:
        problems.append(f"description {len(desc)} chars")
    if not doc.body.strip():
        problems.append("empty body")

    if platform == "hermes":
        if len(text) > MAX_HERMES_TOTAL_CHARS:
            problems.append("over 100k chars")
        if "platforms" not in doc.frontmatter:
            problems.append("no platforms declaration")
        elif not declared_platforms(doc) <= KNOWN_OSES:
            problems.append("platforms is an OS gate; non-OS value present")

    if platform == "claude":
        unexpected = [key for key in doc.keys if key not in CLAUDE_ALLOWED_KEYS]
        if unexpected:
            problems.append(f"keys outside Anthropic allowlist: {unexpected}")
        if "<" in desc or ">" in desc:
            problems.append("description contains angle brackets")

    if platform == "copilot":
        if name and name != "zettelkasten":
            problems.append("name does not match the skill directory")
        if "<" in desc or ">" in desc:
            problems.append("description contains angle brackets")
        if len(doc.body.splitlines()) > COPILOT_MAX_BODY_LINES:
            problems.append("body over 500 lines")

    return problems

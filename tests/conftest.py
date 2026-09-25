"""Make the renderer importable from tests without an installed package."""

import re
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
REPO = TESTS.parent

for path in (REPO / "src", TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

GOLDEN = TESTS / "golden"
FIXTURES = TESTS / "fixtures"

# The shared body is the template minus two seams: the frontmatter, and the environment
# block, which is a `##`-level section and may legitimately differ per platform.
ENVIRONMENT_HEADING = re.compile(r"^## Environment \(.*?\)", flags=re.MULTILINE)


def strip_seams(text: str) -> str:
    """Return the part of a rendered SKILL.md that must be identical on every platform."""
    if not text.startswith("---\n"):
        raise AssertionError("rendered SKILL.md does not start with '---' at byte 0")
    closing = re.search(r"\n---\s*\n", text[3:])
    if not closing:
        raise AssertionError("rendered SKILL.md has no closing frontmatter fence")
    body = text[3 + closing.end() :]

    match = ENVIRONMENT_HEADING.search(body)
    if not match:
        raise AssertionError("rendered SKILL.md has no '## Environment (...)' section")
    tail = body[match.end() :]
    next_heading = re.search(r"^## ", tail, flags=re.MULTILINE)
    if not next_heading:
        raise AssertionError("the environment section is not followed by another '##' section")
    return (body[: match.start()] + tail[next_heading.start() :]).strip()

#!/usr/bin/env python3
"""Lint a Zettelkasten vault: structural errors, decay, and advisory findings.

Read-only, single file, standard library only. There is no --fix and no code path in
this file that opens anything for writing: the script verifies, the agent writes.

    python3 zettel_lint.py <vault> --json
    python3 zettel_lint.py <vault> --fail-on warn
    python3 zettel_lint.py hash <file>          # sha256 over the body bytes

Exit codes: 0 clean at --fail-on, 1 findings, 2 usage or vault error.

The frontmatter parser is a hand-rolled YAML subset. It is deliberately strict: a
document it cannot parse is reported as a parse failure and excluded from every check
that depends on frontmatter, never silently treated as empty. Hermes' own parser falls
back to splitting on ':', which makes every frontmatter check pass vacuously; that is
the failure this parser exists to avoid.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA_VERSION = "1"

# ---------------------------------------------------------------------------
# YAML subset
# ---------------------------------------------------------------------------

# Implicit typing follows YAML 1.1's core schema, whose resolution rules are published
# in PyYAML's resolver.py. They are restated here as data rather than imported, so this
# file keeps zero third-party imports; tests/test_yaml_subset.py runs the real
# yaml.safe_load beside it and fails on any divergence.
NULL_VALUES = frozenset({"", "~", "null", "Null", "NULL"})
TRUE_VALUES = frozenset({"true", "True", "TRUE", "yes", "Yes", "YES", "on", "On", "ON"})
FALSE_VALUES = frozenset({"false", "False", "FALSE", "no", "No", "NO", "off", "Off", "OFF"})

INT_RE = re.compile(
    r"^(?:[-+]?0b[0-1_]+"
    r"|[-+]?0[0-7_]+"
    r"|[-+]?(?:0|[1-9][0-9_]*)"
    r"|[-+]?0x[0-9a-fA-F_]+"
    r"|[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+)$"
)
FLOAT_RE = re.compile(
    r"^(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?"
    r"|\.[0-9_]+(?:[eE][-+][0-9]+)?"
    r"|[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*"
    r"|[-+]?\.(?:inf|Inf|INF)"
    r"|\.(?:nan|NaN|NAN))$"
)
DATE_RE = re.compile(r"^(\d{4})-(\d\d?)-(\d\d?)$")
DATETIME_RE = re.compile(
    r"^(\d{4})-(\d\d?)-(\d\d?)(?:[Tt]|[ \t]+)(\d\d?):(\d\d):(\d\d)"
    r"(?:\.(\d*))?(?:[ \t]*(Z|[-+]\d\d?(?::\d\d)?))?$"
)

UNSUPPORTED_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r":\s*[&*]\S"), "anchors and aliases are not supported"),
    (re.compile(r":\s*[|>]\s*$"), "block scalars are not supported"),
    (re.compile(r":\s*\{"), "flow mappings are not supported"),
    (re.compile(r"^-\s*\{"), "flow mappings are not supported"),
)


class YamlSubsetError(Exception):
    """A construct outside the supported subset, or malformed YAML."""

    def __init__(self, message: str, line: int):
        super().__init__(message)
        self.message = message
        self.line = line


def _strip_comment(value: str) -> str:
    """Remove a trailing comment. A '#' only starts one after whitespace."""
    quote: str | None = None
    for index, char in enumerate(value):
        if quote:
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char == "#" and index > 0 and value[index - 1] in " \t":
            return value[:index].rstrip()
    return value.rstrip()


def _unquote(value: str, line: int) -> tuple[str, bool]:
    """Return (text, was_quoted)."""
    if not value or value[0] not in "'\"":
        return value, False
    quote = value[0]
    if len(value) < 2 or value[-1] != quote:
        raise YamlSubsetError(
            "unclosed quote (multi-line quoted scalars are not supported)", line
        )
    inner = value[1:-1]
    if quote == "'":
        return inner.replace("''", "'"), True
    if re.search(r"\\(?![0abtnvfre \"\\/N_LPxuU])", inner):
        raise YamlSubsetError("unsupported escape sequence in a double-quoted scalar", line)
    escapes = {"\\n": "\n", "\\t": "\t", "\\r": "\r", "\\\\": "\\", '\\"': '"', "\\0": "\0"}
    for escape, replacement in escapes.items():
        inner = inner.replace(escape, replacement)
    return inner, True


def _resolve_scalar(text: str) -> object:
    """Implicit typing for a plain (unquoted) scalar."""
    if text in NULL_VALUES:
        return None
    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False
    if INT_RE.match(text):
        body = text.replace("_", "")
        sign = -1 if body.startswith("-") else 1
        digits = body.lstrip("+-")
        if ":" in digits:
            total = 0
            for part in digits.split(":"):
                total = total * 60 + int(part)
            return sign * total
        if digits.startswith("0b"):
            return sign * int(digits[2:], 2)
        if digits.startswith("0x"):
            return sign * int(digits[2:], 16)
        if digits.startswith("0") and len(digits) > 1:
            return sign * int(digits[1:], 8)
        return sign * int(digits)
    if FLOAT_RE.match(text):
        body = text.replace("_", "")
        lowered = body.lower()
        if lowered.endswith(".inf"):
            return float("-inf") if lowered.startswith("-") else float("inf")
        if lowered.endswith(".nan"):
            return float("nan")
        if ":" in body:
            sign = -1 if body.startswith("-") else 1
            whole, _, fraction = body.lstrip("+-").partition(".")
            total = 0
            for part in whole.split(":"):
                total = total * 60 + int(part)
            return sign * (total + float(f"0.{fraction}"))
        return float(body)
    match = DATETIME_RE.match(text)
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        hour, minute, second = int(match.group(4)), int(match.group(5)), int(match.group(6))
        micro = int((match.group(7) or "0").ljust(6, "0")[:6])
        tz = match.group(8)
        if tz:
            if tz == "Z":
                zone = dt.timezone.utc
            else:
                sign = -1 if tz[0] == "-" else 1
                parts = tz[1:].split(":")
                offset = dt.timedelta(hours=int(parts[0]), minutes=int(parts[1]) if len(parts) > 1 else 0)
                zone = dt.timezone(sign * offset)
            return dt.datetime(year, month, day, hour, minute, second, micro, zone)
        return dt.datetime(year, month, day, hour, minute, second, micro)
    match = DATE_RE.match(text)
    if match:
        return dt.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return text


def parse_scalar(raw: str, line: int) -> object:
    stripped = _strip_comment(raw).strip()
    text, quoted = _unquote(stripped, line)
    if quoted:
        return text
    if ": " in text or text.endswith(":"):
        raise YamlSubsetError(
            "':' inside an unquoted scalar is ambiguous; quote the value", line
        )
    return _resolve_scalar(text)


def _split_flow_list(inner: str, line: int) -> list[str]:
    items: list[str] = []
    current: list[str] = []
    quote: str | None = None
    for char in inner:
        if quote:
            current.append(char)
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
            current.append(char)
        elif char == ",":
            items.append("".join(current))
            current = []
        else:
            current.append(char)
    if quote:
        raise YamlSubsetError("unclosed quote in a flow list", line)
    tail = "".join(current)
    if tail.strip() or items:
        items.append(tail)
    return [item for item in (item.strip() for item in items) if item != ""]


def _strip_closing_flow(inner: str, line: int) -> str:
    if not inner.rstrip().endswith("]"):
        raise YamlSubsetError("a flow list must close with ']' on the same line", line)
    return inner.rstrip()[:-1]


def _check_line(line_text: str, lineno: int, raw: str) -> None:
    indentation = raw[: len(raw) - len(raw.lstrip())]
    if "\t" in indentation:
        raise YamlSubsetError("tabs are not allowed in indentation", lineno)
    if "\t" in raw:
        raise YamlSubsetError("tab characters are not supported", lineno)
    for pattern, message in UNSUPPORTED_PATTERNS:
        if pattern.search(line_text):
            raise YamlSubsetError(message, lineno)


def _split_key(line_text: str, lineno: int) -> tuple[str, str]:
    if ":" not in line_text:
        raise YamlSubsetError("expected 'key: value'", lineno)
    key, _, value = line_text.partition(":")
    key = key.strip()
    if not key:
        raise YamlSubsetError("empty key", lineno)
    if key[0] in "&*":
        raise YamlSubsetError("anchors and aliases are not supported", lineno)
    return key, value.strip()


@dataclass
class _Line:
    lineno: int
    indent: int
    text: str


def _significant(lines: list[str]) -> list[_Line]:
    out: list[_Line] = []
    for lineno, raw in enumerate(lines, start=1):
        if "﻿" in raw:
            raise YamlSubsetError("a byte-order mark is not supported", lineno)
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        body = _strip_comment(raw)
        if not body.strip():
            continue
        _check_line(body.strip(), lineno, raw)
        out.append(_Line(lineno, len(raw) - len(raw.lstrip()), body.strip()))
    return out


def _parse_list(
    items: list[_Line], index: int, indent: int, depth: int
) -> tuple[list[object], int]:
    result: list[object] = []
    while index < len(items):
        current = items[index]
        if current.indent < indent:
            break
        if current.indent > indent:
            raise YamlSubsetError("unexpected indentation in a block list", current.lineno)
        if not current.text.startswith("-"):
            break
        rest = current.text[1:].strip()
        index += 1
        if not rest:
            # A bare '-' introduces a nested block; one level only.
            if index < len(items) and items[index].indent > indent:
                if items[index].text.startswith("-"):
                    nested, index = _parse_list(items, index, items[index].indent, depth + 1)
                    result.append(nested)
                    continue
                raise YamlSubsetError(
                    "nested mappings are not supported at this depth", current.lineno
                )
            result.append(None)
            continue
        if ":" in rest and not rest.startswith(("'", '"', "[")):
            key, value = _split_key(rest, current.lineno)
            entry: dict[str, object] = {}
            if value:
                entry[key] = parse_scalar(value, current.lineno)
            elif index < len(items) and items[index].indent > indent:
                raise YamlSubsetError(
                    "nested mappings are not supported at this depth", current.lineno
                )
            else:
                entry[key] = None
            # Continuation lines of the same mapping, indented past the dash.
            while index < len(items) and items[index].indent > indent:
                follower = items[index]
                if follower.text.startswith("-"):
                    break
                follower_key, follower_value = _split_key(follower.text, follower.lineno)
                if follower_key in entry:
                    raise YamlSubsetError(
                        f"duplicate key {follower_key!r} in a list entry", follower.lineno
                    )
                if not follower_value:
                    raise YamlSubsetError(
                        "nested mappings are not supported at this depth", follower.lineno
                    )
                entry[follower_key] = parse_scalar(follower_value, follower.lineno)
                index += 1
            result.append(entry)
            continue
        if rest.startswith("["):
            result.append(
                [parse_scalar(item, current.lineno) for item in _split_flow_list(_strip_closing_flow(rest[1:], current.lineno), current.lineno)]
            )
            continue
        result.append(parse_scalar(rest, current.lineno))
    return result, index


def parse_yaml_subset(text: str) -> tuple[dict | None, str | None, int | None]:
    """Parse the frontmatter subset.

    Returns (data, error, line). On failure data is None and must not be treated as an
    empty mapping: callers exclude the document from every dependent check instead.

    `line` is 1-based within `text` — this function is handed a frontmatter block, not a
    file. Loaders translate to file lines once, in `split_with_lines`.
    """
    try:
        lines = _significant(text.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
        document: dict[str, object] = {}
        index = 0
        while index < len(lines):
            current = lines[index]
            if current.indent != 0:
                raise YamlSubsetError("unexpected indentation at the top level", current.lineno)
            if current.text.startswith("-"):
                raise YamlSubsetError("the frontmatter must be a mapping, not a list", current.lineno)
            key, value = _split_key(current.text, current.lineno)
            if key in document:
                raise YamlSubsetError(f"duplicate key {key!r}", current.lineno)
            index += 1

            if value.startswith("["):
                document[key] = [
                    parse_scalar(item, current.lineno)
                    for item in _split_flow_list(_strip_closing_flow(value[1:], current.lineno), current.lineno)
                ]
                continue
            if value:
                document[key] = parse_scalar(value, current.lineno)
                continue
            if index < len(lines) and lines[index].indent > 0:
                if not lines[index].text.startswith("-"):
                    raise YamlSubsetError(
                        "nested mappings are not supported at this depth", lines[index].lineno
                    )
                document[key], index = _parse_list(lines, index, lines[index].indent, 1)
                continue
            document[key] = None
        return document, None, None
    except YamlSubsetError as exc:
        return None, exc.message, exc.line


# ---------------------------------------------------------------------------
# Bytes, frontmatter splits, and hashing
# ---------------------------------------------------------------------------

FRONTMATTER_OPEN = b"---\n"
FRONTMATTER_CLOSE = b"\n---\n"


def split_frontmatter_bytes(data: bytes) -> tuple[bytes, bytes]:
    """Split a file into (frontmatter bytes without fences, body bytes).

    Byte-exact: digests are computed over these slices, so a decode/re-encode round trip
    would change every hash. A file that does not open with a fence has no frontmatter,
    and its body is the whole file — a mid-document '---' horizontal rule must not be
    mistaken for a closing fence.
    """
    if not data.startswith(FRONTMATTER_OPEN):
        return b"", data
    end = data.find(FRONTMATTER_CLOSE, len(FRONTMATTER_OPEN))
    if end == -1:
        return b"", data
    return data[len(FRONTMATTER_OPEN) : end], data[end + len(FRONTMATTER_CLOSE) :]


def body_digest(data: bytes) -> str:
    """sha256 over the body bytes, so the digest can be stored in the frontmatter."""
    _, body = split_frontmatter_bytes(data)
    return hashlib.sha256(body).hexdigest()


def _line_after(prefix: bytes) -> int:
    """1-based file line number of the character immediately after `prefix`."""
    return prefix.count(b"\n") + 1


def split_with_lines(data: bytes) -> tuple[bytes, bytes, int, int]:
    """(frontmatter, body, frontmatter_start_line, body_start_line), all 1-based.

    `parse_yaml_subset` and the extractors number lines relative to the text they are
    handed, which is what makes them testable in isolation. Findings have to point at
    real lines in the real file, so every offset is resolved once, here.
    """
    frontmatter, body = split_frontmatter_bytes(data)
    if not frontmatter:
        return b"", body, 1, 1
    body_start = _line_after(data[: len(data) - len(body)])
    return frontmatter, body, 2, body_start


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

WIKILINK_RE = re.compile(r"\[\[([^\[\]]+)\]\]")
PROVENANCE_RE = re.compile(r"\^\[([^\]]+)\]")
FENCE_RE = re.compile(r"^\s{0,3}(```|~~~)")


def strip_code(text: str) -> str:
    """Blank out fenced blocks and inline code, preserving every line and column.

    This is a correctness requirement, not a nicety: `np.array([[500, 375]])` inside a
    fence is not a wikilink, and prose *describing* wikilinks writes `[[wikilinks]]`
    inside backticks.
    """
    out: list[str] = []
    fence: str | None = None
    for line in text.split("\n"):
        match = FENCE_RE.match(line)
        if fence:
            out.append(" " * len(line))
            if match and match.group(1) == fence:
                fence = None
            continue
        if match:
            fence = match.group(1)
            out.append(" " * len(line))
            continue
        out.append(_blank_inline_code(line))
    return "\n".join(out)


def _blank_inline_code(line: str) -> str:
    chars = list(line)
    index = 0
    while index < len(chars):
        if chars[index] != "`":
            index += 1
            continue
        run = 1
        while index + run < len(chars) and chars[index + run] == "`":
            run += 1
        closing = line.find("`" * run, index + run)
        if closing == -1:
            break
        for position in range(index, closing + run):
            chars[position] = " "
        index = closing + run
    return "".join(chars)


def find_wikilinks(text: str) -> list[tuple[str, int]]:
    """(target, line) for every wikilink outside code. Fences and inline code are skipped."""
    found: list[tuple[str, int]] = []
    for lineno, line in enumerate(strip_code(text).split("\n"), start=1):
        for match in WIKILINK_RE.finditer(line):
            target = match.group(1).split("|")[0].split("#")[0].strip()
            if target:
                found.append((target, lineno))
    return found


def find_provenance_markers(text: str) -> list[tuple[str, int]]:
    """(raw path, line) for every ^[raw/...] marker outside code."""
    found: list[tuple[str, int]] = []
    for lineno, line in enumerate(strip_code(text).split("\n"), start=1):
        for match in PROVENANCE_RE.finditer(line):
            found.append((match.group(1).strip(), lineno))
    return found


# ---------------------------------------------------------------------------
# Vault model
# ---------------------------------------------------------------------------


@dataclass
class Note:
    """A permanent note. Every line number here is a 1-based line in the file itself."""

    path: Path
    relpath: str
    frontmatter: dict | None = None
    body: str = ""
    parse_error: str | None = None
    parse_error_line: int | None = None
    links: list[tuple[str, int]] = field(default_factory=list)
    markers: list[tuple[str, int]] = field(default_factory=list)

    @property
    def id(self) -> str | None:
        value = (self.frontmatter or {}).get("id")
        return None if value is None else str(value)

    @property
    def slug(self) -> str:
        return self.path.stem


@dataclass
class RawFile:
    path: Path
    relpath: str
    data: bytes
    frontmatter: dict | None = None
    parse_error: str | None = None
    parse_error_line: int | None = None

    @property
    def digest(self) -> str:
        return body_digest(self.data)


@dataclass
class Vault:
    root: Path
    notes: list[Note] = field(default_factory=list)
    raw: list[RawFile] = field(default_factory=list)
    structure: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)

    @property
    def notes_by_id(self) -> dict[str, Note]:
        out: dict[str, Note] = {}
        for note in self.notes:
            if note.id and note.id not in out:
                out[note.id] = note
        return out

    @property
    def note_slugs(self) -> set[str]:
        return {note.slug for note in self.notes}


REQUIRED_VAULT_PATHS = ("permanent", "SCHEMA.md", "log.md")


def load_vault(root: Path) -> Vault:
    vault = Vault(root=root)
    vault.missing = [name for name in REQUIRED_VAULT_PATHS if not (root / name).exists()]

    permanent = root / "permanent"
    if permanent.is_dir():
        for path in sorted(permanent.glob("*.md")):
            vault.notes.append(_load_note(path, root))

    raw_root = root / "raw"
    if raw_root.is_dir():
        for path in sorted(raw_root.rglob("*.md")):
            data = path.read_bytes()
            frontmatter_bytes, _, frontmatter_start, _ = split_with_lines(data)
            parsed, error, line = parse_yaml_subset(frontmatter_bytes.decode("utf-8", "replace"))
            vault.raw.append(
                RawFile(
                    path=path,
                    relpath=str(path.relative_to(root)),
                    data=data,
                    frontmatter=parsed,
                    parse_error=error,
                    parse_error_line=None if line is None else frontmatter_start + line - 1,
                )
            )

    structure = root / "structure"
    if structure.is_dir():
        for path in sorted(structure.glob("*.md")):
            vault.structure[path.name] = path.read_text(encoding="utf-8", errors="replace")

    return vault


def _shift(lines: list[tuple[str, int]], body_start: int) -> list[tuple[str, int]]:
    return [(target, body_start + line - 1) for target, line in lines]


def _load_note(path: Path, root: Path) -> Note:
    data = path.read_bytes()
    frontmatter_bytes, body_bytes, frontmatter_start, body_start = split_with_lines(data)
    parsed, error, line = parse_yaml_subset(frontmatter_bytes.decode("utf-8", "replace"))
    body = body_bytes.decode("utf-8", "replace")
    return Note(
        path=path,
        relpath=str(path.relative_to(root)),
        frontmatter=parsed,
        body=body,
        parse_error=error,
        parse_error_line=None if line is None else frontmatter_start + line - 1,
        links=_shift(find_wikilinks(body), body_start),
        markers=_shift(find_provenance_markers(body), body_start),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _cmd_hash(path: Path) -> int:
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 2
    print(body_digest(path.read_bytes()))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="zettel_lint.py", description="Lint a Zettelkasten vault (read-only)."
    )
    parser.add_argument("vault", nargs="?", type=Path, help="vault root")
    parser.add_argument("--json", action="store_true", help="emit JSON on stdout")
    args = parser.parse_args(argv)

    if args.vault is not None and args.vault.name == "hash":
        print("usage: zettel_lint.py hash <file>", file=sys.stderr)
        return 2

    parser.print_help()
    return 2


def main_with_subcommands(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "hash":
        if len(argv) != 2:
            print("usage: zettel_lint.py hash <file>", file=sys.stderr)
            return 2
        return _cmd_hash(Path(argv[1]))
    return main(argv)


if __name__ == "__main__":
    raise SystemExit(main_with_subcommands())

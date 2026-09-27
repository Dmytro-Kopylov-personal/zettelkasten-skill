#!/usr/bin/env python3
"""Lint a Zettelkasten vault: what the vault's own files say about themselves.

Read-only, single file, standard library only. There is no --fix and no code path in
this file that opens anything for writing: the script verifies, the agent writes.

    python3 zettel_lint.py <vault> --json
    python3 zettel_lint.py <vault> --fail-on warn
    python3 zettel_lint.py hash <file>          # sha256 over the body bytes

Exit codes: 0 clean at --fail-on, 1 findings, 2 usage or vault error.

Every check here asserts a fact about the vault's own files: a reference that resolves to
nothing, a digest that no longer matches, two notes claiming one identity, a log entry
with no date on it. A check may not decide by a number. "800 words is too long" and "90
days without promoting a draft is too long" are opinions; they were once shipped as rules
with the same authority as the facts beside them, and they are gone. What a vault declares
about *itself* is checked instead, and only what it declares: the vocabulary in its own
SCHEMA.md, and nothing this linter would have imposed on it. The line is that the format is
ours — `id`, `title`, `created`, `updated`, a body, the shape of a link — and the
vocabulary is the vault's.

One consequence is an invariant worth stating because it is testable: no check reads the
clock, so two runs over the same bytes report the same findings whenever they are run.

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
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

#: Versions the JSON contract, not the plugin: 2 is the release where the code set shrank
#: and `config`/`config_sources` became `declared`/`declared_sources`.
SCHEMA_VERSION = "2"

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

FRONTMATTER_OPEN = re.compile(rb"^---\r?\n")
FRONTMATTER_CLOSE = re.compile(rb"\r?\n---[ \t]*\r?\n")
BOM = b"\xef\xbb\xbf"


def split_frontmatter_bytes(data: bytes) -> tuple[bytes, bytes]:
    """Split a file into (frontmatter bytes without fences, body bytes).

    Byte-exact: digests are computed over these slices, so a decode/re-encode round trip
    would change every hash. A file that does not open with a fence has no frontmatter,
    and its body is the whole file — a mid-document '---' horizontal rule must not be
    mistaken for a closing fence. CRLF files are recognised like LF ones, because a
    Windows-authored note is still a note.
    """
    opening = FRONTMATTER_OPEN.match(data)
    if not opening:
        return b"", data
    closing = FRONTMATTER_CLOSE.search(data, opening.end())
    if not closing:
        return b"", data
    return data[opening.end() : closing.start()], data[closing.end() :]


def decode_note_bytes(data: bytes) -> tuple[str | None, str | None]:
    """Decode a file for parsing. Returns (text, error) — never a lossy guess.

    Reading a latin-1 file with errors='replace' would parse to something plausible and
    wrong, so it is reported instead.
    """
    if data.startswith(BOM):
        return None, "a byte-order mark is not supported"
    try:
        return data.decode("utf-8"), None
    except UnicodeDecodeError as exc:
        return None, f"the file is not valid UTF-8 (invalid byte at offset {exc.start})"


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


@dataclass
class ParsedFile:
    frontmatter: dict | None
    error: str | None
    error_line: int | None
    body: str
    body_start_line: int


def parse_file(data: bytes) -> ParsedFile:
    """Parse a whole file, resolving every line number to a file line.

    A file with no frontmatter fence is an error rather than five missing-field
    findings: the five are a symptom, the missing block is the cause, and naming the
    cause is what makes the report actionable.
    """
    decoded, decode_error = decode_note_bytes(data)
    if decode_error:
        return ParsedFile(None, decode_error, 1, "", 1)

    frontmatter_bytes, body_bytes, frontmatter_start, body_start = split_with_lines(data)
    body = body_bytes.decode("utf-8", "replace")
    if not frontmatter_bytes:
        return ParsedFile(None, "the file has no frontmatter block", 1, body, body_start)

    parsed, error, line = parse_yaml_subset(frontmatter_bytes.decode("utf-8"))
    return ParsedFile(
        parsed,
        error,
        None if line is None else frontmatter_start + line - 1,
        body,
        body_start,
    )


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
    _link_index: dict[str, Note] | None = field(default=None, repr=False)
    _declared: dict[str, list[str]] | None = field(default=None, repr=False)

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

    def link_index(self) -> dict[str, Note]:
        """Every spelling Obsidian would resolve to a note here, built once on first use.

        Obsidian writes the shortest unambiguous link and lengthens it only when two notes
        share a basename, so all of these occur in a real vault: `note`, `note.md`,
        `sub/note`, and the vault-relative `permanent/sub/note`. A note's twelve-digit
        filename is what stops two notes from sharing one, and ZK006 checks that.
        """
        if self._link_index is None:
            index: dict[str, Note] = {}
            for note in self.notes:
                rel = note.relpath[:-3] if note.relpath.endswith(".md") else note.relpath
                within = rel.split("/", 1)[1] if "/" in rel else rel
                for form in (note.slug, rel, within):
                    index.setdefault(form, note)
                    index.setdefault(f"{form}.md", note)
                if note.id:
                    index.setdefault(note.id, note)
            self._link_index = index
        return self._link_index

    def resolve(self, target: str) -> Note | None:
        """The note Obsidian would open for this link, or None if it opens nothing.

        Resolution is by the note, not by the string, so a link written in any of the
        accepted spellings credits the same note — which is what keeps the inbound count
        behind ZK010 and the orphan rate in the metrics from disagreeing with ZK008.
        """
        if not target:
            return None
        return self.link_index().get(target)

    def declared_vocabulary(self) -> dict[str, list[str]]:
        """The vocabulary this vault declares in its own SCHEMA.md; {} if it declares none."""
        if self._declared is None:
            self._declared = read_declaration(self.root)
        return self._declared


REQUIRED_VAULT_PATHS = ("permanent", "SCHEMA.md", "log.md")


def load_vault(root: Path) -> Vault:
    vault = Vault(root=root)
    vault.missing = [name for name in REQUIRED_VAULT_PATHS if not (root / name).exists()]

    permanent = root / "permanent"
    if permanent.is_dir():
        for path in sorted(permanent.rglob("*.md")):
            vault.notes.append(_load_note(path, root))

    raw_root = root / "raw"
    if raw_root.is_dir():
        for path in sorted(raw_root.rglob("*.md")):
            data = path.read_bytes()
            parsed = parse_file(data)
            vault.raw.append(
                RawFile(
                    path=path,
                    relpath=str(path.relative_to(root)),
                    data=data,
                    frontmatter=parsed.frontmatter,
                    parse_error=parsed.error,
                    parse_error_line=parsed.error_line,
                )
            )

    structure = root / "structure"
    if structure.is_dir():
        # Deliberately flat, while permanent/ and raw/ recurse. structure/ holds named
        # registries — index.md, SCHEMA.md, overview.md, concept-table.md — whose roles are
        # fixed by the layout, so nesting has no meaning to give a file. Recursing here
        # would buy nothing and cost something: a nested index.md would become a candidate
        # for *the* index, and the vault would be indexed by a file the user meant as a
        # sub-list. A missing structure/index.md is reported as not-applicable, which is
        # visible, so a vault that nests its index is told rather than silently misread.
        for path in sorted(structure.glob("*.md")):
            vault.structure[path.name] = path.read_text(encoding="utf-8", errors="replace")

    return vault


def _shift(lines: list[tuple[str, int]], body_start: int) -> list[tuple[str, int]]:
    return [(target, body_start + line - 1) for target, line in lines]


def _load_note(path: Path, root: Path) -> Note:
    parsed = parse_file(path.read_bytes())
    return Note(
        path=path,
        relpath=str(path.relative_to(root)),
        frontmatter=parsed.frontmatter,
        body=parsed.body,
        parse_error=parsed.error,
        parse_error_line=parsed.error_line,
        links=_shift(find_wikilinks(parsed.body), parsed.body_start_line),
        markers=_shift(find_provenance_markers(parsed.body), parsed.body_start_line),
    )


#: The dimensions a vault may declare in its own `SCHEMA.md`. There is no default for any
#: of them: a key that is absent means that dimension is not checked at all, which is the
#: difference between a foreign vault and a wrong one.
VOCABULARY_DIMENSIONS = ("tags", "required_fields", "types", "statuses", "confidences", "verbs")


def read_declaration(root: Path) -> dict[str, list[str]]:
    """The vocabulary `<root>/SCHEMA.md` declares, by dimension.

    Flat keys with flow lists — the shape `tags:` has always had. The subset parser rejects
    nested mappings outright, so a declaration a vault cannot write is not a declaration.
    A dimension whose key is absent, empty or not a list is left out entirely rather than
    filled in with something this linter would have preferred.
    """
    path = root / "SCHEMA.md"
    if not path.is_file():
        return {}
    frontmatter, _, _, _ = split_with_lines(path.read_bytes())
    parsed, _, _ = parse_yaml_subset(frontmatter.decode("utf-8", "replace"))
    if not isinstance(parsed, dict):
        return {}
    declared: dict[str, list[str]] = {}
    for key in VOCABULARY_DIMENSIONS:
        value = parsed.get(key)
        if not isinstance(value, list):
            continue
        values = sorted({_as_text(item) for item in value if _as_text(item)})
        if values:
            # An empty list says "nothing declared yet", not "nothing is legal".
            declared[key] = values
    return declared


def reference_target(vault: Vault, target: str) -> Note | Path | None:
    """What a reference points at: the note it names, the file it names, or nothing.

    One notion of resolution for every surface that carries a reference — a frontmatter
    link, a `[[wikilink]]`, a `sources:` entry, a `^[raw/...]` marker, an entry in the
    index. Notes resolve through the link index, so every spelling Obsidian accepts
    credits the same note. Everything else falls back to the filesystem, where a name
    written without `.md` also resolves to the file beside it: `raw/x` and `raw/x.md` are
    two spellings of one target, not two answers to one question.
    """
    if not target:
        return None
    note = vault.resolve(target)
    if note is not None:
        return note
    candidate = vault.root / target
    if candidate.is_file():
        return candidate
    if not target.endswith(".md") and (vault.root / f"{target}.md").is_file():
        return vault.root / f"{target}.md"
    return None


def reference_key(vault: Vault, target: str) -> str:
    """A reference's identity for set comparison: the note it resolves to, else its text.

    Two spellings of one note are one reference, which is what stops a Links section
    written the long way from reading as drift against a frontmatter written the short way.
    An unresolved target keys on its own text — that is all there is of it.
    """
    resolved = reference_target(vault, target)
    return resolved.relpath if isinstance(resolved, Note) else target


# ---------------------------------------------------------------------------
# Findings and checks
# ---------------------------------------------------------------------------

ERROR, WARN, INFO = "error", "warn", "info"
SEVERITY_ORDER = {ERROR: 0, WARN: 1, INFO: 2}

ID_IN_FILENAME_RE = re.compile(r"^(\d{12})-(.+)$")
#: Anchored, for validating that a whole string is a date.
ISO_DATE_RE = re.compile(r"^\d{4}-\d\d-\d\d$")
#: Unanchored, for finding a date inside a line — a log entry carries more than a date.
ISO_DATE_FIND = re.compile(r"\d{4}-\d\d-\d\d")


@dataclass(frozen=True, order=True)
class Finding:
    """One finding. Sorted by (code, file, subject, line) for byte-identical output."""

    code: str
    severity: str
    file: str
    subject: str
    message: str
    line: int | None = None
    evidence: str = ""
    action: str = ""
    fix: None = None

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "subject": self.subject,
            "message": self.message,
            "evidence": self.evidence,
            "action": self.action,
            "doc": f"references/lint-checks.md#{self.code.lower()}",
            "fix": None,
        }

    def key(self) -> str:
        """Baseline identity. The line is excluded: edits shift lines."""
        return f"{self.code}|{self.file}|{self.subject}"


@dataclass(frozen=True)
class NotApplicable:
    """A check whose input is absent. Reported, never silently counted as a pass."""

    reason: str


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    parse_failures: list[dict] = field(default_factory=list)
    skipped_checks: list[dict] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


def _as_text(value: object) -> str:
    return "" if value is None else str(value)


def _link_entries(note: Note) -> list[tuple[str, str]]:
    """(target, verb) pairs from the frontmatter, ignoring malformed entries."""
    raw = (note.frontmatter or {}).get("links")
    if not isinstance(raw, list):
        return []
    entries: list[tuple[str, str]] = []
    for item in raw:
        if isinstance(item, dict):
            entries.append((_as_text(item.get("target")), _as_text(item.get("verb"))))
    return entries


def _tag_list(note: Note) -> list[str]:
    raw = (note.frontmatter or {}).get("tags")
    if isinstance(raw, list):
        return [_as_text(tag) for tag in raw]
    if isinstance(raw, str) and raw:
        return [raw]
    return []


def _source_list(note: Note) -> list[str]:
    raw = (note.frontmatter or {}).get("sources")
    if isinstance(raw, list):
        return [_as_text(item) for item in raw]
    if isinstance(raw, str) and raw:
        return [raw]
    return []


def _field(note: Note, key: str) -> object:
    return (note.frontmatter or {}).get(key)


def _date_field(note: Note, key: str) -> dt.date | None:
    value = _field(note, key)
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str) and ISO_DATE_RE.match(value):
        try:
            return dt.date.fromisoformat(value)
        except ValueError:
            return None
    return None


# --- individual checks -------------------------------------------------------------


def check_vault_root(vault: Vault) -> list[Finding]:
    return [
        Finding(
            code="ZK001",
            severity=ERROR,
            file="",
            subject=name,
            message=f"the vault root is missing {name!r}",
            action="initialise the vault, or point the linter at the right directory",
        )
        for name in vault.missing
    ]


def check_parse(vault: Vault) -> list[Finding]:
    findings = []
    for note in vault.notes:
        if note.parse_error:
            findings.append(
                Finding(
                    code="ZK002",
                    severity=ERROR,
                    file=note.relpath,
                    line=note.parse_error_line,
                    subject="frontmatter",
                    message=f"frontmatter could not be parsed: {note.parse_error}",
                    action="fix the frontmatter by hand; the note is excluded from every "
                    "check that reads it rather than being treated as empty",
                )
            )
    for raw in vault.raw:
        if raw.parse_error:
            findings.append(
                Finding(
                    code="ZK002",
                    severity=ERROR,
                    file=raw.relpath,
                    line=raw.parse_error_line,
                    subject="frontmatter",
                    message=f"frontmatter could not be parsed: {raw.parse_error}",
                    action="fix the frontmatter by hand; the raw file is excluded from "
                    "the digest check rather than being treated as unchanged",
                )
            )
    return findings


def check_declaration(vault: Vault) -> list[Finding] | NotApplicable:
    """ZK003. The vault is judged by the vocabulary its own SCHEMA.md declares, and by
    nothing else.

    Five dimensions, each opt-in on its own: `required_fields` (which fields a note must
    carry), `types`, `statuses` and `confidences` (which values are legal), `verbs` (which
    link verbs are legal), and `tags`. A vault that declares none of them is not judged at
    all — a foreign vault's tags are not wrong for being different tags. What the linter
    does impose is the part no note can vary: a filename that is an identity (ZK006), a
    date that is a date (ZK005), a body, and a link that names a target and a verb.
    """
    declared = vault.declared_vocabulary()
    if not declared:
        return NotApplicable("SCHEMA.md declares no vocabulary")
    findings: list[Finding] = []
    required = declared.get("required_fields", [])
    enums = (
        ("type", declared.get("types", [])),
        ("status", declared.get("statuses", [])),
        ("confidence", declared.get("confidences", [])),
    )
    verbs = declared.get("verbs", [])
    tags = declared.get("tags", [])
    for note in vault.notes:
        if note.frontmatter is None:
            continue
        for name in required:
            if _field(note, name) in (None, ""):
                findings.append(
                    Finding(
                        code="ZK003",
                        severity=WARN,
                        file=note.relpath,
                        line=1,
                        subject=name,
                        message=f"the note has no {name!r}, which SCHEMA.md requires",
                        action=f"add {name!r} to the frontmatter, or drop it from SCHEMA.md",
                    )
                )
        for key, allowed in enums:
            value = _field(note, key)
            if not allowed or value in (None, ""):
                continue
            if _as_text(value) not in allowed:
                findings.append(
                    Finding(
                        code="ZK003",
                        severity=WARN,
                        file=note.relpath,
                        line=1,
                        subject=key,
                        message=f"{key} {_as_text(value)!r} is not one of the values "
                        "SCHEMA.md declares",
                        evidence=f"{key}: {_as_text(value)}",
                        action=f"use one of: {', '.join(allowed)} — or declare this one too",
                    )
                )
        for target, verb in _link_entries(note):
            if not verbs or verb in verbs:
                continue
            findings.append(
                Finding(
                    code="ZK003",
                    severity=WARN,
                    file=note.relpath,
                    line=None,
                    subject=target or "link",
                    message=f"the link verb {verb!r} is not one of the verbs SCHEMA.md declares",
                    evidence=f"- target: {target}\n    verb: {verb}",
                    action=f"use one of: {', '.join(verbs)} — or declare this one too",
                )
            )
        for tag in _tag_list(note):
            if tags and tag not in tags:
                findings.append(
                    Finding(
                        code="ZK003",
                        severity=WARN,
                        file=note.relpath,
                        line=1,
                        subject=tag,
                        message=f"tag {tag!r} is not among the tags SCHEMA.md declares",
                        action="add it to SCHEMA.md, or use an existing tag",
                    )
                )
    return findings


def check_dates(vault: Vault) -> list[Finding]:
    findings = []
    for note in vault.notes:
        if note.frontmatter is None:
            continue
        for key in ("created", "updated"):
            value = _field(note, key)
            if value in (None, ""):
                continue
            if _date_field(note, key) is None:
                findings.append(
                    Finding(
                        code="ZK005",
                        severity=ERROR,
                        file=note.relpath,
                        line=1,
                        subject=key,
                        message=f"{key} is not a YYYY-MM-DD date",
                        evidence=f"{key}: {_as_text(value)}",
                        action="write the date unquoted as YYYY-MM-DD",
                    )
                )
        created, updated = _date_field(note, "created"), _date_field(note, "updated")
        if created and updated and updated < created:
            findings.append(
                Finding(
                    code="ZK005",
                    severity=ERROR,
                    file=note.relpath,
                    line=1,
                    subject="updated",
                    message="updated is earlier than created",
                    evidence=f"created {created} > updated {updated}",
                    action="correct one of the two dates",
                )
            )
    return findings


def check_identity(vault: Vault) -> list[Finding]:
    """ZK006. The filename is the note's identity, and the links resolve to it, so it is
    the one thing about a note that cannot be edited freely.

    Two ways to break one identity, and so one code: a filename that is not an identity at
    all, and two files claiming the same one.
    """
    findings: list[Finding] = []
    for note in vault.notes:
        match = ID_IN_FILENAME_RE.match(note.slug)
        if not match:
            findings.append(
                Finding(
                    code="ZK006",
                    severity=ERROR,
                    file=note.relpath,
                    line=None,
                    subject=note.slug,
                    message="the filename is not YYYYMMDDHHMM-slug.md",
                    action="rename the file; IDs are the note's identity and must be stable",
                )
            )
            continue
        stamp = match.group(1)
        try:
            dt.datetime.strptime(stamp, "%Y%m%d%H%M")
        except ValueError:
            findings.append(
                Finding(
                    code="ZK006",
                    severity=ERROR,
                    file=note.relpath,
                    line=None,
                    subject=note.slug,
                    message=f"the timestamp {stamp} is not a real date",
                    action="rename the file with a real timestamp",
                )
            )
            continue
        if note.frontmatter is None or note.id is None:
            continue
        if _as_text(note.id) != stamp:
            findings.append(
                Finding(
                    code="ZK006",
                    severity=ERROR,
                    file=note.relpath,
                    line=1,
                    subject="id",
                    message=f"id {_as_text(note.id)} does not match the filename {stamp}",
                    evidence=f"id: {_as_text(note.id)} / file: {note.slug}",
                    action="make them agree; the filename is what the links resolve to",
                )
            )
    seen: dict[str, list[Note]] = {}
    for note in vault.notes:
        if note.id:
            seen.setdefault(note.id, []).append(note)
    for note_id, notes in sorted(seen.items()):
        if len(notes) < 2:
            continue
        for note in sorted(notes, key=lambda item: item.relpath)[1:]:
            findings.append(
                Finding(
                    code="ZK006",
                    severity=ERROR,
                    file=note.relpath,
                    line=1,
                    subject=note_id,
                    message=f"id {note_id} is used by {len(notes)} notes",
                    evidence=", ".join(sorted(item.relpath for item in notes)),
                    action="the second note is a duplicate idea, not a second file",
                )
            )
    return findings


def check_references(vault: Vault) -> list[Finding]:
    """ZK008. Every reference a note carries points at something, wherever it is written:
    a frontmatter link, a `[[wikilink]]`, a `sources:` entry, a `^[raw/...]` marker.

    One finding per (note, target), not one per surface. The body's Links section restates
    the frontmatter by design (ZK028 enforces it), so a broken target would otherwise be
    counted twice for the single defect and the total would mean nothing. All four surfaces
    go through one resolver, so they cannot disagree about what exists.
    """
    findings = []
    for note in vault.notes:
        reported: set[str] = set()
        for target, verb in _link_entries(note):
            if not target or reference_target(vault, target) is not None:
                continue
            reported.add(target)
            findings.append(
                Finding(
                    code="ZK008",
                    severity=ERROR,
                    file=note.relpath,
                    line=None,
                    subject=target,
                    message=f"the link target {target!r} does not exist",
                    evidence=f"- target: {target}\n    verb: {verb}",
                    action="create the note, or point the link at the note that exists",
                )
            )
        for target, line in note.links:
            if target in reported or reference_target(vault, target) is not None:
                continue
            reported.add(target)
            findings.append(
                Finding(
                    code="ZK008",
                    severity=ERROR,
                    file=note.relpath,
                    line=line,
                    subject=target,
                    message=f"the wikilink {target!r} does not exist",
                    evidence=f"[[{target}]]",
                    action="create the note, or correct the link",
                )
            )
        for source in _source_list(note):
            if source in reported or reference_target(vault, source) is not None:
                continue
            reported.add(source)
            findings.append(
                Finding(
                    code="ZK008",
                    severity=ERROR,
                    file=note.relpath,
                    line=1,
                    subject=source,
                    message=f"the cited source {source!r} is not in the vault",
                    action="capture the source under raw/, or correct the path",
                )
            )
        for target, line in note.markers:
            if target in reported or reference_target(vault, target) is not None:
                continue
            reported.add(target)
            findings.append(
                Finding(
                    code="ZK008",
                    severity=ERROR,
                    file=note.relpath,
                    line=line,
                    subject=target,
                    message=f"the provenance marker points at {target!r}, which is not in the vault",
                    evidence=f"^[{target}]",
                    action="capture the source under raw/, or remove the marker",
                )
            )
    return findings


def inbound_counts(vault: Vault) -> dict[str, int]:
    """Inbound links per note, keyed by relpath.

    Links from `structure/` are excluded, or `index.md` would cure every orphan and ZK010
    would be provably vacuous. The count keys on the note a link *resolves to* rather than
    on the string that was written, so the four spellings of one target are one link. Both
    ZK010 and the metrics use this, so the finding and the number cannot disagree.
    """
    counts: dict[str, int] = {}
    for note in vault.notes:
        targets = [target for target, _ in _link_entries(note) if target]
        targets += [target for target, _ in note.links]
        for target in targets:
            other = vault.resolve(target)
            if other is None or other is note:
                continue
            counts[other.relpath] = counts.get(other.relpath, 0) + 1
    return counts


def check_isolation(vault: Vault) -> list[Finding]:
    """ZK010. A note that neither links nor is linked is not in the vault, whatever it says.

    Both directions are one subject: a note nothing can reach and a note that reaches
    nothing are the same defect seen from either end. The floor is zero rather than "two
    outbound links" — how many links a note *should* carry is a writer's judgement, and a
    check may only assert what it can see in the file.
    """
    inbound = inbound_counts(vault)
    findings = []
    for note in vault.notes:
        if note.frontmatter is None:
            continue
        outbound = len([entry for entry in _link_entries(note) if entry[0]])
        inbound_here = inbound.get(note.relpath, 0)
        if outbound and inbound_here:
            continue
        if not outbound and not inbound_here:
            message = "the note links to nothing, and nothing links to it"
        elif not outbound:
            message = "the note links out to nothing"
        else:
            message = "no note links to this one"
        findings.append(
            Finding(
                code="ZK010",
                severity=WARN,
                file=note.relpath,
                line=None,
                subject=note.slug,
                message=message,
                action="link it to the ideas it extends, supports or contradicts — or link "
                "it from a note that depends on it",
            )
        )
    return findings


def check_index(vault: Vault):
    index = vault.structure.get("index.md")
    if index is None:
        return NotApplicable("there is no structure/index.md")
    findings = []
    for note in vault.notes:
        if note.frontmatter is None:
            continue
        if note.slug not in index and (note.id or "\0") not in index:
            findings.append(
                Finding(
                    code="ZK012",
                    severity=ERROR,
                    file="structure/index.md",
                    line=None,
                    subject=note.slug,
                    message=f"{note.relpath} is not listed in the index",
                    action="add it to structure/index.md",
                )
            )
    for target, line in find_wikilinks(index):
        if reference_target(vault, target) is None:
            findings.append(
                Finding(
                    code="ZK012",
                    severity=ERROR,
                    file="structure/index.md",
                    line=line,
                    subject=target,
                    message=f"the index links to {target!r}, which does not exist",
                    evidence=f"[[{target}]]",
                    action="remove the entry, or create the note it names",
                )
            )
    return findings


def check_raw_hashes(vault: Vault):
    if not vault.raw:
        return NotApplicable("the vault has no raw sources")
    findings = []
    for raw in vault.raw:
        if raw.frontmatter is None:
            continue
        recorded = raw.frontmatter.get("sha256")
        if recorded in (None, ""):
            findings.append(
                Finding(
                    code="ZK014",
                    severity=ERROR,
                    file=raw.relpath,
                    line=1,
                    subject="sha256",
                    message="the raw file records no sha256",
                    action="run `zettel_lint.py hash <file>` and record the digest",
                )
            )
    return findings


def check_empty_body(vault: Vault) -> list[Finding]:
    findings = []
    for note in vault.notes:
        if note.frontmatter is None:
            continue
        if not note.body.strip():
            findings.append(
                Finding(
                    code="ZK015",
                    severity=ERROR,
                    file=note.relpath,
                    line=None,
                    subject=note.slug,
                    message="the note has no body",
                    action="a note is a claim with evidence; write it, or delete the file",
                )
            )
    return findings


def check_hash_drift(vault: Vault):
    if not vault.raw:
        return NotApplicable("the vault has no raw sources")
    findings = []
    for raw in vault.raw:
        if raw.frontmatter is None:
            continue
        recorded = raw.frontmatter.get("sha256")
        if recorded in (None, ""):
            continue
        actual = raw.digest
        if _as_text(recorded) != actual:
            findings.append(
                Finding(
                    code="ZK019",
                    severity=WARN,
                    file=raw.relpath,
                    line=1,
                    subject="sha256",
                    message="the recorded sha256 no longer matches the body",
                    evidence=f"recorded {_as_text(recorded)}\nactual   {actual}",
                    action="raw/ is immutable: re-ingest the source and update the notes "
                    "that cite it, rather than editing the digest",
                )
            )
    return findings


LOG_ENTRY_RE = re.compile(r"^\s*[-*]\s")


def check_log(vault: Vault):
    log_path = vault.root / "log.md"
    if not log_path.is_file():
        return NotApplicable("the vault has no log.md")
    findings = []
    for lineno, line in enumerate(
        log_path.read_text(encoding="utf-8", errors="replace").split("\n"), start=1
    ):
        if not LOG_ENTRY_RE.match(line):
            continue
        if not ISO_DATE_FIND.search(line):
            findings.append(
                Finding(
                    code="ZK022",
                    severity=WARN,
                    file="log.md",
                    line=lineno,
                    subject=f"line {lineno}",
                    message="the log entry carries no YYYY-MM-DD date",
                    evidence=line.strip()[:120],
                    action="log entries are dated; a log you cannot order is not a log",
                )
            )
    return findings


def _cited_files(vault: Vault) -> set[str]:
    """Every file the notes cite, keyed by vault-relative path.

    A source cited as `raw/x` and one cited as `raw/x.md` are one file, because they go
    through the same resolver that decides whether a reference resolves at all.
    """
    cited: set[str] = set()
    for note in vault.notes:
        targets = list(_source_list(note)) + [target for target, _ in note.markers]
        for target in targets:
            resolved = reference_target(vault, target)
            if isinstance(resolved, Path):
                cited.add(str(resolved.relative_to(vault.root)))
            elif target:
                cited.add(target)
    return cited


def check_unreferenced_raw(vault: Vault):
    if not vault.raw:
        return NotApplicable("the vault has no raw sources")
    cited = _cited_files(vault)
    findings = []
    for raw in vault.raw:
        if raw.relpath in cited:
            continue
        findings.append(
            Finding(
                code="ZK026",
                severity=INFO,
                file=raw.relpath,
                line=None,
                subject=raw.relpath,
                message="no note cites this source",
                action="compile a note from it, or say why it is kept",
            )
        )
    return findings


def check_unreciprocated_contradictions(vault: Vault):
    """ZK027. A contradiction is a relationship; one recorded on a single side is half-written."""
    if not any(verb == "contradicts" for note in vault.notes for _, verb in _link_entries(note)):
        return NotApplicable("no note uses the 'contradicts' verb")
    findings = []
    for note in vault.notes:
        for target, verb in _link_entries(note):
            if verb != "contradicts" or not target:
                continue
            other = reference_target(vault, target)
            if not isinstance(other, Note):
                continue
            back = {reference_key(vault, entry) for entry, _ in _link_entries(other) if entry}
            back |= {reference_key(vault, entry) for entry, _ in other.links if entry}
            if note.relpath in back:
                continue
            findings.append(
                Finding(
                    code="ZK027",
                    severity=INFO,
                    file=other.relpath,
                    line=None,
                    subject=note.slug,
                    message=f"{note.relpath} contradicts this note, and it does not link back",
                    action="a contradiction is a relationship: record it on both sides",
                )
            )
    return findings


def check_links_section_drift(vault: Vault) -> list[Finding]:
    """ZK028. The body's Links section restates the frontmatter; the two must agree.

    Compared by what each target *resolves to*, so a body that writes the long form of a
    link the frontmatter wrote short is not drift.
    """
    findings = []
    for note in vault.notes:
        if note.frontmatter is None:
            continue
        if not note.body.strip():
            # A note with no body is ZK015's report. Two findings for one empty file would
            # make the reader fix the same thing twice.
            continue
        frontmatter_targets = {
            reference_key(vault, target) for target, _ in _link_entries(note) if target
        }
        body_targets = {reference_key(vault, target) for target, _ in note.links if target}
        if not frontmatter_targets and not body_targets:
            continue
        if frontmatter_targets != body_targets:
            missing = sorted(frontmatter_targets - body_targets)
            extra = sorted(body_targets - frontmatter_targets)
            findings.append(
                Finding(
                    code="ZK028",
                    severity=INFO,
                    file=note.relpath,
                    line=None,
                    subject=note.slug,
                    message="the Links section and the frontmatter links disagree",
                    evidence=f"only in frontmatter: {missing}\nonly in the body: {extra}",
                    action="the frontmatter is authoritative; bring the body into line",
                )
            )
    return findings


#: The registry. `references/lint-checks.md` documents every code here, 1:1, and a test
#: fails if the two ever drift apart. The numbers are not contiguous, and that is the
#: point: a retired code keeps its number retired, so `ZK019` means one thing in every
#: version that reports it. `references/lint-checks.md` carries the v1 → v2 mapping.
CHECKS: tuple[tuple[str, object], ...] = (
    ("ZK001", check_vault_root),
    ("ZK002", check_parse),
    ("ZK003", check_declaration),
    ("ZK005", check_dates),
    ("ZK006", check_identity),
    ("ZK008", check_references),
    ("ZK010", check_isolation),
    ("ZK012", check_index),
    ("ZK014", check_raw_hashes),
    ("ZK015", check_empty_body),
    ("ZK019", check_hash_drift),
    ("ZK022", check_log),
    ("ZK026", check_unreferenced_raw),
    ("ZK027", check_unreciprocated_contradictions),
    ("ZK028", check_links_section_drift),
)

#: Checks whose subject is the notes themselves. With no notes they have nothing to
#: examine, and saying so is the difference between "clean" and "not looked at".
NOTE_SCOPED = frozenset(
    {"ZK003", "ZK005", "ZK006", "ZK008", "ZK010", "ZK015", "ZK027", "ZK028"}
)
#: Checks whose subject is `raw/`. ZK026 belongs here as much as the two digest checks: a
#: vault with no captures has nothing to hash and nothing to be left uncited, and leaving it
#: out had the same sentence written twice — once in this table, once in the check's body.
RAW_SCOPED = frozenset({"ZK014", "ZK019", "ZK026"})

SEVERITIES = {
    "ZK001": ERROR, "ZK002": ERROR, "ZK005": ERROR, "ZK006": ERROR, "ZK008": ERROR,
    "ZK012": ERROR, "ZK014": ERROR, "ZK015": ERROR,
    "ZK003": WARN, "ZK010": WARN, "ZK019": WARN, "ZK022": WARN,
    "ZK026": INFO, "ZK027": INFO, "ZK028": INFO,
}


def run_checks(vault: Vault) -> Report:
    report = Report()
    for code, function in CHECKS:
        if not vault.notes and code in NOTE_SCOPED:
            report.skipped_checks.append(
                {"code": code, "reason": "not applicable: the vault has no permanent notes"}
            )
            continue
        if not vault.raw and code in RAW_SCOPED:
            report.skipped_checks.append(
                {"code": code, "reason": "not applicable: the vault has no raw sources"}
            )
            continue
        try:
            produced = function(vault)
        except Exception as exc:  # noqa: BLE001 - a check that cannot run must say so
            report.skipped_checks.append(
                {"code": code, "reason": f"{type(exc).__name__}: {exc}"}
            )
            continue
        if isinstance(produced, NotApplicable):
            report.skipped_checks.append({"code": code, "reason": f"not applicable: {produced.reason}"})
            continue
        for finding in produced:
            report.findings.append(
                finding
                if finding.severity == SEVERITIES[code]
                else Finding(
                    **{**finding.__dict__, "severity": SEVERITIES[code]}
                )
            )
    report.findings.sort()
    report.metrics = collect_metrics(vault)
    return report


def collect_metrics(vault: Vault) -> dict:
    verbs: dict[str, int] = {}
    links = 0
    for note in vault.notes:
        for _, verb in _link_entries(note):
            if verb:
                verbs[verb] = verbs.get(verb, 0) + 1
                links += 1
    inbound = inbound_counts(vault)
    orphans = sum(
        1
        for note in vault.notes
        if note.frontmatter is not None and inbound.get(note.relpath, 0) == 0
    )
    return {
        "notes": len(vault.notes),
        "raw_sources": len(vault.raw),
        "links": links,
        "verb_distribution": dict(sorted(verbs.items())),
        "orphan_rate": round(orphans / len(vault.notes), 4) if vault.notes else 0.0,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_document(vault: Vault, report: Report, now: dt.date) -> dict:
    """The JSON contract.

    `declared` is the vocabulary the vault has put in force, and `declared_sources` names
    where each dimension came from: `SCHEMA.md` for one it declares, `not declared` for one
    it does not. That is how a reader tells a vault which opted out of a dimension from one
    this linter never read — the two look identical in the findings.
    """
    by_severity: dict[str, int] = {}
    by_code: dict[str, int] = {}
    for finding in report.findings:
        by_severity[finding.severity] = by_severity.get(finding.severity, 0) + 1
        by_code[finding.code] = by_code.get(finding.code, 0) + 1
    declared = vault.declared_vocabulary()
    return {
        "schema_version": SCHEMA_VERSION,
        "vault": str(vault.root),
        "now": now.isoformat(),
        "declared": dict(sorted(declared.items())),
        "declared_sources": {
            key: ("SCHEMA.md" if key in declared else "not declared")
            for key in VOCABULARY_DIMENSIONS
        },
        "summary": {
            "counts_by_severity": dict(sorted(by_severity.items())),
            "counts_by_code": dict(sorted(by_code.items())),
            "baselined": report.metrics.get("baselined", 0),
            "metrics": report.metrics,
        },
        "findings": [finding.as_dict() for finding in report.findings],
        "parse_failures": report.parse_failures,
        "skipped_checks": report.skipped_checks,
    }


def group_skipped(skipped: list[dict]) -> list[tuple[list[str], str]]:
    """Not-run checks grouped by reason, in the order the reasons first appear.

    The JSON keeps one entry per check — a machine asking "did ZK010 run?" deserves a
    direct answer. The human output would otherwise print the same sentence once per check,
    which is how a report teaches its reader to stop reading it. Every code is still named;
    only the repetition is removed.

    There is deliberately no `ZK003..ZK008 (8 checks)` collapse. The skipped codes are not a
    contiguous run of `CHECKS` — the note-scoped eight are interleaved with the index, raw
    and log checks — so a range would name two codes and hide the rest behind a span no
    reader can expand. At fifteen codes the longest line carries eight names, which is
    legible; the width a collapse saves is not worth a line that cannot be read back.
    """
    groups: dict[str, list[str]] = {}
    for entry in skipped:
        groups.setdefault(entry["reason"], []).append(entry["code"])
    return list(groups.items())


def render_text(document: dict) -> str:
    lines: list[str] = []
    findings = document["findings"]
    for severity in (ERROR, WARN, INFO):
        group = [f for f in findings if f["severity"] == severity]
        if not group:
            continue
        lines.append(f"{severity}: {len(group)}")
        for finding in group:
            where = f"{finding['file']}:{finding['line']}" if finding["line"] else finding["file"]
            lines.append(f"  {finding['code']}  {where or 'vault'}  {finding['message']}")
            if finding["subject"]:
                lines.append(f"        subject: {finding['subject']}")
            if finding["action"]:
                lines.append(f"        action:  {finding['action']}")
        lines.append("")

    summary = document["summary"]
    metrics = summary["metrics"]
    raw_sources = metrics["raw_sources"]
    lines.append(
        f"{metrics['notes']} notes, {raw_sources} raw source{'' if raw_sources == 1 else 's'}, "
        f"{metrics['links']} links, orphan rate {metrics['orphan_rate']:.0%}"
    )
    if summary["baselined"]:
        lines.append(f"{summary['baselined']} finding(s) suppressed by the baseline")
    for reason, codes in group_skipped(document["skipped_checks"]):
        lines.append(f"NOT RUN: {', '.join(codes)} ({reason})")
    for failure in document["parse_failures"]:
        lines.append(f"PARSE FAILURE: {failure['file']}:{failure['line']} {failure['message']}")
    if not findings:
        lines.append("no findings")
    return "\n".join(lines) + "\n"


def lint_vault(
    root: Path,
    now: dt.date,
    baseline: set[str],
    fail_on: str = ERROR,
) -> tuple[dict, int]:
    """`now` is what the report says it was taken; no check reads it, which is what makes
    two runs over the same bytes report the same findings whenever they are run."""
    vault = load_vault(root)
    report = run_checks(vault)

    report.parse_failures = [
        {"file": finding.file, "line": finding.line, "message": finding.message}
        for finding in report.findings
        if finding.code == "ZK002"
    ]

    if baseline:
        kept = [finding for finding in report.findings if finding.key() not in baseline]
        report.metrics["baselined"] = len(report.findings) - len(kept)
        report.findings = kept

    document = build_document(vault, report, now)
    return document, exit_code(document, vault, fail_on)


def exit_code(document: dict, vault: Vault, fail_on: str = ERROR) -> int:
    """2 when this is not a vault at all, 1 when findings reach --fail-on, else 0.

    "Not a vault" must never be reported as "no findings": a green report from a
    directory the linter never understood is the failure this whole tool guards against.
    """
    if "permanent" in vault.missing or not vault.root.is_dir():
        return 2
    threshold = SEVERITY_ORDER[fail_on]
    if any(SEVERITY_ORDER[finding["severity"]] <= threshold for finding in document["findings"]):
        return 1
    return 0


def _cmd_hash(path: Path) -> int:
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 2
    print(body_digest(path.read_bytes()))
    return 0


def _resolve_vault_root(positional: Path | None) -> Path | None:
    if positional is not None:
        return positional
    from_env = os.environ.get("ZETTELKASTEN_VAULT_PATH")
    return Path(from_env) if from_env else None


def _load_baseline(path: Path | None) -> set[str]:
    if path is None:
        return set()
    if not path.is_file():
        print(f"baseline not found: {path}", file=sys.stderr)
        raise SystemExit(2)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"baseline is not valid JSON: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    if isinstance(loaded, dict):
        loaded = loaded.get("findings", [])
    if not isinstance(loaded, list) or not all(isinstance(item, str) for item in loaded):
        print("a baseline is a JSON list of 'code|file|subject' strings", file=sys.stderr)
        raise SystemExit(2)
    return set(loaded)


def _cmd_lint(args: argparse.Namespace) -> int:
    root = _resolve_vault_root(args.vault)
    if root is None:
        print(
            "usage: zettel_lint.py <vault>   (or set ZETTELKASTEN_VAULT_PATH)",
            file=sys.stderr,
        )
        return 2

    now = dt.date.fromisoformat(args.now) if args.now else dt.date.today()
    baseline = _load_baseline(args.baseline)

    document, code = lint_vault(root, now, baseline, args.fail_on)

    if args.baseline_keys:
        keys = sorted({finding["key"] for finding in _all_findings(root)})
        print(json.dumps(keys, indent=2))
        return 0

    if args.json or args.quiet:
        if args.json:
            print(json.dumps(document, indent=2, sort_keys=True))
    else:
        sys.stdout.write(render_text(document))
        if code == 2:
            print(
                "not a vault (ZK001 above): the exit code is 2, never 0 — a directory the "
                "linter did not understand must not read as clean",
                file=sys.stderr,
            )
    return code


def _all_findings(root: Path) -> list[dict]:
    report = run_checks(load_vault(root))
    return [
        {"key": finding.key(), "code": finding.code, "file": finding.file, "subject": finding.subject}
        for finding in report.findings
    ]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "hash":
        if len(argv) != 2:
            print("usage: zettel_lint.py hash <file>", file=sys.stderr)
            return 2
        return _cmd_hash(Path(argv[1]))

    parser = argparse.ArgumentParser(
        prog="zettel_lint.py",
        description="Lint a Zettelkasten vault. Read-only: there is no --fix.",
    )
    parser.add_argument("vault", nargs="?", type=Path, help="vault root")
    parser.add_argument("--json", action="store_true", help="emit the JSON contract on stdout")
    parser.add_argument(
        "--fail-on",
        choices=(ERROR, WARN, INFO),
        default=ERROR,
        help="lowest severity that makes the exit code 1 (default: error)",
    )
    parser.add_argument("--baseline", type=Path, help="JSON list of 'code|file|subject' keys")
    parser.add_argument(
        "--baseline-keys",
        action="store_true",
        help="print the current findings as baseline keys and exit (redirect it yourself: "
        "this script never writes a file)",
    )
    parser.add_argument(
        "--now",
        help="the date the report says it was taken (YYYY-MM-DD). No check decides by it, "
        "so two runs over the same bytes report the same findings whenever they run",
    )
    parser.add_argument("--quiet", action="store_true", help="no output; the exit code is the answer")
    args = parser.parse_args(argv)

    try:
        return _cmd_lint(args)
    except SystemExit as exc:  # a baseline error carries a message and a code
        if isinstance(exc.code, str):
            print(exc.code, file=sys.stderr)
        return int(exc.code) if isinstance(exc.code, int) else 2


if __name__ == "__main__":
    raise SystemExit(main())

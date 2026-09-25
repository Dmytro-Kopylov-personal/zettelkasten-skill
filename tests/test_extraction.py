"""Wikilink and provenance extraction, and the byte-exact digest.

The traps here are not hypothetical: every one of them was observed in a real vault.
`np.array([[500, 375]])` inside a fence, and prose that writes `[[wikilinks]]` inside
backticks to *describe* wikilinks, are the two that a naive scan gets wrong immediately.
"""

from __future__ import annotations

import sys

import pytest
from conftest import REPO

sys.path.insert(0, str(REPO / "skill" / "scripts"))
import zettel_lint  # noqa: E402

find_wikilinks = zettel_lint.find_wikilinks
find_markers = zettel_lint.find_provenance_markers
strip_code = zettel_lint.strip_code
body_digest = zettel_lint.body_digest
split_bytes = zettel_lint.split_frontmatter_bytes


# --- links ------------------------------------------------------------------------


def test_finds_a_plain_wikilink():
    assert find_wikilinks("See [[202609251200-spaced-repetition]] for the rest.") == [
        ("202609251200-spaced-repetition", 1)
    ]


def test_strips_the_alias_and_the_heading():
    assert find_wikilinks("[[202609251200-sr|spaced repetition]] and [[other#Section]]") == [
        ("202609251200-sr", 1),
        ("other", 1),
    ]


def test_line_numbers_survive_stripping():
    text = "one\n\ntwo [[a]]\n```\n[[b]]\n```\nfive [[c]]\n"
    assert find_wikilinks(text) == [("a", 3), ("c", 7)]


def test_trap_a_numpy_index_in_a_fence():
    text = '```python\npoints = np.array([[500, 375]])\n```\n'
    assert find_wikilinks(text) == []


def test_trap_wikilinks_in_inline_code():
    assert find_wikilinks("Write links as `[[wikilinks]]` in the body.") == []


def test_trap_a_markdown_link_that_starts_like_a_wikilink():
    assert find_wikilinks("[[1](https://example.com)]") == []


def test_trap_a_tilde_fence():
    assert find_wikilinks("~~~\n[[inside]]\n~~~\n") == []


def test_trap_an_indented_fence():
    assert find_wikilinks("   ```\n[[inside]]\n   ```\n") == []


def test_trap_a_longer_inline_code_run():
    assert find_wikilinks("``[[a]] `` and [[b]]") == [("b", 1)]


def test_a_link_after_an_unclosed_fence_is_swallowed():
    """An unterminated fence runs to the end of the document, and we say so by omission."""
    assert find_wikilinks("```\ntext\n[[a]]\n") == []


def test_prose_mentioning_the_syntax_inside_backticks_is_not_a_link():
    text = "A wikilink (`[[target|alias]]`, `[[target#heading]]`) resolves by ID.\n"
    assert find_wikilinks(text) == []


def test_strip_code_preserves_every_line_and_column():
    text = "a `code` b\n```\nfenced\n```\nc\n"
    stripped = strip_code(text)
    assert stripped.count("\n") == text.count("\n")
    assert len(stripped.split("\n")[0]) == len(text.split("\n")[0])


# --- provenance -------------------------------------------------------------------


def test_finds_a_provenance_marker():
    text = "Attention is finite. ^[raw/articles/karpathy-llm-wiki-2026.md]\n"
    assert find_markers(text) == [("raw/articles/karpathy-llm-wiki-2026.md", 1)]


def test_a_marker_inside_a_fence_is_not_a_marker():
    assert find_markers("```\n^[raw/x.md]\n```\n") == []


def test_two_markers_on_one_line():
    assert find_markers("^[raw/a.md] and ^[raw/b.md]\n") == [("raw/a.md", 1), ("raw/b.md", 1)]


# --- digest -----------------------------------------------------------------------


def test_digest_is_stable_across_calls():
    data = b"---\nsource_url: x\n---\n\nbody\n"
    assert body_digest(data) == body_digest(data)


def test_digest_ignores_the_frontmatter():
    """Otherwise recording the digest in the frontmatter would change the digest."""
    first = b"---\nsource_url: x\n---\n\nthe body\n"
    second = b"---\nsource_url: x\nsha256: whatever\n---\n\nthe body\n"
    assert body_digest(first) == body_digest(second)


def test_digest_changes_when_the_body_changes():
    assert body_digest(b"---\na: 1\n---\n\nbody\n") != body_digest(b"---\na: 1\n---\n\nbodX\n")


def test_a_file_without_frontmatter_is_hashed_whole():
    assert body_digest(b"just text\n") == body_digest(b"just text\n")


def test_a_mid_document_rule_is_not_a_fence():
    data = b"text\n\n---\n\nmore text\n"
    frontmatter, body = split_bytes(data)
    assert frontmatter == b""
    assert body == data


def test_split_is_byte_exact():
    data = b"---\nid: 1\n---\nbody\n"
    frontmatter, body = split_bytes(data)
    assert frontmatter == b"id: 1"
    assert body == b"body\n"


def test_crlf_bodies_hash_differently_from_lf():
    """Digests are over bytes. Normalising newlines would make drift invisible."""
    assert body_digest(b"---\na: 1\n---\r\nbody\r\n") != body_digest(b"---\na: 1\n---\nbody\n")


# --- the vault model --------------------------------------------------------------


def build_vault(tmp_path, **files):
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return tmp_path


def test_a_folder_that_is_not_a_vault_names_what_is_missing(tmp_path):
    vault = zettel_lint.load_vault(tmp_path)
    assert vault.missing == ["permanent", "SCHEMA.md", "log.md"]
    assert vault.notes == []


def test_loading_a_vault_collects_notes_raw_and_structure(tmp_path):
    root = build_vault(
        tmp_path,
        **{
            "permanent/202609261430-attention.md": (
                "---\nid: 202609261430\ntitle: Attention\ntags: [cognition]\n---\n\n"
                "Attention is finite. ^[raw/articles/x.md] See [[202609251200-sr]].\n"
            ),
            "raw/articles/x.md": "---\nsource_url: https://example.com\n---\n\nsource body\n",
            "structure/index.md": "# Index\n",
            "SCHEMA.md": "# Schema\n",
            "log.md": "# Log\n",
        },
    )
    vault = zettel_lint.load_vault(root)

    assert vault.missing == []
    assert [note.slug for note in vault.notes] == ["202609261430-attention"]
    note = vault.notes[0]
    assert note.id == "202609261430"
    assert note.frontmatter["tags"] == ["cognition"]
    assert note.links == [("202609251200-sr", 7)]
    assert note.markers == [("raw/articles/x.md", 7)]
    assert [raw.relpath for raw in vault.raw] == ["raw/articles/x.md"]
    assert vault.raw[0].digest == body_digest(b"---\nsource_url: https://example.com\n---\n\nsource body\n")
    assert "index.md" in vault.structure


def test_a_note_with_broken_frontmatter_keeps_its_error(tmp_path):
    root = build_vault(
        tmp_path,
        **{
            "permanent/202609261430-broken.md": "---\nid: 1\ntags:\n\t- a\n---\n\nbody\n",
            "SCHEMA.md": "# Schema\n",
            "log.md": "# Log\n",
        },
    )
    vault = zettel_lint.load_vault(root)
    note = vault.notes[0]
    assert note.frontmatter is None
    assert note.parse_error is not None
    assert note.parse_error_line == 4


def test_line_numbers_are_file_lines_not_body_lines(tmp_path):
    """A finding has to point at a line the reader can open the file to."""
    root = build_vault(
        tmp_path,
        **{
            "permanent/202609261430-a.md": (
                "---\nid: 202609261430\n---\n\nfirst\nsecond [[target]]\n"
            ),
            "SCHEMA.md": "# Schema\n",
            "log.md": "# Log\n",
        },
    )
    note = zettel_lint.load_vault(root).notes[0]
    assert note.path.read_text(encoding="utf-8").splitlines()[5] == "second [[target]]"
    assert note.links == [("target", 6)]


def test_notes_without_an_id_are_absent_from_the_id_index(tmp_path):
    root = build_vault(
        tmp_path,
        **{
            "permanent/no-id.md": "---\ntitle: No id\n---\n\nbody\n",
            "SCHEMA.md": "# Schema\n",
            "log.md": "# Log\n",
        },
    )
    vault = zettel_lint.load_vault(root)
    assert vault.notes_by_id == {}
    assert vault.note_slugs == {"no-id"}


def test_load_vault_does_not_write_anything(tmp_path):
    root = build_vault(
        tmp_path,
        **{
            "permanent/202609261430-a.md": "---\nid: 202609261430\n---\n\nbody\n",
            "SCHEMA.md": "# Schema\n",
            "log.md": "# Log\n",
        },
    )
    before = {path: path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}
    zettel_lint.load_vault(root)
    after = {path: path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}
    assert before == after

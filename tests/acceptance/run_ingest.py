#!/usr/bin/env python3
"""The Hermes acceptance run: does a real agent, given the real skill, follow the protocol?

Not a pytest test, because it calls a model: it is run by hand, N times, and the pass rate is
the result. Everything it asserts is deterministic — the shipped linter judges the vault, and
the protocol markers are read out of the session record Hermes itself writes, so the scoring
is done by instruments rather than by reading a transcript and forming an opinion.

    python3 tests/acceptance/run_ingest.py --runs 3

Approvals are deliberately left **on**: this passes no `--yolo`, so Hermes' own configured
approval behaviour still applies to whatever the agent decides to do. An unattended run that
hits a prompt will sit until the timeout and fail the marker, which is the correct outcome —
a harness that disables the user's safety settings to make its own life easier is measuring
a different agent from the one that ships.

A run passes when the vault lints clean AND every protocol marker holds:

  1. `proposed_first`   — the agent emitted prose before its first write tool call, and that
                          prose reads as a plan (at least two candidate notes). The session
                          record carries tool calls in order, so this is checked, not assumed.
  2. `log_entry`        — `log.md` gained a well-formed entry (ZK022 agrees).
  3. `indexed`          — `structure/index.md` gained a note entry outside its example fence.
  4. `linked`           — at least two outbound links from the new notes resolve, and the
                          linter reports no broken link.

The vault is built by performing the Init section literally, from the shipped templates, so a
run that fails because the *scaffold* is wrong is distinguishable from one that fails because
the agent ignored the protocol. The source is written outside the vault, so the Capture step
(which writes `raw/` with a digest) is exercised rather than bypassed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "skill" / "scripts"))
import zettel_lint  # noqa: E402

TEMPLATES = REPO / "skill" / "templates"
PROTOCOL = {
    "SCHEMA.md": "SCHEMA.md",
    "index.md": "structure/index.md",
    "concept-table.md": "structure/concept-table.md",
    "overview.md": "structure/overview.md",
    "log.md": "log.md",
}
VAULT_DIRS = ("raw/articles", "raw/papers", "raw/notes", "permanent", "structure", "inbox")

#: A line that enumerates an intended action: `- x`, `* x`, `1. x`, `2) x`, indented or not.
#: Written as a pattern for the marker rather than a literal `1.` after a plan that used
#: `  2.`, `  3.` … was read as a single item and failed a run that had done nothing wrong.
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\S")

#: Hermes' file-mutation tools, named rather than pattern-matched: a predicate that quietly
#: stopped matching would make the ordering marker unable to fail.
#:
#: `patch` belongs here and was missing at first — it was the tool that made a real run's
#: first write, so the marker was reading "first write" from a later message and would have
#: missed a plan-less write that happened to use it.
#:
#: Deliberately **not** here: `terminal` and `execute_code`, which can write but are mostly
#: how the agent reads. Counting them would fire the marker on every `ls` and fail runs that
#: did nothing wrong. The cost is the mirror image — an agent that writes a vault file
#: through shell redirection before proposing is not caught by this marker. Nothing else in
#: the run is blinded to that: the vault is linted afterwards, and the log and index markers
#: are read from the files themselves.
WRITE_TOOLS = frozenset(
    {
        "write_file", "write", "create_file", "edit_file", "edit", "str_replace",
        "multi_edit", "apply_patch", "patch", "insert_text", "append_file",
        "create_directory",
    }
)

SESSION_ID_RE = re.compile(r"\b(\d{8}_\d{6}_[0-9a-f]{6})\b")

SOURCE = """\
# Spacing and the Forgetting Curve

Reviews that are spaced out beat reviews that are massed, even when the total time spent is
identical. The effect is large and it holds across ages and materials. What makes spacing
work is not the passage of time itself but the effort of retrieval after partial forgetting:
the memory has to be reconstructed, and reconstruction is what strengthens it.

This has a cost that is easy to miss. Spacing feels worse while it is happening. Learners
rate massed practice as more effective than spaced practice in the same session where spaced
practice is producing better retention, a dissociation that has been replicated many times.
Fluency during study is therefore a poor guide to learning, and a learner who trusts the
feeling will choose the schedule that works less well.

Retrieval practice is a separate mechanism with a similar profile. Testing yourself is not
only a measurement of what you know; the act of retrieval changes what you will know later.
The two interact: a test is most valuable when it comes after enough forgetting to be hard,
which is the same condition that makes spacing work.

Both effects are examples of the same underlying claim: difficulty that is desirable. Making
practice harder in the right way improves long-run retention, while making it harder in the
wrong way — interleaving unrelated material too early, or testing before any encoding has
happened — does not. The distinction is not the difficulty itself but whether the difficulty
requires the learner to reconstruct the target.

Practical schedules follow from this rather than from tradition. Expanding intervals are
common in spaced-repetition software, but the evidence for expansion over uniform intervals
is weaker than the evidence for spacing over massing. The robust finding is the gap, not its
shape.
"""


# --- the vault ---------------------------------------------------------------------------


def init_vault(root: Path, domain: str) -> None:
    for name in VAULT_DIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    for source, destination in PROTOCOL.items():
        target = root / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((TEMPLATES / source).read_bytes())

    schema = root / "SCHEMA.md"
    text = schema.read_text(encoding="utf-8").replace("domain: unset", f"domain: {domain}", 1)
    schema.write_text(text, encoding="utf-8")

    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    with (root / "log.md").open("a", encoding="utf-8") as handle:
        handle.write(f"\n- {stamp} — init — created the vault\n")


def snapshot(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): path.read_text(encoding="utf-8", errors="replace")
        for path in root.rglob("*")
        if path.is_file()
    }


# --- the run -----------------------------------------------------------------------------


def session_ids() -> set[str]:
    listing = subprocess.run(
        ["hermes", "sessions", "list"], capture_output=True, text=True, timeout=120
    ).stdout
    return set(SESSION_ID_RE.findall(listing))


def export_session(session_id: str) -> dict:
    result = subprocess.run(
        ["hermes", "sessions", "export", "-", "--session-id", session_id],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return {}
    return json.loads(result.stdout.strip().splitlines()[0])


def run_agent(vault: Path, source_path: Path, *, timeout: int) -> tuple[str, dict, str]:
    """One `hermes -z` run, with approvals as Hermes is configured. `-z` prints no session
    id, so the new one is whichever id was not in the listing before the run."""
    prompt = (
        f"Ingest the source at {source_path} into the Zettelkasten vault at {vault}. "
        "This is an automated run: state your plan first, then proceed without waiting "
        "for confirmation."
    )
    before = session_ids()
    result = subprocess.run(
        ["hermes", "-z", prompt, "--skills", "zettelkasten"],
        cwd=vault,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    new = session_ids() - before
    session_id = sorted(new)[-1] if new else ""
    record = export_session(session_id) if session_id else {}
    return result.stdout, record, session_id


# --- the markers -------------------------------------------------------------------------


def write_calls(messages: list[dict]) -> list[int]:
    """Indices of assistant messages that call a tool which writes."""
    indices = []
    for index, message in enumerate(messages):
        if message.get("role") != "assistant":
            continue
        for call in message.get("tool_calls") or []:
            name = (call.get("function") or {}).get("name") if isinstance(call, dict) else None
            if name in WRITE_TOOLS:
                indices.append(index)
                break
    return indices


def proposed_first(messages: list[dict]) -> tuple[bool, str]:
    """Prose naming at least two candidate notes, before the first write.

    The plan and the first write calls can share one assistant message: a model that states a
    plan and then acts on it emits both in a single turn, and whether the two land in one
    message or two is a detail of the runtime rather than of the protocol. So the plan counts
    if it appears **at or before** the first write — what must not happen is a write with no
    plan stated anywhere before it. That is the failure this marker exists to catch.

    The structural half is exact. The second half asks the prose to be a plan rather than a
    remark, which is why the text is returned: a keyword test cannot judge whether a plan is a
    plan, so the raw proposal is recorded for a human to read.
    """
    first_write = next(iter(write_calls(messages)), None)
    if first_write is None:
        return False, "the agent never wrote anything"
    remarks = False
    for message in messages[: first_write + 1]:
        if message.get("role") != "assistant":
            continue
        text = (message.get("content") or "").strip()
        if not text:
            continue
        remarks = True
        # A floor against degenerate matches, not a judgement of the plan's worth: two
        # enumerated actions in a sentence is a thin plan, but it is still a stated plan.
        if len(text) < 40:
            continue
        items = [line for line in text.splitlines() if LIST_ITEM_RE.match(line)]
        mentions = len(re.findall(r"\bnote\b", text, flags=re.IGNORECASE))
        if len(items) >= 2 or mentions >= 2:
            return True, text[:2000]
    if remarks:
        return False, "prose preceded the first write, but nothing that reads as a plan"
    return False, "the first write carried no prose at all — no plan was stated"


def count_log_entries(text: str) -> int:
    return sum(1 for line in text.splitlines() if zettel_lint.LOG_ENTRY_RE.match(line))


def markers(vault: Path, before: dict[str, str], after: dict[str, str], record: dict) -> dict:
    messages = record.get("messages") or []
    proposed, proposal = proposed_first(messages)

    log_gained = count_log_entries(after.get("log.md", "")) - count_log_entries(
        before.get("log.md", "")
    )

    created = [name for name in after if name not in before and name.startswith("permanent/")]
    index_before = before.get("structure/index.md", "").splitlines()
    indexed = [
        line
        for line in after.get("structure/index.md", "").splitlines()
        if "[[" in line and line not in index_before
    ]

    # find_wikilinks strips fences and inline code itself, so the index template's fenced
    # example cannot be counted as a real entry.
    outbound = sum(len(zettel_lint.find_wikilinks(after[name])) for name in created)

    return {
        "proposed_first": proposed,
        "proposal": proposal,
        "log_entry": log_gained >= 1,
        "log_gained": log_gained,
        "indexed": bool(indexed),
        "index_lines": len(indexed),
        "linked": outbound >= 2,
        "outbound_links": outbound,
        "created": created,
        "write_calls": len(write_calls(messages)),
        "messages": len(messages),
    }


def lint_vault(vault: Path) -> tuple[dict, int]:
    return zettel_lint.lint_vault(vault, {}, dt.date.today(), set(), zettel_lint.ERROR)


def rescore(path: Path) -> int:
    """Recompute the transcript-derived markers from the stored sessions.

    The vault is gone and the model has already run, but Hermes keeps the session, so a
    correction to how the transcript is read costs nothing to apply — which matters when the
    alternative is re-spending a model budget to re-derive a fact already on disk.
    """
    results = json.loads(path.read_text(encoding="utf-8"))
    for result in results:
        session_id = result.get("session_id")
        if not session_id:
            print(f"run {result['run']}: no session id stored, left as it was")
            continue
        record = export_session(session_id)
        messages = record.get("messages") or []
        if not messages:
            print(f"run {result['run']}: session {session_id} produced no messages")
            continue
        proposed, proposal = proposed_first(messages)
        was = result["proposed_first"]
        result.update(
            proposed_first=proposed,
            proposal=proposal,
            write_calls=len(write_calls(messages)),
            messages=len(messages),
        )
        result["passed"] = bool(
            result["vault_lints_clean"]
            and result["proposed_first"]
            and result["log_entry"]
            and result["indexed"]
            and result["linked"]
        )
        change = "" if was == proposed else f"   (was {was})"
        print(f"run {result['run']}: proposed_first = {proposed}{change}")
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    passed = sum(1 for r in results if r["passed"])
    print(f"\n{passed}/{len(results)} passed after re-scoring")
    for marker in MARKERS:
        print(f"  {marker:18s} {sum(1 for r in results if r[marker])}/{len(results)}")
    return 0 if passed == len(results) else 1


# --- the run loop ------------------------------------------------------------------------


def one_run(number: int, *, timeout: int) -> dict:
    root = Path(f"/tmp/zettel-acceptance-{number}")
    if root.exists():
        shutil.rmtree(root)
    vault = root / "vault"
    init_vault(vault, domain="how memory and learning actually work, evidence first")

    source = root / "spacing-and-forgetting.md"
    source.write_text(SOURCE, encoding="utf-8")

    before = snapshot(vault)
    stdout, record, session_id = run_agent(vault, source, timeout=timeout)
    after = snapshot(vault)

    document, code = lint_vault(vault)
    result = {
        "run": number,
        "vault": str(vault),
        "session_id": session_id,
        "vault_lints_clean": code == 0 and document["findings"] == [],
        "findings": [
            {"code": f["code"], "file": f["file"], "message": f["message"]}
            for f in document["findings"]
        ],
        "exit_code": code,
        "model": record.get("model"),
        "cost_usd": record.get("actual_cost_usd") or record.get("estimated_cost_usd"),
        "tokens": {"in": record.get("input_tokens"), "out": record.get("output_tokens")},
        "final_response": stdout.strip()[:1500],
        **markers(vault, before, after, record),
    }
    result["passed"] = bool(
        result["vault_lints_clean"]
        and result["proposed_first"]
        and result["log_entry"]
        and result["indexed"]
        and result["linked"]
    )
    return result


MARKERS = ("proposed_first", "log_entry", "indexed", "linked", "vault_lints_clean")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--json", type=Path, help="also write the raw results here")
    parser.add_argument(
        "--rescore",
        type=Path,
        metavar="RESULTS.json",
        help="recompute the transcript markers from the stored sessions, running nothing",
    )
    args = parser.parse_args()

    if args.rescore:
        return rescore(args.rescore)

    results = []
    for number in range(1, args.runs + 1):
        print(f"\n=== run {number}/{args.runs} ===", flush=True)
        result = one_run(number, timeout=args.timeout)
        results.append(result)
        verdict = "PASS" if result["passed"] else "FAIL"
        print(
            f"{verdict}  lint exit {result['exit_code']}  "
            f"created {len(result['created'])}  links {result['outbound_links']}  "
            f"cost ${result['cost_usd']}"
        )
        for marker in MARKERS:
            print(f"   {'ok ' if result[marker] else 'NO '} {marker}")
        for finding in result["findings"]:
            print(f"   {finding['code']} {finding['file']}: {finding['message']}")

    passed = [r for r in results if r["passed"]]
    print(f"\n=== {len(passed)}/{len(results)} passed ===")
    for marker in MARKERS:
        count = sum(1 for r in results if r[marker])
        print(f"  {marker:18s} {count}/{len(results)}")
    costs = [r["cost_usd"] for r in results if r["cost_usd"] is not None]
    if costs:
        print(f"  total cost         ${sum(costs):.4f}")

    if args.json:
        args.json.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"  written to         {args.json}")
    return 0 if len(passed) == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

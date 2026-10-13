"""Jev requests with more code: whole files where they fit, smaller blocks where not.

Code context for a case, from the checkout at the fixed commit with the mutant
applied and the edited line(s) marked:

- edited file: the whole file if it fits the budget; otherwise the top-level
  function or class containing the edit; otherwise the innermost function
  containing it; otherwise the hunk.
- test file: the whole file if it fits ``TEST_BUDGET``; otherwise its import
  lines plus the test function (and its class header, for a method).

Every choice is recorded with the limit that forced it (``Context.modes``),
so a result can be read by how much code Jev actually had.

Token counts are estimated as characters / 2.8 (see ``est``); ``BUDGET`` leaves room under
Jev's 32k limit on state plus the longest question.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

import agent_judge
import prompts
from run_jev_framing import ONE_QUESTION
from run_jev_framing import SITUATION as FRAMED_SITUATION

BUDGET = 28_000  # estimated tokens for code + test together
TEST_BUDGET = 12_000
MARK = "  # <-- marked line"

REACH_SITUATION = (
    "We're checking which tests execute which lines of code. We only want to know whether "
    "the marked line runs when the named test runs, not whether the test passes or fails."
)
REACH_QUESTION = {
    "reaches": {
        "type": "noul",
        "instructions": "When this test runs, does the marked line execute?",
        "criteria": {
            "true": "The marked line runs at least once during the test.",
            "false": "The marked line never runs during the test.",
        },
    }
}
FAILS_SITUATION = FRAMED_SITUATION.replace(
    "The change request, the original code, the test, and the edit are shown.",
    "The change request, the test file, the mutated code with the edited line marked, and "
    "the edit itself (original and replacement) are shown.",
)


def est(text: str) -> int:
    # Measured on Jev's own counts for these requests: 1.8-4.3 characters per
    # token, median 3.3, never below 2.9 on inputs over 15k tokens. At 4, nine
    # youtube-dl requests were refused as max_tokens_exceeded.
    return int(len(text) / 2.8)


@dataclass
class Context:
    code: str
    test: str
    modes: dict[str, str] = field(default_factory=dict)
    # 1-based inclusive line spans of each file that were sent.
    spans: dict[str, tuple[int, int]] = field(default_factory=dict)


def _mutated_lines(case) -> list[str]:
    root = agent_judge.PROJECTS / f"{case.project}-{case.bug_id}"
    lines = (root / case.edit.path).read_text(encoding="utf-8").splitlines()
    s, e = case.edit.start_line - 1, case.edit.end_line
    got = [x.strip() for x in lines[s:e]]
    if got != [x.strip() for x in case.edit.original.splitlines()]:
        raise prompts.CannotBuild(f"{case.case_id}: file lines do not hold the original")
    indent = lines[s][: len(lines[s]) - len(lines[s].lstrip())]
    base = case.edit.original.splitlines()[0]
    bi = len(base) - len(base.lstrip())
    new = [indent + r[bi:] if r.strip() else r for r in case.edit.replacement.splitlines()]
    out = lines[:s] + new + lines[e:]
    for i in range(s, s + len(new)):
        out[i] += MARK
    return out


def _enclosing(tree: ast.Module, line: int, top_only: bool) -> tuple[int, int] | None:
    best = None
    nodes = tree.body if top_only else list(ast.walk(tree))
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = min([node.lineno] + [d.lineno for d in node.decorator_list])
            if start <= line <= node.end_lineno and (
                best is None or (not top_only and start >= best[0])
            ):
                best = (start, node.end_lineno)
    return best


def _test_context(case) -> tuple[str, str, tuple[int, int] | None]:
    root = agent_judge.PROJECTS / f"{case.project}-{case.bug_id}"
    path = case.test_id.split("::")[0]
    text = (root / path).read_text(encoding="utf-8", errors="replace")
    if est(text) <= TEST_BUDGET:
        return text, "whole file", (1, len(text.splitlines()))
    tree = ast.parse(text)
    lines = text.splitlines()
    imports = [
        "\n".join(lines[n.lineno - 1 : n.end_lineno])
        for n in tree.body
        if isinstance(n, (ast.Import, ast.ImportFrom))
    ]
    parts = case.test_id.split("::")[1:]
    header = ""
    if len(parts) == 2:
        cls = next(
            (n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == parts[0]), None
        )
        if cls is not None:
            header = lines[cls.lineno - 1] + "\n    ...\n"
    body = (
        case.test_source
        if not header
        else "\n".join("    " + ln if ln else ln for ln in case.test_source.splitlines())
    )
    return (
        "\n".join(imports) + "\n\n" + header + body,
        f"imports + test function (file ~{est(text)} tokens > {TEST_BUDGET})",
        None,
    )


def build(case) -> Context:
    test, test_mode, test_span = _test_context(case)
    room = BUDGET - est(test)
    lines = _mutated_lines(case)
    whole = "\n".join(lines)
    ctx = Context(code="", test=test)
    ctx.modes["test"] = test_mode
    test_path = case.test_id.split("::")[0]
    if test_span:
        ctx.spans[test_path] = test_span
    if est(whole) <= room:
        ctx.code, ctx.modes["code"] = whole, "whole file"
        ctx.spans[case.edit.path] = (1, len(lines))
        return ctx
    tree = ast.parse("\n".join(ln.replace(MARK, "") for ln in lines))
    for top_only, label in ((True, "top-level block"), (False, "innermost function")):
        span = _enclosing(tree, case.edit.start_line, top_only)
        if span and est("\n".join(lines[span[0] - 1 : span[1]])) <= room:
            ctx.code = "\n".join(lines[span[0] - 1 : span[1]])
            ctx.modes["code"] = f"{label} (file ~{est(whole)} tokens > room {room})"
            ctx.spans[case.edit.path] = span
            return ctx
    ctx.code = prompts.mutated_hunk(case)
    ctx.modes["code"] = f"hunk (file ~{est(whole)} tokens; no enclosing block fits {room})"
    return ctx


def reach_body(case) -> dict:
    ctx = build(case)
    return {
        "model": "jev-latest",
        "state": {
            "situation": REACH_SITUATION,
            "test_file": ctx.test,
            "test_name": case.test_id.split("::", 1)[1],
            "code": ctx.code,
        },
        "questions": REACH_QUESTION,
    }


def fails_body(case) -> dict:
    ctx = build(case)
    return {
        "model": "jev-latest",
        "state": {
            "situation": FAILS_SITUATION,
            "change_request": prompts.commit_message(case),
            "test_file": ctx.test,
            "test_name": case.test_id.split("::", 1)[1],
            "code": ctx.code,
            "edit": f"original: {case.edit.original.strip()}\nnow: {case.edit.replacement.strip()}",
        },
        "questions": ONE_QUESTION,
    }

"""A coding agent as the escalation judge: can the biggest hammer close the gap?

Approach C sends the cases Jev is unsure about to the current judge. This
sends them instead to Claude Code (`claude -p`), reading a full checkout of
the project at the fixed commit with the mutant already applied. It may read
anything in that copy, the test and its helpers included; it may not run
anything.

Confinement follows #338's `ClaudeCodeAgent` (branch 338-agent-edit-builder,
`src/acceptance/mutation/agent.py`), minus Edit, since nothing here writes:

- `--tools Read,Glob,Grep`: no shell, so no pytest and no way to `cat` a
  denied path.
- `--settings` denying reads of this repository and every other worktree, so
  the agent cannot open `labels.json` (the answers) or the BugsInPy dataset.
- `--permission-mode dontAsk`: anything not allowed is refused.

Cases: the tuning cases C escalates (Jev, context+description, strictly
between the chosen thresholds) plus Jev's confident errors, so "the gap"
covers both what Jev passes on and what it gets wrong.

Record-if-missing under ``.acceptance/cache/jev-m52-agent/`` (gitignored).

Run:  .venv/bin/python docs/experiments/jev/m52/agent_judge.py [--limit N] [--replay]
Writes ``tuning-agent.json`` (aggregates and per-case verdicts by id).
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import prompts
import recorder
from split import cases, load_split

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PROJECTS = ROOT / ".acceptance" / "mutant-labels" / "projects"
CACHE = ROOT / ".acceptance" / "cache" / "jev-m52-agent"
OUT = HERE / "tuning-agent.json"

MODEL = "claude-opus-5-5"
TIMEOUT = 900
VARIANT = "context+description"
DENY = [
    ROOT.parent,  # every worktree, this one included
    Path.home() / "GoogleDrive" / "code" / "AI_acceptance_tool",
]
IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".git", ".pytest_cache")

PROMPT = """\
You are reviewing whether a test would catch a defect. You cannot run anything:
answer by reading the code.

The project in the current directory is checked out at the commit that made
this change:

{change_request}

One small mechanical edit (a mutant) has ALREADY been applied to this copy:

  File: {path}, line {line}
  Original:    {original}
  Now reads:   {replacement}
  ({description})

The test in question is `{test_id}`.

Question: if this test were run against the code as it is now, with the
mutant in place, would it fail (an assertion fails or an error is raised)?

Read the test, the code it calls, and any helpers or fixtures it depends on,
as deeply as you need. Consider the environment the tests run in (for example
the Python version) where it matters.

End your answer with exactly these two lines:
VERDICT: fails   (or VERDICT: survives)
P_FAILS: <your probability, from 0.00 to 1.00, that the test fails>
"""


def _settings() -> str:
    deny = [f"Read(/{p.resolve()}/**)" for p in DENY]
    return json.dumps({"permissions": {"allow": ["Read(./**)"], "deny": deny}}, sort_keys=True)


def _command() -> list[str]:
    return [
        "claude",
        "-p",
        "--output-format",
        "json",
        "--tools",
        "Read,Glob,Grep",
        "--permission-mode",
        "dontAsk",
        "--settings",
        _settings(),
        "--model",
        MODEL,
    ]


def _apply(copy: Path, case) -> None:
    target = copy / case.edit.path
    lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
    s, e = case.edit.start_line - 1, case.edit.end_line
    got = "".join(lines[s:e]).rstrip("\n")
    if [x.strip() for x in got.splitlines()] != [
        x.strip() for x in case.edit.original.splitlines()
    ]:
        raise ValueError(f"{case.case_id}: lines {s + 1}-{e} do not hold the original")
    indent = lines[s][: len(lines[s]) - len(lines[s].lstrip())]
    base = case.edit.original.splitlines()[0]
    base_indent = len(base) - len(base.lstrip())
    new = [
        (indent + r[base_indent:] if r.strip() else r) + "\n"
        for r in case.edit.replacement.splitlines()
    ]
    lines[s:e] = new
    target.write_text("".join(lines), encoding="utf-8")


def prompt_for(case) -> str:
    return PROMPT.format(
        change_request=prompts.commit_message(case),
        path=case.edit.path,
        line=case.edit.start_line,
        original=case.edit.original.strip(),
        replacement=case.edit.replacement.strip(),
        description=case.defect_description,
        test_id=case.test_id,
    )


def _parse(text: str) -> tuple[bool | None, float | None]:
    v = re.findall(r"VERDICT:\s*(fails|survives)", text, re.IGNORECASE)
    p = re.findall(r"P_FAILS:\s*([01](?:\.\d+)?)", text)
    verdict = v[-1].lower() == "fails" if v else None
    prob = float(p[-1]) if p else None
    return verdict, prob


def judge(case, replay: bool) -> dict:
    request = {"model": MODEL, "case_id": case.case_id, "prompt": prompt_for(case)}
    blob = json.dumps(request, sort_keys=True, ensure_ascii=False)
    path = CACHE / f"{hashlib.sha256(blob.encode()).hexdigest()}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    if replay:
        raise LookupError(f"not recorded: {case.case_id}")
    with tempfile.TemporaryDirectory(prefix="jev-agent-") as tmp:
        copy = Path(tmp) / f"{case.project}-{case.bug_id}"
        shutil.copytree(PROJECTS / f"{case.project}-{case.bug_id}", copy, ignore=IGNORE)
        _apply(copy, case)
        start = time.monotonic()
        proc = subprocess.run(
            _command(),
            input=request["prompt"],
            cwd=copy,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
        )
        elapsed = time.monotonic() - start
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        out = {}
    text = out.get("result") or ""
    verdict, prob = _parse(text)
    record = {
        "request": request,
        "returncode": proc.returncode,
        "is_error": out.get("is_error"),
        "result": text,
        "verdict": verdict,
        "p_fails": prob,
        "cost_usd": out.get("total_cost_usd"),
        "num_turns": out.get("num_turns"),
        "elapsed_s": round(elapsed, 1),
        "stderr_tail": proc.stderr[-400:] if proc.returncode else "",
    }
    if verdict is not None:  # never cache a failed run as an answer
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    return record


def selected() -> list[tuple[object, float, str]]:
    t = json.loads((HERE / "tuning-thresholds.json").read_text(encoding="utf-8"))
    lo, hi = t["jev"]["chosen"]["lo"], t["jev"]["chosen"]["hi"]
    tuning = set(load_split()["tuning"])
    out = []
    for c in cases():
        if c.case_id not in tuning:
            continue
        try:
            prompts.mutated_hunk(c)
        except prompts.CannotBuild:
            continue
        p = recorder.jev_p_yes(recorder.jev(prompts.jev_body(c, VARIANT), replay_only=True))
        if lo < p < hi:
            out.append((c, p, "escalated"))
        elif (p >= hi) != c.killed:
            out.append((c, p, "jev-confident-wrong"))
    return out


def main() -> int:
    replay = "--replay" in sys.argv
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    chosen = selected()
    if limit is not None:
        # A fixed-seed random draw, not the first N: case order is sorted by
        # project, so a prefix would be one or two projects only.
        import random

        draw = sorted(random.Random(379).sample(range(len(chosen)), limit))
        chosen = [chosen[i] for i in draw]
    a = json.loads((HERE / "tuning-judge-a.json").read_text(encoding="utf-8"))["verdicts"]

    with ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(lambda x: judge(x[0], replay), chosen))

    rows = []
    for (c, p, group), r in zip(chosen, records, strict=True):
        rows.append(
            {
                "case_id": c.case_id,
                "group": group,
                "killed": c.killed,
                "jev_p": p,
                "a": a[c.case_id],
                "agent": r["verdict"],
                "agent_p": r["p_fails"],
                "cost_usd": r["cost_usd"],
                "elapsed_s": r["elapsed_s"],
                "turns": r["num_turns"],
            }
        )

    def acc(key, group=None):
        rs = [x for x in rows if (group is None or x["group"] == group) and x[key] is not None]
        if key == "jev_p":
            ok = sum((x["jev_p"] >= 0.5) == x["killed"] for x in rs)
        else:
            ok = sum(x[key] == x["killed"] for x in rs)
        return {"n": len(rs), "correct": ok}

    summary = {}
    for g in (None, "escalated", "jev-confident-wrong"):
        summary[g or "all"] = {
            "jev": acc("jev_p", g),
            "a": acc("a", g),
            "agent": acc("agent", g),
        }
    costs = [x["cost_usd"] for x in rows if x["cost_usd"] is not None]
    report = {
        "model": MODEL,
        "cases": len(rows),
        "no_verdict": sum(x["agent"] is None for x in rows),
        "summary": summary,
        "total_cost_usd": round(sum(costs), 2),
        "mean_cost_usd": round(sum(costs) / len(costs), 3) if costs else None,
        "mean_elapsed_s": round(sum(x["elapsed_s"] for x in rows) / len(rows), 1),
        "rows": rows,
    }
    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=1))
    for x in rows:
        print(
            f"{x['group']:<20} killed={x['killed']!s:<5} jev={x['jev_p']:.2f} a={x['a']!s:<5} "
            f"agent={x['agent']!s:<5} p={x['agent_p']} ${x['cost_usd']} {x['elapsed_s']}s"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

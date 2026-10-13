"""Sort the cases the agent got right and Jev got wrong into difficulty categories.

Jev "wrong" means its most likely answer (p >= 0.5 means fails) disagrees with
the executed label. Each such case gets exactly one category, decided by a
test rather than by reading:

1. ``smarter-model``: Opus, with NO tools, given exactly the content Jev saw
   (the "context + description" variant: change request, file path, original
   hunk, test source, defect description) answers correctly. The input was
   enough; Jev's reasoning was not.
2. Otherwise Opus needed the checkout. Count the code locations the agent's
   answer cites that lie OUTSIDE what Jev was shown (the hunk's lines in the
   edited file, and the test function's lines). Citations in one file within
   15 lines of each other count as one location.
   - ``more-context``: exactly one such location.
   - ``multi-step``: two or more, i.e. the answer chains through several
     places Jev never saw.
   - ``uncited``: none. The agent was right without citing anything outside
     the shown material, so nothing here says why it beat no-tools Opus.

The no-tools call is `claude -p --tools ""` in an empty directory, recorded
under ``.acceptance/cache/jev-m52-notools/``.

Run:  .venv/bin/python docs/experiments/jev/m52/classify_gap.py
Writes ``tuning-gap-categories.json`` (case ids, categories, citation counts).
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import agent_judge
import prompts
from split import cases

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CACHE = ROOT / ".acceptance" / "cache" / "jev-m52-notools"
OUT = HERE / "tuning-gap-categories.json"
VARIANT = "context+description"
ENDING = (
    "\n\nAnswer by reasoning about the code shown. End your answer with exactly these two "
    "lines:\nVERDICT: fails   (or VERDICT: survives)\n"
    "P_FAILS: <your probability, from 0.00 to 1.00, that the test fails>"
)
CITE = re.compile(r"`?([\w./-]+\.py)`?(?::(\d+)(?:[-–](\d+))?)?")
NEAR = 15


def no_tools(case) -> dict:
    messages = prompts.mini_messages(case, VARIANT)
    prompt = messages[1]["content"].replace(
        "\n\n" + prompts.question(VARIANT), "\n\n" + prompts.question(VARIANT) + ENDING
    )
    request = {"model": agent_judge.MODEL, "tools": "", "prompt": prompt}
    blob = json.dumps(request, sort_keys=True, ensure_ascii=False)
    path = CACHE / f"{hashlib.sha256(blob.encode()).hexdigest()}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="jev-notools-") as tmp:
        proc = subprocess.run(
            [
                "claude",
                "-p",
                "--output-format",
                "json",
                "--tools",
                "",
                "--model",
                agent_judge.MODEL,
            ],
            input=prompt,
            cwd=tmp,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    out = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else {}
    text = out.get("result") or ""
    verdict, prob = agent_judge._parse(text)
    record = {
        "request": request,
        "result": text,
        "verdict": verdict,
        "p_fails": prob,
        "cost_usd": out.get("total_cost_usd"),
    }
    if verdict is not None:
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
    return record


def _span(file_text: str, snippet: str) -> tuple[int, int] | None:
    """1-based line range where `snippet` sits in `file_text`, matched on stripped lines."""
    want = [ln.strip() for ln in snippet.strip("\n").splitlines()]
    have = [ln.strip() for ln in file_text.splitlines()]
    for i in range(len(have) - len(want) + 1):
        if have[i : i + len(want)] == want:
            return i + 1, i + len(want)
    return None


def shown_spans(case) -> dict[str, tuple[int, int] | None]:
    """What Jev saw, per file: the hunk in the edited file, the test in its file."""
    project = agent_judge.PROJECTS / f"{case.project}-{case.bug_id}"
    test_file = case.test_id.split("::")[0]
    spans = {}
    for rel, snippet in ((case.edit.path, case.implementation_hunk), (test_file, case.test_source)):
        target = project / rel
        spans[rel] = _span(target.read_text(encoding="utf-8"), snippet) if target.exists() else None
    return spans


def outside_locations(case, answer: str) -> list[str]:
    spans = shown_spans(case)
    points: dict[str, list[int | None]] = {}
    for m in CITE.finditer(answer):
        f = m.group(1).lstrip("./")
        # Normalise to the repo-relative path when the answer cites a suffix.
        match = next((k for k in spans if k == f or k.endswith("/" + f)), f)
        line = int(m.group(2)) if m.group(2) else None
        points.setdefault(match, []).append(line)
    found = []
    for f, lines in points.items():
        span = spans.get(f, "absent")
        if span == "absent":  # a file Jev never saw at all
            numbered = sorted({x for x in lines if x is not None})
            if not numbered:
                found.append(f)
                continue
            clusters = []
            for x in numbered:
                if not clusters or x - clusters[-1][-1] > NEAR:
                    clusters.append([x])
                else:
                    clusters[-1].append(x)
            found += [f"{f}:{c[0]}" for c in clusters]
            continue
        if span is None:
            continue  # cannot place what Jev saw; do not guess
        lo, hi = span
        outside = sorted({x for x in lines if x is not None and not lo <= x <= hi})
        clusters = []
        for x in outside:
            if not clusters or x - clusters[-1][-1] > NEAR:
                clusters.append([x])
            else:
                clusters[-1].append(x)
        found += [f"{f}:{c[0]}" for c in clusters]
    return found


def main() -> int:
    report = json.loads((HERE / "tuning-agent.json").read_text(encoding="utf-8"))
    by_id = {c.case_id: c for c in cases()}
    gap = [
        r
        for r in report["rows"]
        if r["agent"] == r["killed"] and (r["jev_p"] >= 0.5) != r["killed"]
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        bare = list(pool.map(lambda r: no_tools(by_id[r["case_id"]]), gap))

    rows = []
    for r, nt in zip(gap, bare, strict=True):
        case = by_id[r["case_id"]]
        agent_rec = agent_judge.judge(case, replay=True)
        locs = outside_locations(case, agent_rec["result"])
        if nt["verdict"] == r["killed"]:
            category = "smarter-model"
        elif not locs:
            category = "uncited"
        elif len(locs) == 1:
            category = "more-context"
        else:
            category = "multi-step"
        rows.append(
            {
                "case_id": r["case_id"],
                "killed": r["killed"],
                "operator": case.edit.operator,
                "jev_p": r["jev_p"],
                "no_tools_verdict": nt["verdict"],
                "no_tools_p": nt["p_fails"],
                "agent_turns": r["turns"],
                "outside_locations": locs,
                "category": category,
            }
        )
    out = {
        "cases": len(rows),
        "categories": dict(Counter(x["category"] for x in rows)),
        "no_tools_cost_usd": round(sum(x["cost_usd"] or 0 for x in bare), 2),
        "rows": rows,
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
    for x in rows:
        print(
            f"{x['category']:<14} killed={x['killed']!s:<5} jev={x['jev_p']:.2f} "
            f"bare={x['no_tools_verdict']!s:<5}({x['no_tools_p']}) turns={x['agent_turns']} "
            f"{x['operator']:<17} {x['outside_locations']}  {x['case_id'][:60]}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

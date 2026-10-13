"""Does more code help Jev? Reach and fails questions, hunk vs file-level context.

Compared on the same 137 tuning cases:
- reach: ``reach_prompt.body`` (hunk) vs ``context_prompt.reach_body``;
- fails: ``run_jev_framing.body_mutant`` (framed prompt, hunk) vs
  ``context_prompt.fails_body`` (framed prompt, file-level context).

Results are broken down by how much code each case got (``Context.modes``).

Did Jev have the context it needed? For the 49 cases the coding agent
explained (``tuning-agent.json``), every ``file.py:line`` its answer cites is
checked against the line spans Jev was sent. A case is "covered" when every
cited location was sent; otherwise the missing citations are listed, split
into "same file, outside what was sent" and "another file".

Run:  .venv/bin/python docs/experiments/jev/m52/run_context.py
Writes ``tuning-context.json``.
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import agent_judge
import context_prompt as cp
import prompts
import reach_prompt
import recorder
from classify_gap import CITE, no_tools
from run_jev_framing import answers, body_mutant, clears_survivors, with_opus
from run_prompts import _auc, score
from run_reach import NEVER_RUN, RUN_NO_CHANGE
from split import cases, load_split

HERE = Path(__file__).resolve().parent
OUT = HERE / "tuning-context.json"
PER_TOKEN = 0.042 / 1_000_000


def safe_jev(body):
    try:
        return recorder.jev(body)
    except Exception as exc:  # noqa: BLE001 — a refused request is a result here
        return {"error": f"{type(exc).__name__}: {str(exc)[:200]}"}


def covered(case, ctx: cp.Context, answer: str) -> dict:
    test_path = case.test_id.split("::")[0]
    missing_same, missing_other = [], []
    for m in CITE.finditer(answer):
        f = m.group(1).lstrip("./")
        line = int(m.group(2)) if m.group(2) else None
        path = next((k for k in (case.edit.path, test_path) if k == f or k.endswith("/" + f)), None)
        if path is None:
            missing_other.append(f if line is None else f"{f}:{line}")
            continue
        span = ctx.spans.get(path)
        if line is None or span is None:
            # A bare file mention, or a file whose sent part has no line span
            # (imports + test function): only a numbered citation can be placed.
            if span is None and line is not None:
                missing_same.append(f"{path}:{line}")
            continue
        if not span[0] <= line <= span[1]:
            missing_same.append(f"{path}:{line}")
    return {
        "covered": not missing_same and not missing_other,
        "missing_same_file": sorted(set(missing_same)),
        "missing_other_file": sorted(set(missing_other)),
    }


def cv_cost(p_fails, reach, tokens, opus, y, target=0.978, folds=5):
    """5-fold cross-validated accuracy/cost of Jev-then-Opus aiming at `target`."""
    n = len(y)
    rng = random.Random(379)
    fold = [0] * n
    for killed in (True, False):
        idx = [i for i in range(n) if y[i] is killed]
        rng.shuffle(idx)
        for j, i in enumerate(idx):
            fold[i] = j % folds
    grid = [round(i / 50, 2) for i in range(51)]
    rules = [
        (c, lo, hi) for c in (0.0, 0.2, 0.25, 0.3, 0.35) for lo in grid for hi in grid if lo < hi
    ]

    def outcome(i, cut, lo, hi):
        cost = tokens[i][0] * PER_TOKEN + (tokens[i][1] * PER_TOKEN if cut else 0)
        if p_fails[i] >= hi:
            return y[i], cost, 0
        if p_fails[i] <= lo or reach[i] < cut:
            return not y[i], cost, 0
        return opus[i]["verdict"] == y[i], cost + opus[i]["cost_usd"], 1

    right = cost = esc = 0.0
    for f in range(folds):
        train = [i for i in range(n) if fold[i] != f]
        best, best_cost = (0.0, -1.0, 2.0), None
        for rule in rules:
            res = [outcome(i, *rule) for i in train]
            if sum(r[0] for r in res) / len(train) >= target:
                c = sum(r[1] for r in res) / len(train)
                if best_cost is None or c < best_cost:
                    best, best_cost = rule, c
        for i in (i for i in range(n) if fold[i] == f):
            ok, c, e = outcome(i, *best)
            right, cost, esc = right + ok, cost + c, esc + e
    return {
        "accuracy": round(right / n, 3),
        "cost_per_case": round(cost / n, 4),
        "escalated_share": round(esc / n, 3),
    }


def main() -> int:
    tuning = set(load_split()["tuning"])
    usable = []
    for c in cases():
        if c.case_id in tuning:
            try:
                prompts.mutated_hunk(c)
                usable.append(c)
            except prompts.CannotBuild:
                pass
    ids = [c.case_id for c in usable]
    y = [c.killed for c in usable]
    ctxs = {c.case_id: cp.build(c) for c in usable}

    def run(c):
        return (
            safe_jev(cp.reach_body(c)),
            safe_jev(cp.fails_body(c)),
            recorder.jev(reach_prompt.body(c), replay_only=True),
            recorder.jev(body_mutant(c), replay_only=True),
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        recs = list(pool.map(run, usable))
    errors = [
        (ids[i], k, r["error"])
        for i, rs in enumerate(recs)
        for k, r in zip(("reach", "fails"), rs[:2], strict=False)
        if "error" in r
    ]
    if errors:
        print(f"{len(errors)} refused requests; first: {errors[:3]}")
        return 1

    reach_ctx = [answers(r[0])["reaches"] for r in recs]
    fails_ctx = [answers(r[1])["fails"] for r in recs]
    reach_hunk = [answers(r[2])["reaches"] for r in recs]
    fails_hunk = [answers(r[3])["fails"] for r in recs]
    tok = lambda r: r["response"]["usage"]["input_tokens"]
    opus = [no_tools(c) for c in usable]
    label = dict(zip(ids, y, strict=True))
    gap = json.loads((HERE / "tuning-gap-categories.json").read_text(encoding="utf-8"))
    false_pos = {r["case_id"] for r in gap["rows"] if not r["killed"]}

    def reach_stats(p):
        lab = [
            (p[i], ids[i] not in NEVER_RUN)
            for i in range(len(ids))
            if y[i] or ids[i] in NEVER_RUN or ids[i] in RUN_NO_CHANGE
        ]
        return {
            "auc_known_reach": round(_auc(lab), 3),
            "never_run_below_0.5": sum(p[ids.index(k)] < 0.5 for k in NEVER_RUN),
            "kills_below_0.5": sum(p[i] < 0.5 for i in range(len(ids)) if y[i]),
            "lowest_kill": round(min(p[i] for i in range(len(ids)) if y[i]), 3),
            "never_run_below_lowest_kill": sum(
                p[ids.index(k)] < min(p[i] for i in range(len(ids)) if y[i]) for k in NEVER_RUN
            ),
        }

    def fails_stats(p, tokens, reach):
        pd = dict(zip(ids, p, strict=True))
        s = score(list(zip(p, y, strict=True)))
        s["false_fails"] = sum(p[i] >= 0.5 and not y[i] for i in range(len(ids)))
        s["missed_kills"] = sum(p[i] < 0.5 and y[i] for i in range(len(ids)))
        s["of_16_false_positives_below_0.5"] = sum(pd[k] < 0.5 for k in false_pos)
        s["clears_survivors"] = clears_survivors(pd, label)
        jc = {ids[i]: tokens[i][0] * PER_TOKEN for i in range(len(ids))}
        oc = {ids[i]: opus[i]["cost_usd"] for i in range(len(ids))}
        ov = {ids[i]: opus[i]["verdict"] for i in range(len(ids))}
        s["survivors_cleared_then_opus"] = with_opus(
            pd, label, ov, oc, jc, s["clears_survivors"]["lowest_kill_p"] - 0.01
        )
        s["cv_jev_then_opus_aiming_0.978"] = cv_cost(p, reach, tokens, opus, y)
        return s

    tokens_ctx = [(tok(r[1]), tok(r[0])) for r in recs]
    tokens_hunk = [(tok(r[3]), tok(r[2])) for r in recs]
    report: dict = {
        "cases": len(ids),
        "context_modes": dict(
            Counter(
                f"code: {ctxs[k].modes['code'].split(' (')[0]} | test: "
                f"{ctxs[k].modes['test'].split(' (')[0]}"
                for k in ids
            )
        ),
        "mean_input_tokens": {
            "reach_hunk": round(sum(t[1] for t in tokens_hunk) / len(ids)),
            "reach_context": round(sum(t[1] for t in tokens_ctx) / len(ids)),
            "fails_hunk": round(sum(t[0] for t in tokens_hunk) / len(ids)),
            "fails_context": round(sum(t[0] for t in tokens_ctx) / len(ids)),
        },
        "reach": {"hunk": reach_stats(reach_hunk), "context": reach_stats(reach_ctx)},
        "fails": {
            "hunk": fails_stats(fails_hunk, tokens_hunk, reach_hunk),
            "context": fails_stats(fails_ctx, tokens_ctx, reach_ctx),
        },
    }

    # By how much code was sent: AUC of the fails question per group.
    groups = defaultdict(list)
    for i, k in enumerate(ids):
        full = ctxs[k].modes["code"] == "whole file" and ctxs[k].modes["test"] == "whole file"
        groups["both whole files" if full else "trimmed"].append(i)
    report["fails_by_context"] = {
        g: {
            "n": len(idx),
            "killed": sum(y[i] for i in idx),
            "auc_hunk": round(_auc([(fails_hunk[i], y[i]) for i in idx]), 3),
            "auc_context": round(_auc([(fails_ctx[i], y[i]) for i in idx]), 3),
            "acc_hunk": round(sum((fails_hunk[i] >= 0.5) == y[i] for i in idx) / len(idx), 3),
            "acc_context": round(sum((fails_ctx[i] >= 0.5) == y[i] for i in idx) / len(idx), 3),
        }
        for g, idx in groups.items()
    }

    # Did Jev have what the agent needed?
    agent = json.loads((HERE / "tuning-agent.json").read_text(encoding="utf-8"))
    by_id = {c.case_id: c for c in usable}
    cov_rows = []
    for row in agent["rows"]:
        k = row["case_id"]
        c = by_id[k]
        ans = agent_judge.judge(c, replay=True)["result"]
        cv = covered(c, ctxs[k], ans)
        i = ids.index(k)
        cov_rows.append(
            {
                "case_id": k,
                "killed": c.killed,
                "code": ctxs[k].modes["code"].split(" (")[0],
                "test": ctxs[k].modes["test"].split(" (")[0],
                **cv,
                "fails_hunk": round(fails_hunk[i], 2),
                "fails_context": round(fails_ctx[i], 2),
                "reach_hunk": round(reach_hunk[i], 2),
                "reach_context": round(reach_ctx[i], 2),
            }
        )

    def right(r, key):
        return (r[key] >= 0.5) == r["killed"]

    report["agent_cases_coverage"] = {
        "n": len(cov_rows),
        "covered": sum(r["covered"] for r in cov_rows),
        "missing_same_file_only": sum(
            (not r["covered"]) and not r["missing_other_file"] for r in cov_rows
        ),
        "missing_other_file": sum(bool(r["missing_other_file"]) for r in cov_rows),
        "right_hunk_vs_context_when_covered": [
            sum(right(r, "fails_hunk") for r in cov_rows if r["covered"]),
            sum(right(r, "fails_context") for r in cov_rows if r["covered"]),
        ],
        "right_hunk_vs_context_when_not": [
            sum(right(r, "fails_hunk") for r in cov_rows if not r["covered"]),
            sum(right(r, "fails_context") for r in cov_rows if not r["covered"]),
        ],
        "rows": cov_rows,
    }
    report["case_modes"] = {k: ctxs[k].modes for k in ids}
    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    printable = {k: v for k, v in report.items() if k not in ("case_modes",)}
    printable["agent_cases_coverage"] = {
        k: v for k, v in report["agent_cases_coverage"].items() if k != "rows"
    }
    print(json.dumps(printable, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

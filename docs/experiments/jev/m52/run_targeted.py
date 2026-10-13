"""Hunk vs file-level vs targeted context for Jev, on the same tuning cases.

Fails question (framed) and reach question (minimal), three ways:
- hunk: ``run_jev_framing.body_mutant`` / ``reach_prompt.body``;
- file-level: ``context_prompt.fails_body`` / ``reach_body``;
- targeted: ``targeted_prompt.fails_body`` / ``reach_body``.

Broken down by the file-level run's groups ("both whole files" vs "trimmed"),
since that split was confounded with project; and, for the 49 cases the coding
agent explained, whether every location its answer cites was sent.

Run:  .venv/bin/python docs/experiments/jev/m52/run_targeted.py
Writes ``tuning-targeted.json``.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import agent_judge
import context_prompt as cp
import prompts
import reach_prompt
import recorder
import targeted_prompt as tp
from classify_gap import CITE, no_tools
from run_context import cv_cost
from run_jev_framing import answers, body_mutant
from run_prompts import _auc, score
from run_reach import NEVER_RUN, RUN_NO_CHANGE
from split import cases, load_split

HERE = Path(__file__).resolve().parent
OUT = HERE / "tuning-targeted.json"


def safe(body):
    try:
        return recorder.jev(body)
    except Exception as exc:  # noqa: BLE001 — a refused request is a result here
        return {"error": f"{type(exc).__name__}: {str(exc)[:200]}"}


def covered(case, spans: dict[str, list[tuple[int, int]]], answer: str) -> bool:
    for m in CITE.finditer(answer):
        f = m.group(1).lstrip("./")
        if not m.group(2):
            continue  # a bare file mention cannot be placed
        line = int(m.group(2))
        path = next((k for k in spans if k == f or k.endswith("/" + f)), None)
        if path is None or not any(a <= line <= b for a, b in spans[path]):
            return False
    return True


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

    def run(c):
        return {
            "fails": {
                "hunk": recorder.jev(body_mutant(c), replay_only=True),
                "file": recorder.jev(cp.fails_body(c), replay_only=True),
                "targeted": safe(tp.fails_body(c)),
            },
            "reach": {
                "hunk": recorder.jev(reach_prompt.body(c), replay_only=True),
                "file": recorder.jev(cp.reach_body(c), replay_only=True),
                "targeted": safe(tp.reach_body(c)),
            },
        }

    with ThreadPoolExecutor(max_workers=8) as pool:
        recs = list(pool.map(run, usable))
    errors = [
        (ids[i], q, k, r["error"])
        for i, rs in enumerate(recs)
        for q in rs
        for k, r in rs[q].items()
        if "error" in r
    ]
    if errors:
        print(f"{len(errors)} refused; first: {errors[:3]}")
        return 1

    key = {"fails": "fails", "reach": "reaches"}
    p = {
        q: {k: [answers(r[q][k])[key[q]] for r in recs] for k in ("hunk", "file", "targeted")}
        for q in ("fails", "reach")
    }
    tok = {
        k: [
            (
                r["fails"][k]["response"]["usage"]["input_tokens"],
                r["reach"][k]["response"]["usage"]["input_tokens"],
            )
            for r in recs
        ]
        for k in ("hunk", "file", "targeted")
    }
    opus = [no_tools(c) for c in usable]
    gap = json.loads((HERE / "tuning-gap-categories.json").read_text(encoding="utf-8"))
    false_pos = {r["case_id"] for r in gap["rows"] if not r["killed"]}
    ctx_report = json.loads((HERE / "tuning-context.json").read_text(encoding="utf-8"))
    whole = {
        k
        for k, m in ctx_report["case_modes"].items()
        if m["code"] == "whole file" and m["test"] == "whole file"
    }

    report: dict = {"cases": len(ids), "fails": {}, "reach": {}, "by_group": {}}
    for k in ("hunk", "file", "targeted"):
        pf, pr = p["fails"][k], p["reach"][k]
        s = score(list(zip(pf, y, strict=True)))
        s["false_fails"] = sum(pf[i] >= 0.5 and not y[i] for i in range(len(ids)))
        s["missed_kills"] = sum(pf[i] < 0.5 and y[i] for i in range(len(ids)))
        s["of_16_false_positives_below_0.5"] = sum(pf[ids.index(c)] < 0.5 for c in false_pos)
        s["mean_input_tokens"] = round(sum(t[0] for t in tok[k]) / len(ids))
        s["cv_jev_then_opus_aiming_0.978"] = cv_cost(pf, pr, tok[k], opus, y)
        report["fails"][k] = s
        lab = [
            (pr[i], ids[i] not in NEVER_RUN)
            for i in range(len(ids))
            if y[i] or ids[i] in NEVER_RUN or ids[i] in RUN_NO_CHANGE
        ]
        low_kill = min(pr[i] for i in range(len(ids)) if y[i])
        report["reach"][k] = {
            "auc_known_reach": round(_auc(lab), 3),
            "never_run_below_0.5": sum(pr[ids.index(c)] < 0.5 for c in NEVER_RUN),
            "kills_below_0.5": sum(pr[i] < 0.5 for i in range(len(ids)) if y[i]),
            "never_run_below_lowest_kill": sum(pr[ids.index(c)] < low_kill for c in NEVER_RUN),
            "mean_input_tokens": round(sum(t[1] for t in tok[k]) / len(ids)),
        }
    for g, members in (("both whole files", whole), ("trimmed", set(ids) - whole)):
        idx = [i for i, k in enumerate(ids) if k in members]
        report["by_group"][g] = {
            "n": len(idx),
            **{
                f"fails_auc_{k}": round(_auc([(p["fails"][k][i], y[i]) for i in idx]), 3)
                for k in ("hunk", "file", "targeted")
            },
        }

    agent = json.loads((HERE / "tuning-agent.json").read_text(encoding="utf-8"))
    by_id = {c.case_id: c for c in usable}
    rows = []
    for row in agent["rows"]:
        c = by_id[row["case_id"]]
        ans = agent_judge.judge(c, replay=True)["result"]
        t = tp.build(c)
        file_ctx = cp.build(c)
        file_spans = {k: [v] for k, v in file_ctx.spans.items()}
        i = ids.index(c.case_id)
        rows.append(
            {
                "case_id": c.case_id,
                "covered_targeted": covered(c, t.spans, ans),
                "covered_file": covered(c, file_spans, ans),
                "right": {
                    k: (p["fails"][k][i] >= 0.5) == y[i] for k in ("hunk", "file", "targeted")
                },
            }
        )
    report["agent_cases"] = {
        "n": len(rows),
        "covered_targeted": sum(r["covered_targeted"] for r in rows),
        "covered_file": sum(r["covered_file"] for r in rows),
        "right_at_0.5": {k: sum(r["right"][k] for r in rows) for k in ("hunk", "file", "targeted")},
    }
    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

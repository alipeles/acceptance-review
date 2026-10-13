"""The best single Jev prompt, told when a reach check is confident the line runs.

The fails question is the framed prompt over the mutated code
(``run_jev_framing.body_mutant``). When the minimal reach question
(``reach_prompt``) scores at least ``THRESHOLD``, one extra field is added to
the state saying so; below it, the request is unchanged and replays from its
existing recording.

One-way on purpose: on the tuning cases with known reach, every case scoring
0.85 or more does run the edited line, while low scores are not trustworthy
(8 kills score below 0.5).

Run:  .venv/bin/python docs/experiments/jev/m52/run_reach_hint.py
Writes ``tuning-reach-hint.json``.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import prompts
import reach_prompt
import recorder
from classify_gap import no_tools
from run_jev_framing import answers, body_mutant, clears_survivors, with_opus
from run_prompts import score
from split import cases, load_split
from thresholds import calibration

HERE = Path(__file__).resolve().parent
OUT = HERE / "tuning-reach-hint.json"
THRESHOLD = 0.85
JEV_PER_TOKEN = 0.042 / 1_000_000

HINT = (
    "A separate check has already looked at whether this test executes the edited line, "
    "and found that it very likely does (estimated probability {p:.0%}). That settles only "
    "the first condition. The test catches the mutant only if the edit also changes "
    "something the test asserts on."
)


def hinted_body(case, reach_p: float) -> dict:
    b = body_mutant(case)
    if reach_p >= THRESHOLD:
        state = {"situation": b["state"]["situation"], "execution_check": HINT.format(p=reach_p)}
        state.update({k: v for k, v in b["state"].items() if k != "situation"})
        b = {**b, "state": state}
    return b


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
    label = {c.case_id: c.killed for c in usable}
    gap = json.loads((HERE / "tuning-gap-categories.json").read_text(encoding="utf-8"))
    false_pos = {r["case_id"] for r in gap["rows"] if not r["killed"]}

    def run(c):
        reach = recorder.jev(reach_prompt.body(c), replay_only=True)
        rp = answers(reach)["reaches"]
        plain = recorder.jev(body_mutant(c), replay_only=True)
        hinted = recorder.jev(hinted_body(c, rp))
        return c.case_id, rp, reach, plain, hinted

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(run, usable))

    opus, opus_cost = {}, {}
    for c in usable:
        o = no_tools(c)
        opus[c.case_id], opus_cost[c.case_id] = o["verdict"], o["cost_usd"]

    reach_p = {cid: rp for cid, rp, *_ in results}
    probs = {
        "framed+mutant": {cid: answers(pl)["fails"] for cid, _, _, pl, _ in results},
        "with reach hint": {cid: answers(h)["fails"] for cid, _, _, _, h in results},
    }
    cost = {
        "framed+mutant": {
            cid: pl["response"]["usage"]["input_tokens"] * JEV_PER_TOKEN
            for cid, _, _, pl, _ in results
        },
        # Two Jev calls: the reach question, then the (possibly hinted) fails question.
        "with reach hint": {
            cid: (r["response"]["usage"]["input_tokens"] + h["response"]["usage"]["input_tokens"])
            * JEV_PER_TOKEN
            for cid, _, r, _, h in results
        },
    }
    hinted = {k for k, p in reach_p.items() if p >= THRESHOLD}

    report: dict = {
        "cases": len(label),
        "threshold": THRESHOLD,
        "hinted_cases": len(hinted),
        "hinted_killed": sum(label[k] for k in hinted),
        "variants": {},
    }
    for name, p in probs.items():
        s = score([(p[k], label[k]) for k in label])
        s["ece"] = calibration(p, label)["ece"]
        s["false_fails"] = sum(p[k] >= 0.5 and not label[k] for k in label)
        s["missed_kills"] = sum(p[k] < 0.5 and label[k] for k in label)
        s["of_16_false_positives_below_0.5"] = sum(p[k] < 0.5 for k in false_pos)
        s["on_hinted_cases"] = {
            "missed_kills": sum(p[k] < 0.5 and label[k] for k in hinted),
            "false_fails": sum(p[k] >= 0.5 and not label[k] for k in hinted),
        }
        s["clears_survivors"] = clears_survivors(p, label)
        lo = s["clears_survivors"]["lowest_kill_p"] - 0.01
        s["survivors_cleared_then_opus"] = with_opus(p, label, opus, opus_cost, cost[name], lo)
        report["variants"][name] = s
    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

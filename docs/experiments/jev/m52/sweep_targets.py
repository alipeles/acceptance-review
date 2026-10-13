"""Cheapest Jev-then-Opus rule reaching each accuracy target, per Jev prompt.

For each Jev "fails" prompt: Jev says "fails" at p >= hi and "survives" at
p <= lo; optionally the minimal reach question also clears a case as
"survives" when its reach score is below ``reach_cut``; Opus (no tools)
judges everything else. Replays recordings only. Tuning cases, so optimistic.

Run:  .venv/bin/python docs/experiments/jev/m52/sweep_targets.py
Writes ``tuning-sweep-targets.json``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import prompts
import reach_prompt
import recorder
from classify_gap import no_tools
from run_jev_framing import ONE_QUESTION, answers, body_mutant
from run_jev_framing import body as framed_body
from split import cases, load_split

HERE = Path(__file__).resolve().parent
OUT = HERE / "tuning-sweep-targets.json"
PER_TOKEN = 0.042 / 1_000_000
GRID = [round(i / 100, 2) for i in range(101)]
REACH_CUTS = [0.0, 0.2, 0.25, 0.27, 0.3, 0.35, 0.4]
TARGETS = (0.978, 0.971, 0.964, 0.956, 0.95, 0.942, 0.934, 0.927, 0.92, 0.912)

PROMPTS = {
    "context+description": lambda c: prompts.jev_body(c, "context+description"),
    "framed": lambda c: framed_body(c, ONE_QUESTION),
    "framed+mutant": body_mutant,
}


def tokens(rec) -> int:
    return rec["response"]["usage"]["input_tokens"]


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
    n = len(usable)
    y = [c.killed for c in usable]
    opus = [no_tools(c) for c in usable]
    reach_rec = [recorder.jev(reach_prompt.body(c), replay_only=True) for c in usable]
    reach = [answers(r)["reaches"] for r in reach_rec]

    report: dict = {"cases": n, "opus_alone_cost": round(sum(o["cost_usd"] for o in opus) / n, 4)}
    for name, build in PROMPTS.items():
        recs = [recorder.jev(build(c), replay_only=True) for c in usable]
        p = [answers(r)["fails"] if "fails" in answers(r) else recorder.jev_p_yes(r) for r in recs]
        options = []
        for cut in REACH_CUTS:
            for lo in GRID:
                for hi in GRID:
                    if lo >= hi:
                        continue
                    right, cost, esc = 0, 0.0, 0
                    for i in range(n):
                        cost += tokens(recs[i]) * PER_TOKEN
                        if cut:
                            cost += tokens(reach_rec[i]) * PER_TOKEN
                        if p[i] >= hi:
                            says = True
                        elif p[i] <= lo or reach[i] < cut:
                            says = False
                        else:
                            says, esc = opus[i]["verdict"], esc + 1
                            cost += opus[i]["cost_usd"]
                        right += says == y[i]
                    options.append(
                        {
                            "reach_cut": cut,
                            "lo": lo,
                            "hi": hi,
                            "accuracy": round(right / n, 3),
                            "escalated_share": round(esc / n, 3),
                            "cost_per_case": round(cost / n, 4),
                        }
                    )
        best = {}
        for t in TARGETS:
            ok = [o for o in options if o["accuracy"] >= t]
            best[str(t)] = min(ok, key=lambda o: o["cost_per_case"]) if ok else None
        report[name] = best

    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print("opus alone", report["opus_alone_cost"])
    for name in PROMPTS:
        print(f"== {name}")
        for t, o in report[name].items():
            print(
                f"  >= {t}: ${o['cost_per_case']}  acc {o['accuracy']}  opus {o['escalated_share']}  "
                f"lo {o['lo']} hi {o['hi']} reach<{o['reach_cut']}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())

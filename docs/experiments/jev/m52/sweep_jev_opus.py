"""Jev first, Opus on the rest: accuracy and cost at every threshold pair.

Replays recordings only. Jev's cost is its recorded input tokens at the
launch price ($0.042 per million input tokens, output free); Opus's is each
case's recorded `total_cost_usd`. Jev is called on every case; Opus only on
the cases Jev passes on.

Thresholds are chosen and scored on the same 137 tuning cases, so every
figure here is optimistic.

Run:  .venv/bin/python docs/experiments/jev/m52/sweep_jev_opus.py
Writes ``tuning-sweep-jev-opus.json``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import prompts
import recorder
from classify_gap import no_tools
from split import cases, load_split

HERE = Path(__file__).resolve().parent
OUT = HERE / "tuning-sweep-jev-opus.json"
VARIANT = "context+description"
JEV_PER_TOKEN = 0.042 / 1_000_000
GRID = [round(i / 100, 2) for i in range(101)]


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
    jev_p, jev_cost, opus, opus_cost = {}, {}, {}, {}
    for c in usable:
        rec = recorder.jev(prompts.jev_body(c, VARIANT), replay_only=True)
        jev_p[c.case_id] = recorder.jev_p_yes(rec)
        jev_cost[c.case_id] = rec["response"]["usage"]["input_tokens"] * JEV_PER_TOKEN
        o = no_tools(c)  # cached; never live here
        opus[c.case_id] = o["verdict"]
        opus_cost[c.case_id] = o["cost_usd"]
    n = len(label)

    def run(lo, hi):
        right = escalated = 0
        cost = 0.0
        for k, y in label.items():
            cost += jev_cost[k]
            if jev_p[k] >= hi:
                says = True
            elif jev_p[k] <= lo:
                says = False
            else:
                says = opus[k]
                escalated += 1
                cost += opus_cost[k]
            right += says == y
        return {
            "lo": lo,
            "hi": hi,
            "accuracy": round(right / n, 3),
            "wrong": n - right,
            "escalated_share": round(escalated / n, 3),
            "cost_per_case": round(cost / n, 5),
        }

    options = [run(lo, hi) for lo in GRID for hi in GRID if lo < hi]
    opus_only = run(-1, 2)

    def cheapest(min_acc):
        ok = [o for o in options if o["accuracy"] >= min_acc]
        return min(ok, key=lambda o: (o["cost_per_case"], -o["accuracy"])) if ok else None

    report = {
        "cases": n,
        "jev_cost_per_case": round(sum(jev_cost.values()) / n, 7),
        "opus_cost_per_case": round(sum(opus_cost.values()) / n, 4),
        "opus_only": opus_only,
        "current_thresholds": run(0.47, 0.84),
        "cheapest_at_least": {
            str(a): cheapest(a) for a in (0.978, 0.971, 0.964, 0.956, 0.949, 0.934)
        },
        "jev_p_by_label": {
            "survived": sorted(round(jev_p[k], 2) for k, y in label.items() if not y),
            "killed": sorted(round(jev_p[k], 2) for k, y in label.items() if y),
        },
    }
    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "jev_p_by_label"}, indent=1))
    print("Jev p, survived:", report["jev_p_by_label"]["survived"])
    print("Jev p, killed:  ", report["jev_p_by_label"]["killed"])
    return 0


if __name__ == "__main__":
    sys.exit(main())

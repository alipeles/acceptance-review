"""Cross-validated cost and accuracy of the Jev-then-Opus rule at an accuracy target.

``sweep_targets.py`` picks the cheapest rule on the same cases it scores, which
flatters it. Here the tuning cases are split into 5 folds (stratified by label,
fixed seed); the rule is chosen on 4 folds (cheapest meeting the target there)
and scored on the fifth. Reported: pooled accuracy and cost over all 5 scored
folds. Still tuning cases only; the held-out set is untouched.

Run:  .venv/bin/python docs/experiments/jev/m52/cv_targets.py
Writes ``tuning-cv-targets.json``.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import prompts
import reach_prompt
import recorder
from classify_gap import no_tools
from run_jev_framing import ONE_QUESTION, answers, body_mutant
from run_jev_framing import body as framed_body
from split import cases, load_split
from sweep_targets import PER_TOKEN, tokens

HERE = Path(__file__).resolve().parent
OUT = HERE / "tuning-cv-targets.json"
GRID = [round(i / 50, 2) for i in range(51)]
REACH_CUTS = [0.0, 0.2, 0.25, 0.3, 0.35]
TARGETS = (0.978, 0.95, 0.92)
FOLDS = 5

PROMPTS = {
    "context+description": lambda c: prompts.jev_body(c, "context+description"),
    "framed": lambda c: framed_body(c, ONE_QUESTION),
    "framed+mutant": body_mutant,
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
    n = len(usable)
    rng = random.Random(379)
    fold = [0] * n
    for killed in (True, False):
        idx = [i for i, c in enumerate(usable) if c.killed is killed]
        rng.shuffle(idx)
        for j, i in enumerate(idx):
            fold[i] = j % FOLDS

    y = [c.killed for c in usable]
    opus = [no_tools(c) for c in usable]
    reach_rec = [recorder.jev(reach_prompt.body(c), replay_only=True) for c in usable]
    reach = [answers(r)["reaches"] for r in reach_rec]
    report: dict = {"cases": n, "folds": FOLDS}

    for name, build in PROMPTS.items():
        recs = [recorder.jev(build(c), replay_only=True) for c in usable]
        p = [answers(r)["fails"] if "fails" in answers(r) else recorder.jev_p_yes(r) for r in recs]

        def outcome(i, cut, lo, hi, recs=recs, p=p):
            cost = tokens(recs[i]) * PER_TOKEN + (tokens(reach_rec[i]) * PER_TOKEN if cut else 0)
            if p[i] >= hi:
                return y[i], cost, 0
            if p[i] <= lo or reach[i] < cut:
                return not y[i], cost, 0
            return opus[i]["verdict"] == y[i], cost + opus[i]["cost_usd"], 1

        rules = [(cut, lo, hi) for cut in REACH_CUTS for lo in GRID for hi in GRID if lo < hi]
        per_target = {}
        for t in TARGETS:
            right = cost = esc = 0.0
            for f in range(FOLDS):
                train = [i for i in range(n) if fold[i] != f]
                test = [i for i in range(n) if fold[i] == f]
                best, best_cost = (0.0, -1.0, 2.0), None  # fallback: Opus on everything
                for rule in rules:
                    res = [outcome(i, *rule) for i in train]
                    acc = sum(r[0] for r in res) / len(train)
                    c = sum(r[1] for r in res) / len(train)
                    if acc >= t and (best_cost is None or c < best_cost):
                        best, best_cost = rule, c
                for i in test:
                    ok, c, e = outcome(i, *best)
                    right += ok
                    cost += c
                    esc += e
            per_target[str(t)] = {
                "accuracy": round(right / n, 3),
                "cost_per_case": round(cost / n, 4),
                "escalated_share": round(esc / n, 3),
            }
        report[name] = per_target

    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Freeze the designs scored on the held-out set, from tuning recordings only.

Every rule here is chosen on the 137 usable tuning cases and written to
``frozen.json`` before ``score_heldout.py`` reads a single held-out case. The
held-out set is scored once, against exactly what this file wrote.

Designs:

- ``A``: the shipped judge (``defects/pair_mapping.py`` ``_batches``/``_ask``).
- ``opus``: no-tools Opus 5.5 on every case (``classify_gap.no_tools``).
- ``jev_targeted``: Jev alone, targeted-context fails prompt, "fails" at >= 0.5.
- ``jev_then_opus/<prompt>/<target>``: Jev first; "fails" when p >= hi;
  "survives" when p <= lo or the reach score < cut; otherwise Opus decides.
  ``targeted`` uses ``targeted_prompt`` for both questions; ``hunk`` uses the
  framed mutated-code prompt and the minimal reach prompt. The rule is the
  cheapest (cut, lo, hi) whose accuracy on all tuning cases meets the target.

Declared before scoring, for held-out cases:
- a case whose Jev request cannot be built, or is refused, goes to Opus;
- an Opus answer with no parseable verdict counts as wrong;
- an A pair with no verdict counts as wrong.
The primary design is ``jev_then_opus/targeted/0.978``.

Run:  .venv/bin/python docs/experiments/jev/m52/freeze.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import prompts
import reach_prompt
import recorder
import targeted_prompt as tp
from classify_gap import no_tools
from run_jev_framing import answers, body_mutant
from split import cases, load_split
from sweep_targets import PER_TOKEN, tokens

HERE = Path(__file__).resolve().parent
OUT = HERE / "frozen.json"
GRID = [round(i / 50, 2) for i in range(51)]
REACH_CUTS = [0.0, 0.2, 0.25, 0.3, 0.35]
TARGETS = (0.978, 0.95)
PROMPTS = {
    "targeted": (tp.fails_body, tp.reach_body),
    "hunk": (body_mutant, reach_prompt.body),
}


def outcome(p_fails, reach, fails_tok, reach_tok, opus_ok, opus_cost, killed, rule):
    """(right, cost, escalated) for one case under rule (cut, lo, hi)."""
    cut, lo, hi = rule
    cost = fails_tok * PER_TOKEN + (reach_tok * PER_TOKEN if cut else 0)
    if p_fails >= hi:
        return killed, cost, 0
    if p_fails <= lo or reach < cut:
        return not killed, cost, 0
    return opus_ok, cost + opus_cost, 1


def fit(rows, target):
    """Cheapest rule meeting `target` on rows; Opus on everything if none does."""
    best, best_cost = (0.0, -1.0, 2.0), None
    for cut in REACH_CUTS:
        for lo in GRID:
            for hi in GRID:
                if lo >= hi:
                    continue
                res = [outcome(*r, (cut, lo, hi)) for r in rows]
                acc = sum(x[0] for x in res) / len(rows)
                cost = sum(x[1] for x in res) / len(rows)
                if acc >= target and (best_cost is None or cost < best_cost):
                    best, best_cost = (cut, lo, hi), cost
    res = [outcome(*r, best) for r in rows]
    return {
        "rule": {"reach_cut": best[0], "lo": best[1], "hi": best[2]},
        "tuning_accuracy": round(sum(x[0] for x in res) / len(rows), 3),
        "tuning_cost_per_case": round(sum(x[1] for x in res) / len(rows), 4),
        "tuning_escalated_share": round(sum(x[2] for x in res) / len(rows), 3),
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
    opus = [no_tools(c) for c in usable]
    frozen: dict = {"tuning_cases": len(usable), "primary": "jev_then_opus/targeted/0.978"}
    frozen["designs"] = {
        "A": {"what": "shipped judge, gpt-5.4-mini batched"},
        "opus": {"what": "no-tools Opus 5.5, context+description prompt"},
        "jev_targeted": {"what": "Jev alone, targeted fails prompt", "rule": {"hi": 0.5}},
    }
    for name, (fails_body, reach_body) in PROMPTS.items():
        rows = []
        for c, o in zip(usable, opus, strict=True):
            f = recorder.jev(fails_body(c), replay_only=True)
            r = recorder.jev(reach_body(c), replay_only=True)
            rows.append(
                (
                    answers(f)["fails"],
                    answers(r)["reaches"],
                    tokens(f),
                    tokens(r),
                    o["verdict"] == c.killed,
                    o["cost_usd"],
                    c.killed,
                )
            )
        for t in TARGETS:
            frozen["designs"][f"jev_then_opus/{name}/{t}"] = {
                "what": f"Jev ({name} prompts) then Opus, rule fit on tuning aiming {t}",
                **fit(rows, t),
            }
    OUT.write_text(json.dumps(frozen, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(frozen, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

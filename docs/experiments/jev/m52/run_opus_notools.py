"""No-tools Opus on every tuning case, alone and as Jev's escalation judge.

Same call as ``classify_gap.no_tools``: `claude -p --tools ""`, Opus 5.5, the
"context + description" content Jev and Mini see. Recorded under
``.acceptance/cache/jev-m52-notools/``.

Compared on the same 137 cases:
- Opus alone;
- Jev decides at the thresholds chosen in ``thresholds.py``, Opus takes the
  rest (approach C with Opus in place of the current judge);
- the same rule with the current judge (approach C as chosen), for reference.

Run:  .venv/bin/python docs/experiments/jev/m52/run_opus_notools.py
Writes ``tuning-opus-notools.json``.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import prompts
import recorder
from classify_gap import no_tools
from run_prompts import score
from split import cases, load_split
from thresholds import calibration

HERE = Path(__file__).resolve().parent
OUT = HERE / "tuning-opus-notools.json"
VARIANT = "context+description"


def summarise(says: dict[str, bool], label: dict[str, bool]) -> dict:
    tp = sum(says[k] and label[k] for k in label)
    fp = sum(says[k] and not label[k] for k in label)
    return {
        "accuracy": round(sum(says[k] == label[k] for k in label) / len(label), 3),
        "precision_fails": round(tp / (tp + fp), 3) if tp + fp else None,
        "wrong": sum(says[k] != label[k] for k in label),
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
    label = {c.case_id: c.killed for c in usable}

    with ThreadPoolExecutor(max_workers=4) as pool:
        records = dict(zip(label, pool.map(no_tools, usable), strict=True))
    missing = [k for k, r in records.items() if r["verdict"] is None]
    if missing:
        print(f"no verdict for {len(missing)} cases; rerun to retry them: {missing[:3]}")
        return 1

    opus_p = {
        k: r["p_fails"] if r["p_fails"] is not None else float(r["verdict"])
        for k, r in records.items()
    }
    opus = {k: r["verdict"] for k, r in records.items()}
    jev_p = {
        c.case_id: recorder.jev_p_yes(recorder.jev(prompts.jev_body(c, VARIANT), replay_only=True))
        for c in usable
    }
    t = json.loads((HERE / "tuning-thresholds.json").read_text(encoding="utf-8"))
    lo, hi = t["jev"]["chosen"]["lo"], t["jev"]["chosen"]["hi"]
    a = json.loads((HERE / "tuning-judge-a.json").read_text(encoding="utf-8"))["verdicts"]

    def hybrid(fallback):
        return {
            k: True if jev_p[k] >= hi else False if jev_p[k] <= lo else fallback[k] for k in label
        }

    costs = [r["cost_usd"] for r in records.values() if r["cost_usd"] is not None]
    report = {
        "cases": len(label),
        "thresholds": {"lo": lo, "hi": hi},
        "opus_alone": {
            **summarise(opus, label),
            **{k: v for k, v in score([(opus_p[k], label[k]) for k in label]).items() if k != "n"},
            "ece": calibration(opus_p, label)["ece"],
            "mean_cost_usd": round(sum(costs) / len(costs), 3),
        },
        "jev_alone": summarise({k: jev_p[k] >= 0.5 for k in label}, label),
        "jev_then_opus": summarise(hybrid(opus), label),
        "jev_then_current_judge": summarise(hybrid(a), label),
        "current_judge_alone": summarise(a, label),
        "opus_wrong": sorted(k for k in label if opus[k] != label[k]),
        "total_cost_usd": round(sum(costs), 2),
    }
    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

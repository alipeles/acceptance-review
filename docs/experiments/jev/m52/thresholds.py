"""Choose approach C's and D's thresholds on the tuning set, and measure calibration.

C: Jev decides "fails" when p >= hi and "survives" when p <= lo; every other
case goes to the current judge (approach A). D: the same rule on Mini's token
probabilities. One threshold per answer, because a false "fails" (a test
credited with catching a defect it misses) is the costly error.

Choice rule, from #371's adoption bar: among threshold pairs where the
combined answer's precision on "fails" is at least A's, and the model decides
at least half the cases, take the most accurate; ties go to more decided.

Thresholds chosen and scored on the same cases flatter themselves, so these
are tuning figures only. The held-out set is scored once, later, with the
thresholds frozen here.

Replays recordings only.
Run:  .venv/bin/python docs/experiments/jev/m52/thresholds.py
Writes ``tuning-thresholds.json``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import prompts
import recorder
from split import cases, load_split

HERE = Path(__file__).resolve().parent
VARIANT = "context+description"
OUT = HERE / "tuning-thresholds.json"
GRID = [round(i / 100, 2) for i in range(0, 101, 1)]


def probabilities(provider: str, usable) -> dict[str, float]:
    out = {}
    for c in usable:
        if provider == "jev":
            rec = recorder.jev(prompts.jev_body(c, VARIANT), replay_only=True)
            out[c.case_id] = recorder.jev_p_yes(rec)
        else:
            rec = recorder.mini(
                recorder.mini_request(prompts.mini_messages(c, VARIANT)), replay_only=True
            )
            out[c.case_id] = recorder.mini_p_yes(rec)
    return out


def combined(p, a, label, lo, hi) -> dict:
    tp = fp = correct = decided = 0
    for cid, y in label.items():
        if p[cid] >= hi:
            says, decided = True, decided + 1
        elif p[cid] <= lo:
            says, decided = False, decided + 1
        else:
            says = a[cid]
        correct += says == y
        tp += says and y
        fp += says and not y
    n = len(label)
    return {
        "lo": lo,
        "hi": hi,
        "accuracy": round(correct / n, 3),
        "precision_fails": round(tp / (tp + fp), 3) if tp + fp else None,
        "decided_share": round(decided / n, 3),
    }


def calibration(p, label, bins=5) -> dict:
    rows = []
    ece = 0.0
    n = len(label)
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        ids = [cid for cid in label if lo <= p[cid] < hi or (b == bins - 1 and p[cid] == 1.0)]
        if not ids:
            rows.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": 0})
            continue
        conf = sum(p[i] for i in ids) / len(ids)
        freq = sum(label[i] for i in ids) / len(ids)
        ece += len(ids) / n * abs(conf - freq)
        rows.append(
            {
                "bin": f"{lo:.1f}-{hi:.1f}",
                "n": len(ids),
                "mean_p": round(conf, 3),
                "share_killed": round(freq, 3),
            }
        )
    return {"ece": round(ece, 3), "bins": rows}


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
    a_report = json.loads((HERE / "tuning-judge-a.json").read_text(encoding="utf-8"))
    a = a_report["verdicts"]
    a_precision = a_report["precision_killed"]

    report: dict = {
        "variant": VARIANT,
        "a": {"accuracy": a_report["accuracy"], "precision_fails": a_precision},
    }
    for provider in ("jev", "mini"):
        p = probabilities(provider, usable)
        options = [combined(p, a, label, lo, hi) for lo in GRID for hi in GRID if lo < 0.5 <= hi]
        ok = [
            o
            for o in options
            if o["precision_fails"] is not None
            and o["precision_fails"] >= a_precision
            and o["decided_share"] >= 0.5
        ]
        best = max(ok, key=lambda o: (o["accuracy"], o["decided_share"])) if ok else None
        argmax = combined(p, a, label, 0.4999, 0.5)
        report[provider] = {
            "alone": {"accuracy": argmax["accuracy"], "precision_fails": argmax["precision_fails"]},
            "chosen": best,
            "calibration": calibration(p, label),
        }

    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

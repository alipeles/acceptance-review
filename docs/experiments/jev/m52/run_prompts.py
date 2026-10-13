"""Run the four prompt variants for Jev and Mini over the tuning set, and score them.

Tuning set only; the held-out set is never touched here. Cases whose mutated
code cannot be built are left out of every variant, so all variants are
scored on the same cases.

Run:  .venv/bin/python docs/experiments/jev/m52/run_prompts.py [--replay]
Writes aggregate scores to ``tuning-prompts.json`` beside this file.
"""

from __future__ import annotations

import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import prompts
import recorder
from split import cases, load_split

HERE = Path(__file__).resolve().parent
OUT = HERE / "tuning-prompts.json"


def _auc(pairs: list[tuple[float, bool]]) -> float:
    pos = [p for p, y in pairs if y]
    neg = [p for p, y in pairs if not y]
    wins = sum((p > n) + 0.5 * (p == n) for p in pos for n in neg)
    return wins / (len(pos) * len(neg))


def score(pairs: list[tuple[float, bool]]) -> dict:
    n = len(pairs)
    eps = 1e-6
    killed = [p for p, y in pairs if y]
    survived = [p for p, y in pairs if not y]
    return {
        "n": n,
        "accuracy": round(sum((p >= 0.5) == y for p, y in pairs) / n, 3),
        "brier": round(sum((p - y) ** 2 for p, y in pairs) / n, 3),
        "log_loss": round(-sum(math.log(max(eps, p if y else 1 - p)) for p, y in pairs) / n, 3),
        "auc": round(_auc(pairs), 3),
        "mean_p_killed": round(sum(killed) / len(killed), 3),
        "mean_p_survived": round(sum(survived) / len(survived), 3),
    }


def main() -> int:
    replay = "--replay" in sys.argv
    tuning = set(load_split()["tuning"])
    usable = []
    skipped = []
    for c in cases():
        if c.case_id not in tuning:
            continue
        try:
            prompts.mutated_hunk(c)
            usable.append(c)
        except prompts.CannotBuild:
            skipped.append(c.case_id)

    jobs = []
    for c in usable:
        for v in prompts.VARIANTS:
            jobs.append(("jev", c, v))
            jobs.append(("mini", c, v))

    def run(job):
        provider, c, v = job
        if provider == "jev":
            rec = recorder.jev(prompts.jev_body(c, v), replay_only=replay)
            return provider, v, c, recorder.jev_p_yes(rec), rec
        rec = recorder.mini(recorder.mini_request(prompts.mini_messages(c, v)), replay_only=replay)
        return provider, v, c, recorder.mini_p_yes(rec), rec

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(run, jobs))

    report: dict = {"tuning_cases": len(usable), "left_out": skipped, "scores": {}}
    for provider in ("jev", "mini"):
        for v in prompts.VARIANTS:
            rows = [r for r in results if r[0] == provider and r[1] == v]
            pairs = [(p, c.killed) for _, _, c, p, _ in rows if p is not None]
            s = score(pairs)
            s["no_answer"] = len(rows) - len(pairs)
            s["mean_ms"] = round(sum(r[4]["elapsed_ms"] for r in rows) / len(rows))
            if provider == "jev":
                s["mean_input_tokens"] = round(
                    sum(r[4]["response"]["usage"]["input_tokens"] for r in rows) / len(rows)
                )
            else:
                s["mean_input_tokens"] = round(
                    sum(r[4]["response"]["usage"]["prompt_tokens"] for r in rows) / len(rows)
                )
            report["scores"][f"{provider}:{v}"] = s

    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(f"tuning cases: {len(usable)} (left out: {len(skipped)})")
    header = "approach:variant                 n   acc  brier logloss  auc  p|kill p|surv  none   ms  tok"
    print(header)
    for name, s in report["scores"].items():
        print(
            f"{name:<30} {s['n']:>4} {s['accuracy']:.3f} {s['brier']:.3f} {s['log_loss']:6.3f} "
            f"{s['auc']:.3f} {s['mean_p_killed']:.3f}  {s['mean_p_survived']:.3f} {s['no_answer']:>4} "
            f"{s['mean_ms']:>5} {s['mean_input_tokens']:>5}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

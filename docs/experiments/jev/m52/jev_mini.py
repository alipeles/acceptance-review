"""Jev first, Mini for the cases Jev is unsure of: the cheap alternative to Jev then Opus.

Asked after the held-out set had been scored once, because Jev then Opus costs
about 45 times the shipped judge. The held-out set is therefore no longer
untouched, but every rule here is still fitted on tuning cases only, by the
procedure below, and then applied to the held-out cases unchanged.

Two fallbacks for the cases Jev is unsure of:
- ``shipped``: the shipped judge (GPT-5.4 Mini, batched), using the verdicts
  already recorded by ``run_judge_a.py`` (tuning) and ``score_heldout.py``
  (held out). This is #379's approach C, with the targeted Jev prompt.
- ``mini``: one Mini call per case on the prompt Opus was given
  (``context+description``), "fails" when Mini's p(yes) >= 0.5. If Mini gives
  no usable answer, Jev's own p >= 0.5 decides.

Rule: Jev (targeted prompt) says "fails" at p >= hi and "survives" at p <= lo;
the rest go to the fallback. (lo, hi) maximises tuning accuracy; ties go to the
rule sending fewer cases to the fallback, then the lower ``lo``.

Cost: Jev at $0.042/M input tokens; Mini at $0.75/M input and $4.50/M output
(these reproduce the ``cost_usd`` the harness records for the shipped judge's
calls); the shipped judge at its measured mean cost per case on each set.

Run from the repo root:  .venv/bin/python docs/experiments/jev/m52/jev_mini.py
Writes ``jev-mini.json``.
"""

from __future__ import annotations

import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import prompts
import recorder
import targeted_prompt as tp
from run_jev_framing import answers
from split import cases, load_split
from sweep_targets import PER_TOKEN, tokens

HERE = Path(__file__).resolve().parent
OUT = HERE / "jev-mini.json"
GRID = [round(i / 50, 2) for i in range(51)]
VARIANT = "context+description"
MINI_IN, MINI_OUT = 0.75 / 1_000_000, 4.50 / 1_000_000
# Measured from the shipped judge's recorded transcripts (usage.cost_usd):
# 61 calls for 137 tuning cases, 52 calls for 92 held-out cases.
SHIPPED_PER_CASE = {"tuning": 0.0675 / 137, "held_out": 0.0566 / 92}


def usable(side: str):
    ids = set(load_split()[side])
    out = []
    for c in cases():
        if c.case_id in ids:
            try:
                prompts.mutated_hunk(c)
                out.append(c)
            except prompts.CannotBuild:
                pass
    return out


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    p = k / n
    d = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(mid - half, 3), round(mid + half, 3)]


def rows(side: str, replay_only: bool):
    """Per case: (killed, jev_p, jev_cost, shipped_verdict, mini_verdict, mini_cost)."""
    cs = usable(side)
    if side == "tuning":
        shipped = json.loads((HERE / "tuning-judge-a.json").read_text(encoding="utf-8"))["verdicts"]
    else:
        per = json.loads((HERE / "heldout.json").read_text(encoding="utf-8"))["per_case"]
        shipped = {k: v["A"] for k, v in per.items()}

    def one(c):
        j = recorder.jev(tp.fails_body(c), replay_only=True)
        m = recorder.mini(
            recorder.mini_request(prompts.mini_messages(c, VARIANT)), replay_only=replay_only
        )
        p = answers(j)["fails"]
        mp = recorder.mini_p_yes(m)
        u = m["response"]["usage"] or {}
        return (
            c.killed,
            p,
            tokens(j) * PER_TOKEN,
            shipped.get(c.case_id),
            (p >= 0.5) if mp is None else (mp >= 0.5),
            u.get("prompt_tokens", 0) * MINI_IN + u.get("completion_tokens", 0) * MINI_OUT,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(one, cs))


def apply(rs, fallback: str, lo: float, hi: float, side: str):
    right = esc = 0
    cost = 0.0
    said = []
    for killed, p, jc, sv, mv, mc in rs:
        cost += jc
        if p >= hi:
            v = True
        elif p <= lo:
            v = False
        else:
            esc += 1
            if fallback == "shipped":
                v, cost = sv, cost + SHIPPED_PER_CASE[side]
            else:
                v, cost = mv, cost + mc
        said.append((v, killed))
        right += v is not None and v == killed
    n = len(rs)
    tp_ = sum(v is True and k for v, k in said)
    fp = sum(v is True and not k for v, k in said)
    return {
        "accuracy": round(right / n, 3),
        "accuracy_95pct_interval": wilson(right, n),
        "precision_on_fails": round(tp_ / (tp_ + fp), 3) if tp_ + fp else None,
        "false_fails": fp,
        "missed_kills": sum(v is False and k for v, k in said),
        "sent_to_fallback": round(esc / n, 3),
        "cost_per_case": round(cost / n, 5),
    }


def fit(rs, fallback: str):
    best = None
    for lo in GRID:
        for hi in GRID:
            if lo >= hi:
                continue
            s = apply(rs, fallback, lo, hi, "tuning")
            key = (s["accuracy"], -s["sent_to_fallback"], -lo)
            if best is None or key > best[0]:
                best = (key, lo, hi)
    return best[1], best[2]


def alone(rs, which: str, side: str):
    if which == "jev":
        return apply(rs, "mini", 0.4999, 0.5, side)  # every case decided by Jev at 0.5
    return apply(rs, which, -1.0, 2.0, side)  # every case sent to the fallback


def main() -> int:
    tuning = rows("tuning", replay_only=True)
    held = rows("held_out", replay_only=False)
    report: dict = {"tuning_cases": len(tuning), "held_out_cases": len(held), "designs": {}}
    for name in ("jev", "shipped", "mini"):
        report["designs"][f"{name} alone"] = {
            "tuning": alone(tuning, name, "tuning"),
            "held_out": alone(held, name, "held_out"),
        }
    for fb in ("shipped", "mini"):
        lo, hi = fit(tuning, fb)
        report["designs"][f"jev then {fb}"] = {
            "rule": {"lo": lo, "hi": hi},
            "tuning": apply(tuning, fb, lo, hi, "tuning"),
            "held_out": apply(held, fb, lo, hi, "held_out"),
        }
    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

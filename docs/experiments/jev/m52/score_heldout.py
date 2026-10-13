"""Score the designs frozen in ``frozen.json`` on the held-out set, once.

Reads the rules from ``frozen.json`` (committed before this ran) and applies
them unchanged; nothing here is fit. Refuses to run if ``heldout.json``
already exists, since the held-out set is scored once.

Live calls: Jev (two questions, two prompt shapes), no-tools Opus on every
case, and the shipped judge (A). All recorded, so a rerun after deleting
``heldout.json`` replays rather than calling again.

Run from the repo root (A's transcript store is found from the working
directory):  .venv/bin/python docs/experiments/jev/m52/score_heldout.py
Writes ``heldout.json`` (aggregates and per-case verdicts by id only).
"""

from __future__ import annotations

import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import prompts
import reach_prompt
import recorder
import targeted_prompt as tp
from classify_gap import no_tools
from freeze import outcome
from run_jev_framing import answers, body_mutant
from run_judge_a import judge_all
from split import cases, load_split
from sweep_targets import PER_TOKEN, tokens

from acceptance.config import RunConfig
from acceptance.llm import Mode

HERE = Path(__file__).resolve().parent
FROZEN = HERE / "frozen.json"
OUT = HERE / "heldout.json"
PROMPTS = {
    "targeted": (tp.fails_body, tp.reach_body),
    "hunk": (body_mutant, reach_prompt.body),
}


def ask(build, case):
    """Jev's record, or None when the request cannot be built or is refused."""
    try:
        return recorder.jev(build(case))
    except Exception:  # noqa: BLE001 — declared in freeze.py: such a case goes to Opus
        return None


def wilson(k: int, n: int, z: float = 1.96) -> list[float]:
    p = k / n
    d = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(mid - half, 3), round(mid + half, 3)]


def summary(said: list[bool | None], y: list[bool], cost=None, esc=None) -> dict:
    n = len(y)
    right = sum(s is not None and s == t for s, t in zip(said, y, strict=True))
    out = {
        "accuracy": round(right / n, 3),
        "accuracy_95pct_interval": wilson(right, n),
        "false_fails": sum(s is True and not t for s, t in zip(said, y, strict=True)),
        "missed_kills": sum(s is False and t for s, t in zip(said, y, strict=True)),
        "no_verdict": sum(s is None for s in said),
    }
    if cost is not None:
        out["cost_per_case"] = round(sum(cost) / n, 4)
    if esc is not None:
        out["escalated_share"] = round(sum(esc) / n, 3)
    return out


def main() -> int:
    if OUT.exists():
        print(f"{OUT.name} exists; the held-out set is scored once")
        return 1
    frozen = json.loads(FROZEN.read_text(encoding="utf-8"))["designs"]
    held = set(load_split()["held_out"])
    usable, unbuildable = [], []
    for c in cases():
        if c.case_id in held:
            try:
                prompts.mutated_hunk(c)
                usable.append(c)
            except prompts.CannotBuild:
                unbuildable.append(c.case_id)
    ids = [c.case_id for c in usable]
    y = [c.killed for c in usable]

    def jev_all(c):
        return {name: (ask(f, c), ask(r, c)) for name, (f, r) in PROMPTS.items()}

    with ThreadPoolExecutor(max_workers=8) as pool:
        jev_recs = list(pool.map(jev_all, usable))
        opus = list(pool.map(no_tools, usable))
    a_verdicts, _ = judge_all(usable, RunConfig(mode=Mode.RECORD).build_client())

    report: dict = {
        "held_out_cases": len(held),
        "usable": len(usable),
        "unbuildable": len(unbuildable),
        "killed": sum(y),
        "survived": len(y) - sum(y),
        "jev_requests_failed": {
            name: sum(r[name][0] is None or r[name][1] is None for r in jev_recs)
            for name in PROMPTS
        },
        "designs": {},
    }
    d = report["designs"]
    d["A"] = summary([a_verdicts.get(i) for i in ids], y)
    d["opus"] = summary([o["verdict"] for o in opus], y, cost=[o["cost_usd"] or 0.0 for o in opus])
    tf = [r["targeted"][0] for r in jev_recs]
    d["jev_targeted"] = summary(
        [None if f is None else answers(f)["fails"] >= 0.5 for f in tf],
        y,
        cost=[0.0 if f is None else tokens(f) * PER_TOKEN for f in tf],
    )
    per_case = {i: {"killed": t} for i, t in zip(ids, y, strict=True)}
    for key, spec in frozen.items():
        if not key.startswith("jev_then_opus/"):
            continue
        _, name, _ = key.split("/")
        rule = (spec["rule"]["reach_cut"], spec["rule"]["lo"], spec["rule"]["hi"])
        said, cost, esc = [], [], []
        for i, (c, o) in enumerate(zip(usable, opus, strict=True)):
            f, r = jev_recs[i][name]
            o_cost = o["cost_usd"] or 0.0
            if f is None or r is None:
                said.append(o["verdict"])
                cost.append(o_cost)
                esc.append(1)
                continue
            ok, cst, e = outcome(
                answers(f)["fails"],
                answers(r)["reaches"],
                tokens(f),
                tokens(r),
                o["verdict"] == c.killed,
                o_cost,
                c.killed,
                rule,
            )
            # Map right/wrong back to a verdict so false fails and missed kills count.
            said.append(o["verdict"] if e else (c.killed if ok else not c.killed))
            cost.append(cst)
            esc.append(e)
        d[key] = {
            "rule": spec["rule"],
            "tuning": {
                "accuracy": spec["tuning_accuracy"],
                "cost_per_case": spec["tuning_cost_per_case"],
                "escalated_share": spec["tuning_escalated_share"],
            },
            "held_out": summary(said, y, cost=cost, esc=esc),
        }
        for cid, s in zip(ids, said, strict=True):
            per_case[cid][key] = s
    for cid, a, o in zip(ids, (a_verdicts.get(i) for i in ids), opus, strict=True):
        per_case[cid]["A"] = a
        per_case[cid]["opus"] = o["verdict"]
    report["per_case"] = per_case
    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "per_case"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

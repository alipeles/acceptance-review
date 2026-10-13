"""Split the #372 mutant cases 60/40 into tuning and held-out sets.

Stratified by killed/survived, from a fixed seed, made before any prompt is
tried. Only case ids are written (``split.json``, committed); the cases
themselves stay in the gitignored label file.

Run:  .venv/bin/python docs/experiments/jev/m52/split.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from acceptance.benchmark.mutants.labels import MutantCase, load_mutant_labels

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LABELS = ROOT / ".acceptance" / "mutant-labels" / "labels.json"
SPLIT = HERE / "split.json"

SEED = 379
TUNING_SHARE = 0.6


def cases() -> list[MutantCase]:
    return load_mutant_labels(LABELS).cases


def load_split() -> dict[str, list[str]]:
    return json.loads(SPLIT.read_text(encoding="utf-8"))


def main() -> int:
    if SPLIT.exists():
        print(f"{SPLIT.name} already exists; the split is made once")
        return 1
    rng = random.Random(SEED)
    tuning: list[str] = []
    held_out: list[str] = []
    for killed in (True, False):
        ids = sorted(c.case_id for c in cases() if c.killed is killed)
        rng.shuffle(ids)
        cut = round(len(ids) * TUNING_SHARE)
        tuning += ids[:cut]
        held_out += ids[cut:]
    out = {"seed": SEED, "tuning": sorted(tuning), "held_out": sorted(held_out)}
    SPLIT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    by_id = {c.case_id: c for c in cases()}
    for name in ("tuning", "held_out"):
        k = sum(by_id[i].killed for i in out[name])
        print(f"{name}: {len(out[name])} cases, {k} killed, {len(out[name]) - k} survived")
    return 0


if __name__ == "__main__":
    sys.exit(main())

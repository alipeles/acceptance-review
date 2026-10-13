"""Approach A: the shipped defect-to-test judge, over the tuning set.

Calls `defects/pair_mapping.py` the way `judge_pairs` does — its own
`_batches` (up to 40 judgements, up to 4 tests per call) and `_ask` — so A is
the judge that actually ships, not a copy of its prompt. Skipped: the
reachability prefilter, which needs a repository checkout; every labelled
case is a pair the judge is asked about.

Pairs are batched per BugsInPy bug, since one review only ever offers the
judge defects and tests from one codebase. Each mutant is one `Defect`
(type `other`, the operator's description), each test one `DiscoveredTest`.

Recorded through the harness's own transcript store (`.acceptance/cache/`),
record-if-missing.

Run:  .venv/bin/python docs/experiments/jev/m52/run_judge_a.py [--replay]
Writes ``tuning-judge-a.json`` beside this file (aggregates and per-case
verdicts by case id only).
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import prompts
from split import cases, load_split

from acceptance.config import RunConfig
from acceptance.defects.pair_mapping import (
    DEFAULT_PAIR_BATCH_SIZE,
    DEFAULT_TESTS_PER_BATCH,
    _ask,
    _batches,
)
from acceptance.defects.reachability import Pair
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.llm import Mode
from acceptance.review_state import Defect, DefectType

HERE = Path(__file__).resolve().parent
OUT = HERE / "tuning-judge-a.json"


def _mutant_id(case_id: str) -> str:
    """'PySnooper/1/m0/tests/x.py::t' -> 'm0'."""
    return case_id.split("/")[2]


def main() -> int:
    replay = "--replay" in sys.argv
    client = RunConfig(mode=Mode.REPLAY if replay else Mode.RECORD).build_client()
    tuning = set(load_split()["tuning"])
    usable = []
    for c in cases():
        if c.case_id not in tuning:
            continue
        try:
            prompts.mutated_hunk(c)  # same 137 cases as the other approaches
        except prompts.CannotBuild:
            continue
        usable.append(c)

    by_bug = defaultdict(list)
    for c in usable:
        by_bug[(c.project, c.bug_id)].append(c)

    def judge_bug(bug_cases):
        defects = {}
        tests = {}
        pairs = []
        case_of = {}
        for c in bug_cases:
            mid = _mutant_id(c.case_id)
            defects.setdefault(
                mid,
                Defect(
                    id=mid,
                    obligation_id="O1",
                    type=DefectType.OTHER,
                    description=c.defect_description,
                ),
            )
            tests.setdefault(
                c.test_id,
                DiscoveredTest(
                    test_id=c.test_id, file=c.test_id.split("::")[0], source=c.test_source
                ),
            )
            pair = Pair(defects[mid], tests[c.test_id])
            pairs.append(pair)
            case_of[pair.key] = c.case_id
        out = {}
        calls = []
        for batch in _batches(pairs, DEFAULT_PAIR_BATCH_SIZE, DEFAULT_TESTS_PER_BATCH):
            start = time.monotonic()
            answered, _unusable, _ = _ask(list(batch.items), batch, client)
            calls.append((len(batch.items), (time.monotonic() - start) * 1000))
            for pair in batch.items:
                cid = case_of[pair.key]
                if pair.key in answered:
                    out[cid] = answered[pair.key][0]
                else:
                    out[cid] = None  # shed or unusable: no verdict
        return out, calls

    verdicts: dict[str, bool | None] = {}
    calls: list[tuple[int, float]] = []
    with ThreadPoolExecutor(max_workers=6) as pool:
        for out, c in pool.map(judge_bug, by_bug.values()):
            verdicts.update(out)
            calls += c

    label = {c.case_id: c.killed for c in usable}
    judged = {k: v for k, v in verdicts.items() if v is not None}
    tp = sum(v and label[k] for k, v in judged.items())
    fp = sum(v and not label[k] for k, v in judged.items())
    tn = sum((not v) and (not label[k]) for k, v in judged.items())
    fn = sum((not v) and label[k] for k, v in judged.items())
    n = len(judged)
    report = {
        "tuning_cases": len(usable),
        "judged": n,
        "no_verdict": len(verdicts) - n,
        "calls": len(calls),
        "accuracy": round((tp + tn) / n, 3),
        "precision_killed": round(tp / (tp + fp), 3) if tp + fp else None,
        "recall_killed": round(tp / (tp + fn), 3) if tp + fn else None,
        "precision_survived": round(tn / (tn + fn), 3) if tn + fn else None,
        "recall_survived": round(tn / (tn + fp), 3) if tn + fp else None,
        "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "mean_ms_per_case": round(sum(ms for _, ms in calls) / len(verdicts)),
        "verdicts": dict(sorted(verdicts.items())),
    }
    # A replay times the cache, not the judge; keep the live run's figure.
    if replay and OUT.exists():
        report["mean_ms_per_case"] = json.loads(OUT.read_text(encoding="utf-8"))["mean_ms_per_case"]
    OUT.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    for k, v in report.items():
        if k != "verdicts":
            print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

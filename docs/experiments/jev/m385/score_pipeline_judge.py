"""Score the pipeline's pair judge on DR-379's 92 held-out mutant cases (#385).

DR-379 measured Jev then GPT-5.4 Mini at 85.9% (77-92%) on these cases, with
Jev shown each mutant's edit. #385 wired a different thing into the pipeline,
and this measures that thing, through the pipeline's own code:

- the defect is DESCRIBED, not applied: Jev and the model see the delivered
  code with the mutated lines marked and the case's defect description, which
  is what a pair looks like inside a review (`defects/jev_context.py`);
- the fallback is the run's default model (Claude Sonnet 5.5), answering yes
  or no, not Mini's token probability;
- when the model gives no usable answer the pair is unanswered, not decided.

Each case becomes one `Defect` naming one changed region (the mutated lines),
one `DiscoveredTest`, and the case's commit message as the requirement text.
The decision is `pair_mapping._decide_all`, the function the pipeline calls.

Calls are recorded in `.acceptance/cache/transcripts` like any review's, so a
second run replays. Output holds ids and numbers only, nothing from BugsInPy.

Run (needs network to api.typesafe.ai and Anthropic, so the sandbox off):
    .venv/bin/python docs/experiments/jev/m385/score_pipeline_judge.py \
        --labels ~/code/acceptance-worktrees/_archived-caches/379-jev-experiment/mutant-labels
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from acceptance.benchmark.mutants.labels import MutantCase, load_mutant_labels
from acceptance.config import RunConfig
from acceptance.coverage.prompt import hunk_label
from acceptance.defects.jev_context import CodeIndex, build_context
from acceptance.defects.pair_mapping import JEV_STAGE, _decide_all
from acceptance.defects.reachability import Pair
from acceptance.evidence.discovery import DiscoveredTest
from acceptance.jev import JevProvider
from acceptance.llm import Mode
from acceptance.review_state import (
    ChangeSet,
    Defect,
    DefectType,
    DiffHunk,
    FileChange,
)

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
SPLIT = HERE.parent / "m52" / "split.json"
OUT = HERE / "heldout-pipeline.json"
MODEL_STAGE = "defect-to-test pair mapping"


def requirement(case: MutantCase) -> str:
    """The commit message, as the experiment showed it (`m52/prompts.py`)."""
    return case.requirement_text.split("\n---\n", 1)[0].strip()


def pair_for(case: MutantCase) -> tuple[Pair, ChangeSet]:
    edit = case.edit
    change_set = ChangeSet(
        base_revision="mutant",
        head_revision=case.fixed_commit,
        files=[
            FileChange(
                path=edit.path,
                status="modified",
                category="source",
                hunks=[
                    DiffHunk(
                        header="@@",
                        old_start=edit.start_line,
                        old_lines=edit.end_line - edit.start_line + 1,
                        new_start=edit.start_line,
                        new_lines=edit.end_line - edit.start_line + 1,
                        content=edit.original,
                    )
                ],
            )
        ],
    )
    defect = Defect(
        id=f"case/{case.case_id}",
        obligation_id="case",
        type=DefectType.OTHER,
        description=case.defect_description,
        code_refs=[hunk_label(edit.path, 0)],
    )
    test = DiscoveredTest(
        test_id=case.test_id, file=case.test_id.split("::")[0], source=case.test_source
    )
    return Pair(defect, test), change_set


def wilson(correct: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = correct / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (centre - half, centre + half)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", type=Path, required=True, help="the mutant-labels directory")
    parser.add_argument("--mode", choices=["record", "replay"], default="record")
    args = parser.parse_args()
    load_dotenv(REPO_ROOT / ".env", override=False)

    held_out = set(json.loads(SPLIT.read_text(encoding="utf-8"))["held_out"])
    cases = sorted(
        (c for c in load_mutant_labels(args.labels / "labels.json").cases if c.case_id in held_out),
        key=lambda c: c.case_id,
    )
    assert len(cases) == len(held_out), (len(cases), len(held_out))

    client = RunConfig(
        mode=Mode(args.mode), transcript_root=REPO_ROOT / ".acceptance/cache/transcripts"
    ).build_client()
    jev = JevProvider()
    indexes: dict[Path, CodeIndex] = {}

    items = []
    for case in cases:
        root = args.labels / "projects" / f"{case.project}-{case.bug_id}"
        if root not in indexes:
            indexes[root] = CodeIndex(root)
        pair, change_set = pair_for(case)
        context = build_context(pair.defect, pair.test, change_set, indexes[root])
        items.append((pair, requirement(case), context))

    decisions = _decide_all(items, client, jev)

    rows = []
    for case, decision in zip(cases, decisions):
        rows.append(
            {
                "case_id": case.case_id,
                "killed": case.killed,
                "jev_probability": decision.probability,
                "judged_by": decision.judged_by.value,
                "predicted": decision.kills,
                "correct": decision.kills is not None and decision.kills == case.killed,
            }
        )

    n = len(rows)
    answered = [r for r in rows if r["predicted"] is not None]
    correct = sum(r["correct"] for r in rows)
    by_judge = Counter(r["judged_by"] for r in answered)
    unanswered = n - len(answered)
    fails_predicted = [r for r in answered if r["predicted"]]
    cost = Counter()
    calls = Counter()
    for call in client.observed_calls:
        cost[call["stage"]] += (call.get("usage") or {}).get("cost_usd") or 0.0
        calls[call["stage"]] += 1
    low, high = wilson(correct, n)
    summary = {
        "cases": n,
        "accuracy": round(correct / n, 4),
        "accuracy_95": [round(low, 4), round(high, 4)],
        "experiment_figure": {"accuracy": 0.859, "accuracy_95": [0.77, 0.92]},
        "decided_by_jev": by_judge.get("jev", 0),
        "decided_by_model": by_judge.get("model", 0),
        "unanswered": unanswered,
        "precision_on_fails": (
            round(sum(r["correct"] for r in fails_predicted) / len(fails_predicted), 4)
            if fails_predicted
            else None
        ),
        "calls": dict(calls),
        "cost_usd": {stage: round(value, 6) for stage, value in cost.items()},
        "cost_per_case_usd": round(sum(cost.values()) / n, 6),
        "jev_stage": JEV_STAGE,
        "model_stage": MODEL_STAGE,
    }
    OUT.write_text(
        json.dumps({"summary": summary, "cases": rows}, indent=1) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Pilot the two response shapes for the (defect, test) pair question (#314).

#314's Gate 1 question is not *build a call graph?* — that is settled — but how a
batch of pairs ANSWERS. DR-312's resolved question 2 names two arms and forbids
settling it by argument, because DR-173 is the record of an armchair-plausible
mapping shape that improved its headline number by losing 91 of 153 correct
mappings.

    LISTING  each test names the defects it would catch; a defect the test does
             not name is taken to survive. The response stays small and it is the
             list shape the model handles today. Shedding is INVISIBLE: a
             judgement the model quietly skipped is indistinguishable from one it
             answered "survives", and that silently un-covers a defect.

    VERDICT  each test carries an explicit verdict for EVERY offered defect.
             Shedding becomes visible, because a missing (test, defect) entry is
             detectable. But it is the shape DR-173 measured losing 59% of
             correct mappings, and it grows the response, which never amortizes
             — the caching discount is input-only.

Both arms send the SAME request content. Only the response schema differs, so any
difference in the figures is attributable to the shape and to nothing else.

## What it scores against

#315's human-reviewed defect labels on the archetype fixtures, whose `killed_by`
lists the tests that would fail if the delivered code contained that defect. That
is ground truth, which is stronger than the control #314's acceptance names (the
current mapping stage's shared-mapping count) — that control compares against
another model stage's opinion, and this compares against a human's.

**The labelled defects are fed in directly rather than enumerated.** #315 exists
to separate "the enumerator missed the defect" from "the judge missed the kill",
and this pilot is choosing a shape for the judge. Feeding it the labelled set
holds the enumerator constant at perfect, so every difference measured here
belongs to the judge.

## Reading the figures

    recall     of the labelled kills, the share the arm predicted. THE STOP
               CONDITION: an arm whose recall falls below the other's, or below
               the control, is rejected however good its other figures look.
    precision  of the arm's predicted kills, the share that were labelled.
    kills/defect  the guard metric — DR-173's analogue of mean ids per test. An
               arm that wins by answering "no" more often shows up here as a
               collapsed mean, and that is the failure DR-173 exists to catch.
    unanswered the pairs the arm returned nothing about. Reported as a count and
               as whether the shape lets us DETECT it at all, which is the whole
               case for the verdict arm.

Run with the sandbox off only if the provider host is not reachable; the default
model host is allowed. Writes findings.json beside this file.

    .venv/bin/python docs/experiments/pair-response-shape/pilot.py
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from acceptance.config import DEFAULT_SEED, RunConfig
from acceptance.llm import Mode, StrictResponseModel
from acceptance.partition import partition
from acceptance.request_blocks import Block, BlockKind, assemble
from acceptance.supplied_ids import constrain
from acceptance.usage import summarize

ARCHETYPES = REPO / "tests" / "fixtures" / "archetypes"
OUT = Path(__file__).resolve().parent / "findings.json"

LISTING_STAGE = "pair mapping pilot (listing)"
VERDICT_STAGE = "pair mapping pilot (verdict)"

_SHARED_PROMPT = """\
You are given some concrete DEFECTS — specific ways the delivered code could be
wrong — and some TESTS from the same codebase.

THE QUESTION, applied to one (defect, test) pair at a time:

    If the delivered code contained THIS DEFECT, would THIS TEST fail?

Answer it as a matter of fact about the test's assertions, not about what the
test is named or what it seems to be about. A test fails on a defect only when
the defect changes a value the test actually asserts on. A test that exercises
the defective code but asserts nothing affected by the defect does NOT fail, and
neither does a test that stubs out the defective behaviour.

Judge every pair independently. Do not assume that a test which catches one
defect catches its neighbours, and do not assume a defect no test seems aimed at
is therefore uncaught."""

_LISTING_INSTRUCTION = """\
For each test, return `catches`: the ids of the defects that test would fail on.
Return an entry for EVERY test, using an empty list where the test would fail on
none of them."""

_VERDICT_INSTRUCTION = """\
For each test, return one entry per OFFERED DEFECT — every defect id, not only
the ones it catches — with `fails` true if the test would fail on that defect and
false if it would not. A test with five defects offered returns five entries."""


class _Listed(StrictResponseModel):
    test_id: str
    catches: list[str]


class _Listing(StrictResponseModel):
    tests: list[_Listed]


class _Judged(StrictResponseModel):
    defect_id: str
    fails: bool


class _Verdicted(StrictResponseModel):
    test_id: str
    defects: list[_Judged]


class _Verdicts(StrictResponseModel):
    tests: list[_Verdicted]


def _test_ids(head: Path) -> dict[str, str]:
    """Every test in the case's head revision, as pytest node id -> source.

    Node ids are built the way `killed_by` writes them in the labels —
    `<file>::<name>` — so predictions and labels are comparable without
    normalising either side.
    """
    found: dict[str, str] = {}
    for path in sorted(head.rglob("test_*.py")):
        source = path.read_text(encoding="utf-8")
        try:
            module = ast.parse(source)
        except SyntaxError:
            continue
        lines = source.splitlines()
        relative = path.relative_to(head).as_posix()
        for node in module.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith(
                "test"
            ):
                segment = "\n".join(lines[node.lineno - 1 : (node.end_lineno or node.lineno)])
                found[f"{relative}::{node.name}"] = segment
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                for item in node.body:
                    if isinstance(
                        item, ast.FunctionDef | ast.AsyncFunctionDef
                    ) and item.name.startswith("test"):
                        segment = "\n".join(
                            lines[item.lineno - 1 : (item.end_lineno or item.lineno)]
                        )
                        found[f"{relative}::{node.name}::{item.name}"] = segment
    return found


def _cases() -> list[dict]:
    """Every archetype carrying defect labels, with its tests and source."""
    loaded = []
    for directory in sorted(ARCHETYPES.iterdir()):
        labels = directory / "labels.json"
        head = directory / "head"
        if not labels.is_file() or not head.is_dir():
            continue
        defects = json.loads(labels.read_text(encoding="utf-8")).get("defects") or []
        tests = _test_ids(head)
        if not defects or not tests:
            continue
        source = {
            path.relative_to(head).as_posix(): path.read_text(encoding="utf-8")
            for path in sorted(head.rglob("*.py"))
            if not path.name.startswith("test_") and "__pycache__" not in path.parts
        }
        loaded.append(
            {"name": directory.name, "defects": defects, "tests": tests, "source": source}
        )
    return loaded


def _blocks(case: dict, instruction: str) -> list[Block]:
    source = "\n\n".join(f"### {path}\n{text}" for path, text in sorted(case["source"].items()))
    defects = "\n".join(
        f"- id={defect['id']}: {defect['description']}" for defect in case["defects"]
    )
    tests = "\n\n".join(f"### {node}\n{body}" for node, body in sorted(case["tests"].items()))
    return [
        Block(BlockKind.INSTRUCTIONS, f"{_SHARED_PROMPT}\n\n{instruction}"),
        Block(BlockKind.SUBJECT, f"## Delivered source\n\n{source}"),
        Block(BlockKind.SUBJECT, f"## Defects\n\n{defects}"),
        Block(BlockKind.SUBJECT, f"## Tests\n\n{tests}"),
    ]


def _unanswered(case: dict, predicted: dict[str, set[str]], arm: str, raw) -> dict:
    """How many pairs the arm said nothing about, and whether we could tell.

    In the verdict arm a shed pair is detectable: the test's entry is present and
    a defect id is missing from it. In the listing arm it is NOT — a defect the
    model skipped and a defect it decided survives look identical, which is
    exactly DR-164's silent-filter trap. The count below is therefore an
    UNDERCOUNT for the listing arm, and saying so is the point.
    """
    total = len(case["defects"]) * len(case["tests"])
    answered = 0
    if arm == "verdict":
        offered = {defect["id"] for defect in case["defects"]}
        for entry in raw.tests:
            answered += len({judged.defect_id for judged in entry.defects} & offered)
    else:
        answered = len(predicted) * len(case["defects"])
    return {
        "pairs": total,
        "unanswered": max(0, total - answered),
        "detectable": arm == "verdict",
    }


def _score(cases: list[dict], predictions: dict[str, dict[str, set[str]]]) -> dict:
    """Recall, precision and the guard metric, pooled over every case."""
    labelled_edges: set[tuple[str, str, str]] = set()
    predicted_edges: set[tuple[str, str, str]] = set()
    defects = 0
    for case in cases:
        predicted = predictions.get(case["name"]) or {}
        defects += len(case["defects"])
        for defect in case["defects"]:
            for node in defect.get("killed_by") or []:
                labelled_edges.add((case["name"], defect["id"], node))
        for node, caught in predicted.items():
            for defect_id in caught:
                predicted_edges.add((case["name"], defect_id, node))

    hit = labelled_edges & predicted_edges
    return {
        "labelled_kills": len(labelled_edges),
        "predicted_kills": len(predicted_edges),
        "matched": len(hit),
        "recall": (len(hit) / len(labelled_edges)) if labelled_edges else None,
        "precision": (len(hit) / len(predicted_edges)) if predicted_edges else None,
        "kills_per_defect": (len(predicted_edges) / defects) if defects else None,
    }


def main() -> int:
    cases = _cases()
    if not cases:
        print("no archetype cases carry defect labels", file=sys.stderr)
        return 1

    pairs = sum(len(case["defects"]) * len(case["tests"]) for case in cases)
    print(f"{len(cases)} cases, {sum(len(c['defects']) for c in cases)} defects, {pairs} pairs")

    # Repeated draws, because one draw is what DR-173 warns against and #150 is
    # the open issue on provider variance. The seed is the only thing varied —
    # same prompts, same cases, same temperature — so a spread across these is
    # draw variance and nothing else. Three is enough to see whether a
    # difference between the arms is larger than the noise around it; it is not
    # enough to put a confidence interval on either arm, and the write-up says so.
    seeds = [DEFAULT_SEED, DEFAULT_SEED + 1, DEFAULT_SEED + 2]

    findings: dict = {"cases": [case["name"] for case in cases], "seeds": seeds, "arms": {}}
    for arm, seed in [(arm, seed) for arm in ("listing", "verdict") for seed in seeds]:
        config = RunConfig(mode=Mode.RECORD, seed=seed)
        client = config.build_client()
        predictions: dict[str, dict[str, set[str]]] = {}
        shedding = []
        for case in cases:
            defect_ids = [defect["id"] for defect in case["defects"]]
            test_ids = sorted(case["tests"])
            if arm == "listing":
                model, stage, instruction = _Listing, LISTING_STAGE, _LISTING_INSTRUCTION
                allowed = {"test_id": test_ids, "catches": defect_ids}
            else:
                model, stage, instruction = _Verdicts, VERDICT_STAGE, _VERDICT_INSTRUCTION
                allowed = {"test_id": test_ids, "defect_id": defect_ids}
            batch = partition([case["name"]], 1, key=lambda name: name)[0]
            raw = client.complete(
                assemble(_blocks(case, instruction)),
                constrain(model, allowed),
                batch.request_partition(),
                parse_as=model,
                stage=stage,
            )
            predicted: dict[str, set[str]] = {}
            for entry in raw.tests:
                if arm == "listing":
                    predicted[entry.test_id] = set(entry.catches)
                else:
                    predicted[entry.test_id] = {
                        judged.defect_id for judged in entry.defects if judged.fails
                    }
            predictions[case["name"]] = predicted
            shedding.append(_unanswered(case, predicted, arm, raw))

        usage = summarize(client.observed_calls)
        findings["arms"][f"{arm}/seed={seed}"] = {
            **_score(cases, predictions),
            "unanswered_pairs": sum(entry["unanswered"] for entry in shedding),
            "shedding_detectable": arm == "verdict",
            "cost_usd": usage.run_spend_usd,
            "prompt_tokens": sum(stage.prompt_tokens for stage in usage.stages),
            "completion_tokens": sum(stage.completion_tokens for stage in usage.stages),
            "predictions": {
                name: {node: sorted(caught) for node, caught in sorted(predicted.items())}
                for name, predicted in sorted(predictions.items())
            },
        }

    OUT.write_text(json.dumps(findings, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for label, figures in findings["arms"].items():
        print(
            f"{label:22s} recall={figures['recall']:.4f} precision={figures['precision']:.4f} "
            f"kills/defect={figures['kills_per_defect']:.3f} "
            f"unanswered={figures['unanswered_pairs']} "
            f"detectable={figures['shedding_detectable']} "
            f"cost=${figures['cost_usd']:.4f} out_tokens={figures['completion_tokens']}"
        )

    # The spread across seeds is the thing to read, not any single row: an arm
    # whose recall moves more between seeds than the two arms differ from each
    # other has not been separated by this experiment.
    print()
    for arm in ("listing", "verdict"):
        rows = [figures for label, figures in findings["arms"].items() if label.startswith(arm)]
        recalls = [row["recall"] for row in rows]
        print(
            f"{arm:8s} recall min={min(recalls):.4f} max={max(recalls):.4f} "
            f"mean={sum(recalls) / len(recalls):.4f}  "
            f"out_tokens mean={sum(r['completion_tokens'] for r in rows) / len(rows):.0f}  "
            f"cost mean=${sum(r['cost_usd'] for r in rows) / len(rows):.4f}"
        )
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

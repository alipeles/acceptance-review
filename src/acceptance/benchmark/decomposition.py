"""Decomposition scoring hook (M1.4).

Wires M1.2/M1.3's obligation decomposition into the M-B0.3
decomposition-accuracy metric. Decomposing a case only needs its task text —
not a materialized repo, diff, or test run — so this hook is deliberately
lighter than the full checker pipeline (M-B0.2's run_case): no git
materialization, just parse -> decompose -> a minimal Review carrying the
resulting obligation_map, ready for score_case/score_case_set.
"""

from __future__ import annotations

from acceptance.benchmark.case import BenchmarkCase
from acceptance.benchmark.scoring import score_case
from acceptance.llm import ModelClient
from acceptance.requirement.obligations import decompose
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import Review, ReviewProvenance


def decompose_case(case: BenchmarkCase, client: ModelClient) -> BenchmarkCase:
    """Decompose a case's task text and return a scored copy of `case`."""
    parsed = parse_task_file(case.inputs.task_text)
    result = decompose(parsed, client)

    review = Review(
        mode="local",
        reviewed_revision=case.inputs.head_revision,
        provenance=ReviewProvenance(
            determinism_mode=client.mode.value,
            model=client.model,
            temperature=client.temperature,
            seed=client.seed,
        ),
        obligation_map=result.obligations,
    )
    scored_case = case.model_copy(update={"reviewer_output": review})
    return scored_case.model_copy(update={"score": score_case(scored_case)})

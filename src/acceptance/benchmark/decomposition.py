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
from acceptance.benchmark.hooks import scored_copy
from acceptance.config import provenance_for
from acceptance.llm import ModelClient
from acceptance.requirement.obligations import decompose
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import Review


def decompose_case(case: BenchmarkCase, client: ModelClient) -> BenchmarkCase:
    """Decompose a case's task text and return a scored copy of `case`."""
    parsed = parse_task_file(case.inputs.task_text)
    result = decompose(parsed, client)

    review = Review(
        mode="local",
        reviewed_revision=case.inputs.head_revision,
        # Stamped after `decompose` has run, so the honoured controls it reports
        # reflect calls that actually happened (#160).
        provenance=provenance_for(client),
        obligation_map=result.obligations,
    )
    return scored_copy(case, review)

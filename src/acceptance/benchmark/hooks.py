"""Shared plumbing for benchmark scoring hooks.

Every hook that wires a capability's output into `score_case` (M1.4's
`decompose_case`, M3.3's `classify_case`, and the M4/M5 hooks still to come)
follows the same shape: stamp a `ReviewProvenance` from the `ModelClient` that
produced the output, build a `Review`, then copy it onto the case and attach
its score. Factored out once decomposition.py and coverage.py built the same
two steps identically.
"""

from __future__ import annotations

from acceptance.benchmark.case import BenchmarkCase
from acceptance.benchmark.scoring import score_case
from acceptance.llm import ModelClient
from acceptance.review_state import Review, ReviewProvenance


def provenance_from(client: ModelClient) -> ReviewProvenance:
    return ReviewProvenance(
        determinism_mode=client.mode.value,
        model=client.model,
        temperature=client.temperature,
        seed=client.seed,
    )


def scored_copy(case: BenchmarkCase, review: Review) -> BenchmarkCase:
    """Attach `review` to a copy of `case` and score it; `case` is untouched."""
    scored_case = case.model_copy(update={"reviewer_output": review})
    return scored_case.model_copy(update={"score": score_case(scored_case)})

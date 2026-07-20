"""Checker-under-test runner (M-B0.2).

Feeds a BenchmarkCase's inputs through the current checker (M0.6's
`run_check` pipeline) and returns a new case with `reviewer_output` and
`score` filled in. Cases are treated as data, not mutated in place: the
input case is untouched, and a copy carries the result.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from acceptance.benchmark.case import BenchmarkCase
from acceptance.benchmark.scoring import score_case
from acceptance.cli import run_check
from acceptance.config import RunConfig
from acceptance.review_store import ReviewStore


def run_case(
    case: BenchmarkCase,
    config: RunConfig | None = None,
    review_store: ReviewStore | None = None,
) -> BenchmarkCase:
    """Run the checker over `case.inputs` and return a scored copy of `case`."""
    config = config if config is not None else RunConfig()
    review_store = review_store if review_store is not None else ReviewStore()
    repo = Path(case.inputs.repo)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as task_file:
        task_file.write(case.inputs.task_text)
        task_path = Path(task_file.name)

    try:
        review = run_check(
            task=str(task_path),
            base=case.inputs.base_revision,
            head=case.inputs.head_revision,
            config=config,
            store=review_store,
            repo=repo,
        )
    finally:
        task_path.unlink(missing_ok=True)

    scored_case = case.model_copy(update={"reviewer_output": review})
    scored_case = scored_case.model_copy(update={"score": score_case(scored_case)})
    return scored_case

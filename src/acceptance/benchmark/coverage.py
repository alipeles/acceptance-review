"""Coverage & evidence scoring hook (M3.3, extended M5.5; pipeline shared M7.4).

Wires the checker's static-analysis capabilities into the M-B0.3 §11.1
metrics. Since M7.4 the analysis itself lives in `pipeline.py::run_review`,
shared with the CLI — this module is now just the benchmark's adapter around
it: materialize the case's diff, run the review, attach it to a scored copy.
Keeping one pipeline is deliberate: the CLI and the benchmark previously
drifted (every capability from M4 on reached only the benchmark), which meant
dogfooding exercised less than the benchmark measured.

`scoring.py`'s gap metric (`_gap_counts`) matches a ground-truth gap to a
reported `Finding` by the description of the obligation the gap concerns
(`Finding.related_obligation`). A non-addressed `ImplementationCoverage` is
exactly that: it names the obligation the checker believes is incompletely
covered, so it becomes a Finding linked to that obligation. An
`UnrequestedChange` has no obligation to link — §9.2 unrequested changes are
about code that shouldn't have changed, not about an obligation going
unmet — so it becomes an unlinked Finding: reported for a human to read, but
not yet counted by a metric that only scores obligation-linked gaps.
"""

from __future__ import annotations

from pathlib import Path

from acceptance.benchmark.case import BenchmarkCase
from acceptance.benchmark.hooks import scored_copy
from acceptance.change.diff import extract_change_set
from acceptance.config import ScopeExpansionPolicy
from acceptance.llm import ModelClient
from acceptance.pipeline import run_review


def classify_case(
    case: BenchmarkCase,
    client: ModelClient,
    policy: ScopeExpansionPolicy = ScopeExpansionPolicy.STRICT,
) -> BenchmarkCase:
    """Run the shared review pipeline over a case's diff and return a scored
    copy of `case`. The benchmark's adapter around `run_review` — every
    capability the CLI runs is scored here, by construction."""
    repo = Path(case.inputs.repo)
    change_set = extract_change_set(
        repo, case.inputs.base_revision, case.inputs.head_revision
    )
    review = run_review(
        task_text=case.inputs.task_text,
        change_set=change_set,
        repo=repo,
        client=client,
        reviewed_revision=case.inputs.head_revision,
        declaration_text=case.inputs.declaration_text,
        policy=policy,
    )
    return scored_copy(case, review)

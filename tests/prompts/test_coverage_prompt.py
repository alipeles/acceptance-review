"""Prompt-quality tests for coverage classification (#310), over REAL responses.

`tests/coverage/test_classify.py` injects hand-authored answers, so it checks
that the request marks a scope exclusion and cannot check what the model does
with the mark. This replays a committed corpus instead. Re-record with:

    ACCEPTANCE_RECORD=1 pytest tests/prompts/test_coverage_prompt.py -q

Recorded against an archetype fixture only: a transcript embeds the full
request, so recording a dogfood run would commit this repo's own diffs into
fixtures.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from acceptance.benchmark.fixtures import materialize_archetype
from acceptance.change.diff import extract_change_set
from acceptance.coverage.classify import CoverageStatus, classify_coverage
from acceptance.review_state import Obligation, ObligationType, RequiredEvidence
from acceptance.source_ref import TextSpan
from tests.support import recorded_client

ARCHETYPES = Path(__file__).resolve().parents[1] / "fixtures" / "archetypes"

# Three scope exclusions over a diff that touches none of them. Two are worded
# in the absence form the decomposer is asked for. The third is worded as work
# to do — the shape #302's Gate 2 produced, "The change excludes model calls
# issued by the measurement harness from the review run scope", which the
# coverage stage then reported not addressed beside siblings carrying the same
# evidence. Its bullet ends with an explanatory clause, as that one did.
_EXCLUSIONS = [
    (
        "no-sales-tax",
        "Sales tax on the receipt line.",
        "The change does not add sales tax to the receipt line.",
    ),
    (
        "no-other-currencies",
        "Currency symbols other than the dollar.",
        "The change does not add currency symbols other than the dollar.",
    ),
    (
        "refund-receipts",
        "Receipts for refunds, which the returns service prints.",
        (
            "The change excludes refund receipts from `format_line`, so that a refund "
            "is handed to the returns service instead of being formatted."
        ),
    ),
]


def _boundary(obligation_id: str, bullet: str, description: str) -> Obligation:
    return Obligation(
        id=obligation_id,
        description=description,
        type=ObligationType.INVARIANT,
        importance="normal",
        explicit=True,
        observable_behavior=f"work on {bullet.rstrip('.').lower()} appearing in the diff",
        source_spans=[TextSpan(text=bullet, start=0, end=len(bullet))],
        required_evidence=RequiredEvidence.CODE_ONLY,
        required_evidence_reason="A scope exclusion is owed code evidence only.",
        satisfied_by_absence=True,
    )


@pytest.fixture(scope="module")
def classified(tmp_path_factory):
    fixture = materialize_archetype(
        ARCHETYPES / "01-missed-obligation", tmp_path_factory.mktemp("repo")
    )
    change_set = extract_change_set(fixture.repo_path, fixture.base_sha, fixture.head_sha)
    obligations = [_boundary(*exclusion) for exclusion in _EXCLUSIONS]
    coverages = classify_coverage(obligations, change_set, recorded_client())
    return {coverage.obligation_id: coverage for coverage in coverages}


def test_scope_exclusions_with_the_same_evidence_get_the_same_status(classified):
    """#310's Acceptance: identical code evidence yields the identical status
    across every scope-exclusion obligation in one run. The diff touches none of
    the three, so the evidence for each is the same — nothing breaches it."""
    statuses = {oid: coverage.status for oid, coverage in classified.items()}

    assert len(set(statuses.values())) == 1, f"same evidence, different statuses: {statuses}"


def test_a_misworded_scope_exclusion_is_judged_as_a_boundary(classified):
    """The sharper half. Equal statuses could be equally wrong; the one the
    review must reach is `addressed`, since no hunk does any excluded work."""
    coverage = classified["refund-receipts"]

    assert coverage.status is CoverageStatus.ADDRESSED, coverage.rationale

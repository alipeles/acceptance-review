"""Coverage scoring hook (M3.3).

Wires M3.1's implementation-coverage classification and M3.2's
unrequested-change detection into the M-B0.3 gap-detection/false-alarm
metric. Like M1.4's decompose_case (decomposition.py), this stays lighter
than the full checker pipeline (M-B0.2's run_case) — it only needs a case's
task text and its materialized repo's diff, no test execution.

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
from acceptance.benchmark.hooks import provenance_from, scored_copy
from acceptance.change.diff import extract_change_set
from acceptance.coverage.classify import CoverageStatus, ImplementationCoverage, classify_coverage
from acceptance.coverage.unrequested import UnrequestedChange, detect_unrequested_changes
from acceptance.evidence_tier import Component, EvidenceTier
from acceptance.llm import ModelClient
from acceptance.requirement.obligations import decompose
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import Finding, Link, Obligation, Review

_SEVERITY_BY_STATUS = {
    CoverageStatus.NOT_ADDRESSED: "high",
    CoverageStatus.PARTIALLY_ADDRESSED: "medium",
    CoverageStatus.UNCLEAR: "low",
    CoverageStatus.REQUIRES_NON_CODE_EVIDENCE: "low",
}


def _coverage_finding(obligation: Obligation, coverage: ImplementationCoverage) -> Finding:
    if coverage.diff_refs:
        links = [
            Link(kind="code", ref=f"{ref.file}#{ref.hunk_header}", text=coverage.rationale)
            for ref in coverage.diff_refs
        ]
    else:
        links = [Link(kind="requirement", ref=obligation.id, text=obligation.description)]
    return Finding(
        type="coverage_gap",
        severity=_SEVERITY_BY_STATUS[coverage.status],
        description=coverage.rationale,
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=links,
        related_obligation=obligation.description,
    )


def _unrequested_finding(change: UnrequestedChange) -> Finding | None:
    # No diff location to point to means nothing a human can act on; the
    # required-link invariant (Finding._require_at_least_one_link) would
    # reject it anyway, so skip rather than fabricate a link.
    if not change.diff_refs:
        return None
    return Finding(
        type="unrequested_change",
        severity="low" if change.kind.value == "internal" else "medium",
        description=change.rationale,
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[
            Link(kind="code", ref=f"{ref.file}#{ref.hunk_header}", text=change.rationale)
            for ref in change.diff_refs
        ],
    )


def classify_case(case: BenchmarkCase, client: ModelClient) -> BenchmarkCase:
    """Decompose, classify coverage, and detect unrequested changes for a
    case's diff; return a scored copy of `case`."""
    parsed = parse_task_file(case.inputs.task_text)
    obligations = decompose(parsed, client).obligations
    change_set = extract_change_set(
        Path(case.inputs.repo), case.inputs.base_revision, case.inputs.head_revision
    )

    coverages = classify_coverage(obligations, change_set, client)
    unrequested = detect_unrequested_changes(obligations, change_set, client)

    obligations_by_id = {obligation.id: obligation for obligation in obligations}
    findings = [
        _coverage_finding(obligations_by_id[coverage.obligation_id], coverage)
        for coverage in coverages
        if coverage.status != CoverageStatus.ADDRESSED
    ]
    findings.extend(
        finding
        for finding in (_unrequested_finding(change) for change in unrequested)
        if finding is not None
    )

    review = Review(
        mode="local",
        reviewed_revision=case.inputs.head_revision,
        provenance=provenance_from(client),
        obligation_map=obligations,
        change_set=change_set,
        findings=findings,
    )
    return scored_copy(case, review)

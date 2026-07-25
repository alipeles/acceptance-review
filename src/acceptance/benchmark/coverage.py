"""Coverage & evidence scoring hook (M3.3, extended M5.5).

Wires the checker's static-analysis capabilities into the M-B0.3 §11.1
metrics. Like M1.4's decompose_case (decomposition.py), this stays lighter
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

M5.5 adds the test-evidence chain (discover -> map -> extract -> discriminate
-> classify strength) ahead of coverage classification, so `Obligation.
evidence_class` is set from real analysis of the case's own tests before
`scoring.py`'s evidence-classification-agreement metric reads it.
"""

from __future__ import annotations

from pathlib import Path

from acceptance.benchmark.case import BenchmarkCase
from acceptance.benchmark.hooks import provenance_from, scored_copy
from acceptance.change.diff import extract_change_set
from acceptance.config import ScopeExpansionPolicy
from acceptance.coverage.classify import CoverageStatus, ImplementationCoverage, classify_coverage
from acceptance.coverage.disposition import DispositionedChange, classify_dispositions
from acceptance.coverage.open_questions import apply_open_question_resolutions, resolve_open_questions
from acceptance.coverage.unrequested import detect_unrequested_changes
from acceptance.evidence.discovery import discover_tests
from acceptance.evidence.discrimination import judge_discrimination
from acceptance.evidence.extraction import extract_test_evidence
from acceptance.evidence.mapping import apply_test_mapping, map_tests_to_obligations
from acceptance.evidence.strength import apply_evidence_strength, classify_strength
from acceptance.evidence_tier import Component, EvidenceTier
from acceptance.llm import ModelClient
from acceptance.requirement.obligations import decompose
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import (
    UNREQUESTED_CHANGE,
    Finding,
    Link,
    Obligation,
    Review,
    UnrequestedChangeDisposition,
)

_SEVERITY_BY_STATUS = {
    CoverageStatus.NOT_ADDRESSED: "high",
    CoverageStatus.PARTIALLY_ADDRESSED: "medium",
    CoverageStatus.UNCLEAR: "low",
    CoverageStatus.REQUIRES_NON_CODE_EVIDENCE: "low",
}

# An in_service change is accepted; separable should be split; risky demands
# scrutiny — so severity tracks disposition, not the change's raw kind.
_SEVERITY_BY_DISPOSITION = {
    UnrequestedChangeDisposition.IN_SERVICE: "low",
    UnrequestedChangeDisposition.SEPARABLE: "medium",
    UnrequestedChangeDisposition.RISKY: "high",
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


def _unrequested_finding(dispositioned: DispositionedChange) -> Finding | None:
    change = dispositioned.change
    # No diff location to point to means nothing a human can act on; the
    # required-link invariant (Finding._require_at_least_one_link) would
    # reject it anyway, so skip rather than fabricate a link.
    if not change.diff_refs:
        return None
    return Finding(
        type=UNREQUESTED_CHANGE,
        severity=_SEVERITY_BY_DISPOSITION[dispositioned.disposition],
        description=change.rationale,
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[
            Link(kind="code", ref=f"{ref.file}#{ref.hunk_header}", text=change.rationale)
            for ref in change.diff_refs
        ],
        disposition=dispositioned.disposition,
        recommended_action=dispositioned.recommendation,
    )


def classify_case(
    case: BenchmarkCase,
    client: ModelClient,
    policy: ScopeExpansionPolicy = ScopeExpansionPolicy.STRICT,
) -> BenchmarkCase:
    """Decompose; discover and map candidate tests; extract, discriminate, and
    classify their evidence strength; classify coverage, detect unrequested
    changes and their dispositions for a case's diff; return a scored copy of
    `case`. The benchmark's assembled static pipeline — each capability lands
    here as it ships so its §11.1 metric is scored (M3-M5)."""
    parsed = parse_task_file(case.inputs.task_text)
    decomposition = decompose(parsed, client)
    obligations = decomposition.obligations
    repo = Path(case.inputs.repo)
    change_set = extract_change_set(
        repo, case.inputs.base_revision, case.inputs.head_revision
    )

    discovered = discover_tests(repo, change_set)
    mapping = map_tests_to_obligations(obligations, discovered.tests, client)
    obligations = apply_test_mapping(obligations, mapping)

    test_evidence = extract_test_evidence(repo, discovered.tests, change_set, mapping)
    discriminations = judge_discrimination(obligations, test_evidence, change_set, client)
    strengths = classify_strength(obligations, test_evidence, discriminations)
    obligations = apply_evidence_strength(obligations, strengths)

    coverages = classify_coverage(obligations, change_set, client)
    unrequested = detect_unrequested_changes(obligations, change_set, client)
    dispositioned = classify_dispositions(
        unrequested, obligations, coverages, change_set, policy, client
    )
    resolutions = resolve_open_questions(decomposition.open_questions, change_set, client)
    open_questions = apply_open_question_resolutions(decomposition.open_questions, resolutions)

    obligations_by_id = {obligation.id: obligation for obligation in obligations}
    findings = [
        _coverage_finding(obligations_by_id[coverage.obligation_id], coverage)
        for coverage in coverages
        if coverage.status != CoverageStatus.ADDRESSED
    ]
    findings.extend(
        finding
        for finding in (_unrequested_finding(change) for change in dispositioned)
        if finding is not None
    )

    review = Review(
        mode="local",
        reviewed_revision=case.inputs.head_revision,
        provenance=provenance_from(client),
        obligation_map=obligations,
        open_questions=open_questions,
        change_set=change_set,
        findings=findings,
    )
    return scored_copy(case, review)

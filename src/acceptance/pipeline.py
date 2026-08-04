"""The assembled static review pipeline (M7.4).

ONE pipeline, called by both consumers — the CLI (`acceptance check`) and the
benchmark (`benchmark/coverage.py::classify_case`). Before this existed the two
had drifted badly: every capability from M4 onward (test discovery/mapping,
evidence extraction, discrimination, strength, declaration comparison,
recommendations, verdict) was wired only into the benchmark path, so the CLI —
the very command used to dogfood the tool against its own changes — still ran
the M3-era chain and could not show test evidence or a verdict at all. Sharing
one function makes that divergence impossible by construction rather than by
keeping two copies in step.

Order follows §10.1: decompose → discover/map tests → extract, discriminate,
and classify test evidence → implementation coverage → unrequested changes and
their dispositions → resolve open questions → recommendations → declaration
comparison → completion verdict.
"""

from __future__ import annotations

from pathlib import Path

from acceptance.config import (
    DEFAULT_MAPPING_BATCH_SIZE,
    ScopeExpansionPolicy,
    provenance_for,
)
from acceptance.rerun import (
    carried_findings,
    carried_recommendations,
    compute_delta,
    merge_carried_forward,
    obligations_to_rederive,
    task_source_for,
)
from acceptance.coverage.classify import CoverageStatus, ImplementationCoverage, classify_coverage
from acceptance.coverage.declaration_comparison import (
    compare_declaration,
    declaration_mismatch_finding,
)
from acceptance.coverage.disposition import DispositionedChange, classify_dispositions
from acceptance.coverage.open_questions import apply_open_question_resolutions, resolve_open_questions
from acceptance.coverage.recommendations import recommend_tests
from acceptance.coverage.unrequested import detect_unrequested_changes
from acceptance.evidence.discovery import discover_tests
from acceptance.evidence.discrimination import judge_discrimination
from acceptance.evidence.extraction import extract_test_evidence
from acceptance.evidence.mapping import apply_test_mapping, map_tests_to_obligations
from acceptance.evidence.strength import apply_evidence_strength, classify_strength
from acceptance.supplied_ids import UnusableAnswer, UnusableAnswerLog
from acceptance.evidence_tier import Component, EvidenceTier
from acceptance.llm import ModelClient
from acceptance.requirement.declaration import declaration_absent_finding, parse_declaration
from acceptance.requirement.obligations import decompose
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import (
    UNREQUESTED_CHANGE,
    UNUSABLE_ANSWER,
    ChangeSet,
    Finding,
    Link,
    Obligation,
    Review,
    UnrequestedChangeDisposition,
)
from acceptance.verdict import derive_verdict

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


def coverage_finding(obligation: Obligation, coverage: ImplementationCoverage) -> Finding:
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


def _apply_indeterminate(
    obligations: list[Obligation], unusable: UnusableAnswerLog
) -> list[Obligation]:
    """Mark obligations whose judgment was never obtained as `indeterminate`.

    Only the evidence axis: `indeterminate` says "we did not obtain this
    judgment", which is exactly what an unusable answer means. `verdict.py`
    already routes it to `unable_to_determine` and lists it as an escalation
    candidate, so a review that could not read part of its own reviewer cannot
    come back clean.
    """
    if not unusable.indeterminate_obligations:
        return obligations
    return [
        obligation.model_copy(update={"evidence_class": "indeterminate"})
        if obligation.id in unusable.indeterminate_obligations
        else obligation
        for obligation in obligations
    ]


def unusable_answer_finding(answer: UnusableAnswer) -> Finding:
    """Name the stage and the id, so a reader can tell which judgment is missing.

    Deliberately not advisory. An unrequested change or a declaration overclaim
    is about the delivered work and leaves the verdict alone; this is about the
    review itself failing to answer a question it asked, which is precisely the
    thing a reader must not mistake for a clean result.
    """
    return Finding(
        type=UNUSABLE_ANSWER,
        severity="major",
        description=(
            f"The {answer.stage} stage returned {answer.returned_id!r} for "
            f"{answer.field!r}, which was never supplied to that call. The "
            "judgment it was meant to carry was not obtained."
        ),
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="requirement", ref=answer.returned_id, text=answer.stage)],
    )


def unrequested_finding(dispositioned: DispositionedChange) -> Finding | None:
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


def _apply_coverage_status(
    obligations: list[Obligation], coverages: list[ImplementationCoverage]
) -> list[Obligation]:
    """Record each obligation's §9.2 coverage status AND the code regions that
    satisfy it, so the report can render the implementation-coverage axis
    faithfully instead of inferring it from which findings happen to exist —
    findings are lossy here (an `addressed` obligation produces none, and so
    does an unanalyzed one, yet they mean opposite things). Carrying the refs
    is what lets the review say *where* an obligation was satisfied, not just
    that it was."""
    coverage_by_id = {c.obligation_id: c for c in coverages}
    updated = []
    for obligation in obligations:
        coverage = coverage_by_id.get(obligation.id)
        updated.append(
            obligation.model_copy(
                update={
                    "coverage_status": coverage.status.value if coverage else None,
                    "coverage_refs": (
                        [f"{ref.file}#{ref.hunk_header}" for ref in coverage.diff_refs]
                        if coverage
                        else []
                    ),
                }
            )
        )
    return updated


def run_review(
    task_text: str,
    change_set: ChangeSet,
    repo: Path,
    client: ModelClient,
    reviewed_revision: str,
    declaration_text: str | None = None,
    policy: ScopeExpansionPolicy = ScopeExpansionPolicy.STRICT,
    mapping_batch_size: int = DEFAULT_MAPPING_BATCH_SIZE,
    task_identifier: str = "<inline>",
    prior: Review | None = None,
) -> Review:
    """Run the full static review pipeline and return the assembled Review.

    With `prior`, this is an incremental re-run (M7.5): obligations the new work
    could not have affected keep their prior judgments and the per-obligation
    model stages are asked only about the rest. Decomposition is deliberately
    NOT skipped — the same task text hashes to the same request, so it replays
    from its transcript at no cost, and re-running it keeps the obligation set
    derived from one place rather than two.
    """
    parsed = parse_task_file(task_text)
    decomposition = decompose(parsed, client)
    obligations = decomposition.obligations

    # Whole-diff stages below always run: unrequested-change detection and
    # open-question resolution are about the change as a whole, not about any one
    # obligation, so there is no unaffected subset to carry forward.
    fresh_obligations = obligations
    if prior is not None:
        obligations = obligations_to_rederive(fresh_obligations, prior, change_set)

    # One log for the whole run: every stage that asks the model to echo back an
    # id we supplied reports the ids it could not honour here (#163).
    unusable = UnusableAnswerLog()

    discovered = discover_tests(repo, change_set)
    mapping = map_tests_to_obligations(
        obligations, discovered.tests, client, mapping_batch_size, unusable
    )
    obligations = apply_test_mapping(obligations, mapping)

    test_evidence = extract_test_evidence(repo, discovered.tests, change_set, mapping)
    discriminations = judge_discrimination(
        obligations, test_evidence, change_set, client, unusable
    )
    strengths = classify_strength(obligations, test_evidence, discriminations)
    obligations = apply_evidence_strength(obligations, strengths)
    # After strength, deliberately: an obligation whose judgment was never
    # obtained must not carry the strength the classifier inferred from its
    # absence. A re-run cannot improve a judgment it did not re-examine, and
    # neither can a first run claim one it never made.
    obligations = _apply_indeterminate(obligations, unusable)

    coverages = classify_coverage(obligations, change_set, client, unusable)
    obligations = _apply_coverage_status(obligations, coverages)
    unrequested = detect_unrequested_changes(obligations, change_set, client, unusable)
    dispositioned = classify_dispositions(
        unrequested, obligations, coverages, change_set, policy, client
    )
    resolutions = resolve_open_questions(
        decomposition.open_questions, change_set, client, unusable
    )
    open_questions = apply_open_question_resolutions(decomposition.open_questions, resolutions)
    recommendations = recommend_tests(
        obligations, discriminations, change_set, client, unusable
    )

    obligations_by_id = {obligation.id: obligation for obligation in obligations}
    findings = [
        coverage_finding(obligations_by_id[coverage.obligation_id], coverage)
        for coverage in coverages
        if coverage.status != CoverageStatus.ADDRESSED
    ]

    delta = None
    if prior is not None:
        judged = obligations
        obligations = merge_carried_forward(fresh_obligations, judged, prior)
        carried = [
            obligation for obligation in obligations if obligation.carried_forward_from
        ]
        # A re-run must not lose the gap it reported last time for code nobody
        # touched: the verdict reads gaps off findings, so an unaddressed
        # obligation that was not re-examined would otherwise look resolved.
        findings.extend(carried_findings(prior, carried))
        recommendations = recommendations + carried_recommendations(prior, carried)
    findings.extend(
        finding
        for finding in (unrequested_finding(change) for change in dispositioned)
        if finding is not None
    )
    findings.extend(unusable_answer_finding(answer) for answer in unusable.answers)

    if declaration_text is not None:
        declaration = parse_declaration(declaration_text)
        mismatches = compare_declaration(
            declaration, obligations, change_set, test_evidence, client
        )
        findings.extend(declaration_mismatch_finding(m) for m in mismatches)
    else:
        declaration = None
        findings.append(declaration_absent_finding())

    completion = derive_verdict(obligations, findings, open_questions)
    if prior is not None:
        delta = compute_delta(prior, obligations, completion.verdict.value)

    return Review(
        mode="local",
        reviewed_revision=reviewed_revision,
        task_source=task_source_for(task_text, task_identifier),
        delta=delta,
        # Stamped here, at the end, rather than accepted from the caller: only
        # after the calls have run does the client know which determinism
        # controls the provider honoured (#160).
        provenance=provenance_for(client),
        obligation_map=obligations,
        open_questions=open_questions,
        change_set=change_set,
        declaration=declaration,
        findings=findings,
        recommendations=recommendations,
        completion=completion,
    )

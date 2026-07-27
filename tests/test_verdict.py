"""M7.2 acceptance: the completion verdict is derived deterministically from
the findings, one of no-material-gaps / incomplete / needs-clarification /
needs-non-code-review / unable-to-determine; a positive verdict renders the
§3.7 "no material gaps at the achievable tier" caveat; an unresolved open
question blocks a positive verdict (#113).

derive_verdict is a pure function, so these assert its output directly — no
model call is involved in the headline result at all."""

from acceptance.review_state import (
    CompletionVerdict,
    Finding,
    Link,
    Obligation,
    ObligationType,
    OpenQuestion,
)
from acceptance.evidence_tier import Component, EvidenceTier
from acceptance.verdict import derive_verdict


def _obligation(obligation_id: str, evidence_class: str | None, importance: str = "critical") -> Obligation:
    return Obligation(
        id=obligation_id, description=f"{obligation_id} behavior", type=ObligationType.FUNCTIONAL,
        importance=importance, explicit=True, observable_behavior="...", evidence_class=evidence_class,
    )


def _coverage_gap(obligation_description: str) -> Finding:
    return Finding(
        type="coverage_gap", severity="high", description="missing",
        evidence_tier=EvidenceTier.STATIC, produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="requirement", ref="x", text="x")],
        related_obligation=obligation_description,
    )


def _advisory_finding(finding_type: str) -> Finding:
    return Finding(
        type=finding_type, severity="low", description="advisory",
        evidence_tier=EvidenceTier.BUILDER_CLAIM, produced_by=Component.BUILDER_DECLARATION,
        links=[Link(kind="declaration", ref="declaration", text="claim")],
    )


def _open_question(question_id: str, resolved: bool) -> OpenQuestion:
    return OpenQuestion(id=question_id, question="?", resolved=resolved)


def test_all_strong_is_no_material_gaps_with_the_caveat():
    result = derive_verdict([_obligation("a", "strongly_supported")], [], [])

    assert result.verdict is CompletionVerdict.NO_MATERIAL_GAPS
    assert any("achievable evidence tier" in lim for lim in result.limitations)  # §3.7 caveat
    assert any("not proof of correctness" in lim for lim in result.limitations)


def test_coverage_gap_is_incomplete():
    obligations = [_obligation("a", "strongly_supported")]
    findings = [_coverage_gap("a behavior")]

    result = derive_verdict(obligations, findings, [])

    assert result.verdict is CompletionVerdict.INCOMPLETE
    assert "a" in result.rationale


def test_weak_evidence_is_incomplete():
    # Decision A: present-but-non-discriminating evidence blocks the positive.
    for weak in ("partially_supported", "nominally_supported", "unsupported"):
        result = derive_verdict([_obligation("a", weak)], [], [])
        assert result.verdict is CompletionVerdict.INCOMPLETE, weak


def test_unresolved_open_question_blocks_positive_and_needs_clarification():
    # #113: even with every obligation strong, an unresolved open question
    # cannot render no-material-gaps.
    obligations = [_obligation("a", "strongly_supported")]
    result = derive_verdict(obligations, [], [_open_question("q", resolved=False)])

    assert result.verdict is CompletionVerdict.NEEDS_CLARIFICATION


def test_resolved_open_question_does_not_block():
    obligations = [_obligation("a", "strongly_supported")]
    result = derive_verdict(obligations, [], [_open_question("q", resolved=True)])

    assert result.verdict is CompletionVerdict.NO_MATERIAL_GAPS


def test_requires_non_code_evidence_is_needs_non_code_review():
    result = derive_verdict([_obligation("a", "requires_other_evidence")], [], [])
    assert result.verdict is CompletionVerdict.NEEDS_NON_CODE_REVIEW


def test_indeterminate_is_unable_to_determine_and_an_escalation_candidate():
    result = derive_verdict([_obligation("a", "indeterminate")], [], [])

    assert result.verdict is CompletionVerdict.UNABLE_TO_DETERMINE
    assert result.escalation_candidates == ["a"]  # the seam a try-harder loop consumes


def test_unclassified_evidence_is_treated_as_indeterminate():
    result = derive_verdict([_obligation("a", None)], [], [])
    assert result.verdict is CompletionVerdict.UNABLE_TO_DETERMINE


def test_no_obligations_is_unable_to_determine():
    result = derive_verdict([], [], [])
    assert result.verdict is CompletionVerdict.UNABLE_TO_DETERMINE


def test_advisory_findings_do_not_block_a_positive_verdict():
    # A declaration mismatch / unrequested change is advisory (DR-081, #31):
    # the delivered obligation is strong, so the verdict stays positive.
    obligations = [_obligation("a", "strongly_supported")]
    findings = [_advisory_finding("declaration_mismatch"), _advisory_finding("unrequested_change")]

    result = derive_verdict(obligations, findings, [])

    assert result.verdict is CompletionVerdict.NO_MATERIAL_GAPS


def test_definite_gap_outranks_indeterminate():
    # A concrete coverage gap is more actionable than uncertainty -> incomplete,
    # and the indeterminate obligation is still surfaced for escalation.
    obligations = [_obligation("a", "strongly_supported"), _obligation("b", "indeterminate")]
    findings = [_coverage_gap("a behavior")]

    result = derive_verdict(obligations, findings, [])

    assert result.verdict is CompletionVerdict.INCOMPLETE
    assert result.escalation_candidates == ["b"]


def test_completion_result_round_trips_through_persistence():
    from acceptance.review_state import CompletionResult

    result = derive_verdict([_obligation("a", "strongly_supported")], [], [])
    assert CompletionResult.from_dict(result.to_dict()) == result

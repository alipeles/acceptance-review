"""M7.2 acceptance: the completion verdict is derived deterministically from
the findings, one of no-material-gaps / incomplete / needs-clarification /
needs-non-code-review / unable-to-determine; a positive verdict renders the
§3.7 "no material gaps at the achievable tier" caveat; an unresolved open
question blocks a positive verdict (#113).

derive_verdict is a pure function, so these assert its output directly — no
model call is involved in the headline result at all."""

import inspect

from acceptance.review_state import (
    AdmissibleEvidence,
    CompletionVerdict,
    Finding,
    Link,
    Obligation,
    ObligationType,
    OpenQuestion,
)
from acceptance.evidence_tier import Component, EvidenceTier
from acceptance.verdict import derive_verdict


def _obligation(
    obligation_id: str, evidence_class: str | None, importance: str = "critical"
) -> Obligation:
    return Obligation(
        id=obligation_id,
        description=f"{obligation_id} behavior",
        type=ObligationType.FUNCTIONAL,
        importance=importance,
        explicit=True,
        observable_behavior="...",
        evidence_class=evidence_class,
    )


def _coverage_gap(obligation_description: str) -> Finding:
    return Finding(
        type="coverage_gap",
        severity="high",
        description="missing",
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="requirement", ref="x", text="x")],
        related_obligation=obligation_description,
    )


def _advisory_finding(finding_type: str) -> Finding:
    return Finding(
        type=finding_type,
        severity="low",
        description="advisory",
        evidence_tier=EvidenceTier.BUILDER_CLAIM,
        produced_by=Component.BUILDER_DECLARATION,
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


def test_the_weak_count_is_read_off_the_obligations_not_the_recommendations():
    """The summary's weak count must not be derivable from the recommendation
    list (#218).

    If it were, a response that skipped a recommendation would *lower* the
    reported weak count — a decomposer-style blindness where answering less
    scores better (#214). `derive_verdict` is not given the recommendations at
    all, which is the strongest form of that guarantee; this pins it, since a
    later refactor threading them in would look harmless.
    """
    obligations = [
        _obligation("a", "nominally_supported"),
        _obligation("b", "unsupported"),
        _obligation("c", "strongly_supported"),
    ]

    result = derive_verdict(obligations, [], [])

    assert "2 obligation(s) with non-discriminating test evidence" in result.rationale
    assert "recommendation" not in inspect.signature(derive_verdict).parameters


# --- #153: the code-evidence-only axis ---------------------------------------


def _boundary_obligation(obligation_id: str, evidence_class: str | None = None) -> Obligation:
    """An obligation derived from a `## Scope exclusions` bullet."""
    return Obligation(
        id=obligation_id,
        description=f"The change does not alter {obligation_id}",
        type=ObligationType.INVARIANT,
        importance="critical",
        explicit=True,
        observable_behavior="...",
        evidence_class=evidence_class,
        admissible_evidence=AdmissibleEvidence.CODE_ONLY,
    )


def test_a_code_evidence_only_obligation_does_not_make_the_verdict_incomplete():
    """#153's acceptance. `unsupported` on a boundary obligation is not a gap:
    no test can assert that excluded work was not done, so the absence of one
    is the expected state rather than a missing deliverable.

    Paired with an ordinary strongly-supported obligation so the verdict has
    something to be positive about, and the boundary one is the only candidate
    gap in the set."""
    result = derive_verdict(
        [
            _obligation("ok", "strongly_supported"),
            _boundary_obligation("pagination", "unsupported"),
        ],
        [],
        [],
    )

    assert result.verdict is CompletionVerdict.NO_MATERIAL_GAPS


def test_an_unclassified_code_evidence_only_obligation_is_not_indeterminate():
    """The None case, separately: an ordinary obligation with no evidence_class
    is treated as indeterminate (test_unclassified_evidence_is_treated_as_
    indeterminate). A boundary obligation is never classified on that axis at
    all, so the same None must not escalate."""
    result = derive_verdict(
        [_obligation("ok", "strongly_supported"), _boundary_obligation("currencies", None)],
        [],
        [],
    )

    assert result.verdict is CompletionVerdict.NO_MATERIAL_GAPS
    assert result.escalation_candidates == []


def test_a_breached_boundary_is_still_a_material_gap():
    """The other half, and the one that keeps the exclusion falsifiable. #153
    exempts boundary obligations from the TEST axis only. A coverage gap against
    one — the diff crossing the boundary — is a material gap like any other, and
    a change that exempted the whole obligation would make an exclusion
    impossible to violate."""
    breached = _boundary_obligation("pagination", None)
    result = derive_verdict(
        [_obligation("ok", "strongly_supported"), breached],
        [_coverage_gap(breached.description)],
        [],
    )

    assert result.verdict is CompletionVerdict.INCOMPLETE
    assert breached.id in result.rationale


def test_a_positive_rationale_does_not_claim_tests_for_a_boundary_obligation():
    """§3.7 applied to the sentence itself. "Every obligation is addressed and
    strongly supported by discriminating tests" is false when one of them was
    confirmed by an absence, and claiming discriminating tests that cannot exist
    is the overclaim the bound exists to prevent."""
    result = derive_verdict(
        [_obligation("ok", "strongly_supported"), _boundary_obligation("currencies")],
        [],
        [],
    )

    assert result.verdict is CompletionVerdict.NO_MATERIAL_GAPS
    assert "Every obligation" not in result.rationale
    assert "boundary" in result.rationale

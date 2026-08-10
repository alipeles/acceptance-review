"""Completion verdict derivation (M7.2, §10.1 step 11, §3.7).

Rolls the findings up into one overall result:
no-material-gaps / incomplete / needs-clarification / needs-non-code-review /
unable-to-determine.

This is a **deterministic, pure function of the findings** — never a model
call. The headline result is the product's most consequential output, so it
must be auditable: it traces to the exact obligations/findings that produced
it, not a free-text conclusion a model asserted (§13.6, "no free-text
conclusions"). "Trying harder" on a hard case belongs upstream — resolving an
`indeterminate` finding via deeper retrieval or execution raises its evidence,
and then this same function re-derives cleanly. `escalation_candidates` names
exactly where that extra effort would matter, so the seam for a future
"try harder" loop is explicit while the rollup stays a stable function.

Materiality is strict here: any coverage gap or any non-strong test evidence
blocks a positive verdict ("positive results are bounded," §3.7 — decision A).
Severity/importance-weighted materiality (a low-severity gap on a normal-
importance obligation counting as immaterial) is a deliberate future
refinement, not built now.

Advisory findings never move the verdict: an `unrequested_change` (real code,
scored on its own axis) and a `declaration_mismatch` (a bogus claim about
undone work) are flagged but do not block acceptance of the delivered change
(DR-081, issue #31) — so a change whose obligations are all strongly supported
is `no_material_gaps` even alongside an advisory declaration overclaim.
"""

from __future__ import annotations

from acceptance.coverage.open_questions import derived_obligation_id
from acceptance.review_state import (
    AdmissibleEvidence,
    CompletionResult,
    CompletionVerdict,
    Disposition,
    Finding,
    MandateCoverage,
    Obligation,
    OpenQuestion,
    RequirementMap,
)

# §9.3 classes that are a real evidence gap short of strong support (decision A).
_WEAK_EVIDENCE = {"partially_supported", "nominally_supported", "unsupported"}

_POSITIVE_CAVEAT = (
    "No material gaps found at the achievable evidence tier — not proof of "
    "correctness. The full application was not independently executed (§3.7)."
)
_STATIC_CAVEAT = (
    "Judgments are static inferences unless a higher tier is recorded; the "
    "full application was not independently executed."
)


def assess_mandate_coverage(
    requirement_map: RequirementMap | None,
    obligations: list[Obligation],
) -> MandateCoverage | None:
    """How much of the mandate this review was able to judge (#214).

    Decided from each requirement's `Disposition`, never from reading its text.
    That is what makes this a rule rather than a judgment call, and it is only
    possible because the disposition is enforced rather than trusted: a
    `yielded` disposition naming no obligation and a `no_obligation` disposition
    with no reason are both rejected at parse, so the three cases below are
    exhaustive and each means exactly what it says.

    - `yielded` — obligations exist. Judged.
    - `no_obligation` — a decision the decomposer made and stated a reason for.
      **Taken at face value**, so a bare section marker costs nothing. Whether
      the decline was CORRECT is decomposition quality (#193, #211); re-judging
      it here would put a second, weaker decomposer inside the verdict.
    - `open_question` — judged only if the question produced a derived
      obligation, which happens when the diff resolved it. A question the diff
      left open produces nothing that any later stage can bear on, so the review
      genuinely cannot speak to that requirement.
    """
    if requirement_map is None or not requirement_map.requirements:
        return None

    obligation_ids = {obligation.id for obligation in obligations}
    declined: list[str] = []
    unjudged: list[str] = []
    for entry in requirement_map.dispositions:
        if entry.obligation_ids:
            continue
        if entry.disposition is Disposition.NO_OBLIGATION:
            declined.append(entry.requirement_id)
            continue
        # An `open_question` disposition. Judged only via what the resolution
        # derived; `unyielding()` cannot answer this, since it predates derived
        # obligations and reports the requirement as producing nothing either way.
        if any(
            derived_obligation_id(question_id) in obligation_ids
            for question_id in entry.open_question_ids
        ):
            continue
        unjudged.append(entry.requirement_id)

    return MandateCoverage(
        total_requirements=len(requirement_map.requirements),
        declined_requirements=declined,
        unjudged_requirements=unjudged,
        unread_source_blocks=len(requirement_map.unread_source),
    )


def derive_verdict(
    obligations: list[Obligation],
    findings: list[Finding],
    open_questions: list[OpenQuestion],
    requirement_map: RequirementMap | None = None,
) -> CompletionResult:
    """Deterministically roll the review up into one completion verdict."""
    coverage = assess_mandate_coverage(requirement_map, obligations)
    if not obligations:
        return _bounded(
            CompletionResult(
                verdict=CompletionVerdict.UNABLE_TO_DETERMINE,
                rationale="No obligations were derived from the task; nothing to assess.",
                limitations=[_STATIC_CAVEAT],
            ),
            coverage,
        )

    gap_obligations = {
        finding.related_obligation
        for finding in findings
        if finding.type == "coverage_gap" and finding.related_obligation is not None
    }

    material_gaps: list[str] = []
    weak_evidence: list[str] = []
    non_code: list[str] = []
    indeterminate: list[str] = []
    code_only: list[str] = []
    for obligation in obligations:
        if obligation.description in gap_obligations:
            material_gaps.append(obligation.id)  # code missing/partial — a coverage gap
            continue
        if obligation.admissible_evidence is AdmissibleEvidence.CODE_ONLY:
            code_only.append(obligation.id)
            # #153: the test-evidence axis does not apply, so no value on it —
            # including None — is a gap. It still reached the coverage-gap check
            # above, which is the axis that DOES apply: a breached boundary is a
            # material gap like any other. Skipping the whole obligation instead
            # would make an exclusion unfalsifiable.
            continue
        evidence = obligation.evidence_class
        if evidence == "requires_other_evidence":
            non_code.append(obligation.id)
        elif evidence in _WEAK_EVIDENCE:
            weak_evidence.append(obligation.id)  # present but non-discriminating tests
        elif evidence == "indeterminate" or evidence is None:
            indeterminate.append(obligation.id)
        # strongly_supported -> no gap

    unresolved = [q.id for q in open_questions if not q.resolved]

    # Precedence: an unresolved material ambiguity undermines every other
    # judgment, so it comes first; a definite gap (code or evidence) outranks
    # mere uncertainty (indeterminate); advisory findings never appear here.
    if unresolved:
        return _bounded(
            CompletionResult(
                verdict=CompletionVerdict.NEEDS_CLARIFICATION,
                rationale=(
                    f"{len(unresolved)} open question(s) remain unresolved by the diff; "
                    "the delivered behavior cannot be judged until they are answered."
                ),
                limitations=[_STATIC_CAVEAT],
                escalation_candidates=indeterminate,
            ),
            coverage,
        )
    if material_gaps or weak_evidence:
        return _bounded(
            CompletionResult(
                verdict=CompletionVerdict.INCOMPLETE,
                rationale=_incomplete_rationale(material_gaps, weak_evidence),
                limitations=[_STATIC_CAVEAT],
                escalation_candidates=indeterminate,
            ),
            coverage,
        )
    if non_code:
        return _bounded(
            CompletionResult(
                verdict=CompletionVerdict.NEEDS_NON_CODE_REVIEW,
                rationale=(
                    f"{len(non_code)} obligation(s) require evidence the code and tests "
                    "cannot provide (docs, runtime, or deploy behavior)."
                ),
                limitations=[_STATIC_CAVEAT],
                escalation_candidates=indeterminate,
            ),
            coverage,
        )
    if indeterminate:
        return _bounded(
            CompletionResult(
                verdict=CompletionVerdict.UNABLE_TO_DETERMINE,
                rationale=(
                    f"{len(indeterminate)} obligation(s) could not be classified from static "
                    "evidence; deeper retrieval or execution would be needed to decide."
                ),
                limitations=[_STATIC_CAVEAT],
                escalation_candidates=indeterminate,
            ),
            coverage,
        )
    # Only the obligations the test-evidence axis applies to can be described as
    # test-supported. Saying "every obligation" while a boundary was confirmed by
    # the absence of work would claim discriminating tests that do not and cannot
    # exist — the §3.7 bound on positive results, applied to the sentence itself.
    if code_only:
        rationale = (
            f"{len(obligations) - len(code_only)} obligation(s) addressed and strongly "
            f"supported by discriminating tests; {len(code_only)} boundary "
            "obligation(s) confirmed from code evidence, which is the only kind "
            "that applies to them."
        )
    else:
        rationale = "Every obligation is addressed and strongly supported by discriminating tests."
    return _bounded(
        CompletionResult(
            verdict=CompletionVerdict.NO_MATERIAL_GAPS,
            rationale=rationale,
            limitations=[_POSITIVE_CAVEAT],
        ),
        coverage,
    )


def _bounded(result: CompletionResult, coverage: MandateCoverage | None) -> CompletionResult:
    """Record mandate coverage on the result, and let a shortfall CAP it (#214).

    Applied after the derivation above rather than as another branch inside it,
    which is what makes "a decomposer that drops requirements scores worse,
    never better" true mechanically instead of by inspection. A bound can only
    ever move the verdict away from `no_material_gaps`; it can never move one
    toward it, and it never re-orders the existing precedence. Dropping a
    requirement therefore cannot launder a known gap into a softer-sounding
    result — an `incomplete` review stays `incomplete` and gains a disclosure.

    The shortfall lands on `unable_to_determine` because that is already what
    this function returns when NO obligations were derived. That is this same
    rule at its limit, so generalizing from "covered none of the mandate" to
    "covered part of it" keeps one meaning rather than inventing a second, and
    it matches the standing invariant that uncertainty is first-class: a
    requirement the review could not judge is uncertainty, not a pass.

    The figure is recorded on EVERY result, including complete ones. Two reviews
    with identical obligation-level evidence and different mandate coverage must
    not be the same result, and when both would otherwise be positive the enum
    alone cannot express that.
    """
    if coverage is None:
        return result
    result = result.model_copy(update={"mandate_coverage": coverage})
    if coverage.complete:
        return result

    shortfall = _shortfall(coverage)
    if result.verdict is CompletionVerdict.NO_MATERIAL_GAPS:
        return result.model_copy(
            update={
                "verdict": CompletionVerdict.UNABLE_TO_DETERMINE,
                "rationale": (
                    f"{result.rationale} But {shortfall} — so the review speaks to part "
                    "of the mandate only, and cannot report that it found no material "
                    "gaps."
                ),
                "limitations": [_STATIC_CAVEAT],
            }
        )
    # Already non-positive: the bound changes nothing about the verdict, but the
    # shortfall is still disclosed. Suppressing it because the verdict was
    # negative anyway would hide it exactly when the review is being revised.
    return result.model_copy(
        update={"limitations": [*result.limitations, f"Mandate coverage: {shortfall}."]}
    )


def _shortfall(coverage: MandateCoverage) -> str:
    parts = []
    if coverage.unjudged_requirements:
        parts.append(
            f"{len(coverage.unjudged_requirements)} of {coverage.total_requirements} "
            "requirement(s) produced no obligation this review could judge "
            f"({', '.join(coverage.unjudged_requirements)})"
        )
    if coverage.unread_source_blocks:
        parts.append(
            f"{coverage.unread_source_blocks} block(s) of the task file were read as no "
            "requirement at all"
        )
    return "; ".join(parts)


def _incomplete_rationale(material_gaps: list[str], weak_evidence: list[str]) -> str:
    parts = []
    if material_gaps:
        parts.append(
            f"{len(material_gaps)} obligation(s) not fully implemented ({', '.join(material_gaps)})"
        )
    if weak_evidence:
        parts.append(
            f"{len(weak_evidence)} obligation(s) with non-discriminating test evidence "
            f"({', '.join(weak_evidence)})"
        )
    return "; ".join(parts) + "."

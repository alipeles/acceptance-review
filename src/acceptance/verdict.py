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

from acceptance.review_state import (
    AdmissibleEvidence,
    CompletionResult,
    CompletionVerdict,
    Finding,
    Obligation,
    OpenQuestion,
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


def derive_verdict(
    obligations: list[Obligation],
    findings: list[Finding],
    open_questions: list[OpenQuestion],
) -> CompletionResult:
    """Deterministically roll the review up into one completion verdict."""
    if not obligations:
        return CompletionResult(
            verdict=CompletionVerdict.UNABLE_TO_DETERMINE,
            rationale="No obligations were derived from the task; nothing to assess.",
            limitations=[_STATIC_CAVEAT],
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
        return CompletionResult(
            verdict=CompletionVerdict.NEEDS_CLARIFICATION,
            rationale=(
                f"{len(unresolved)} open question(s) remain unresolved by the diff; "
                "the delivered behavior cannot be judged until they are answered."
            ),
            limitations=[_STATIC_CAVEAT],
            escalation_candidates=indeterminate,
        )
    if material_gaps or weak_evidence:
        return CompletionResult(
            verdict=CompletionVerdict.INCOMPLETE,
            rationale=_incomplete_rationale(material_gaps, weak_evidence),
            limitations=[_STATIC_CAVEAT],
            escalation_candidates=indeterminate,
        )
    if non_code:
        return CompletionResult(
            verdict=CompletionVerdict.NEEDS_NON_CODE_REVIEW,
            rationale=(
                f"{len(non_code)} obligation(s) require evidence the code and tests "
                "cannot provide (docs, runtime, or deploy behavior)."
            ),
            limitations=[_STATIC_CAVEAT],
            escalation_candidates=indeterminate,
        )
    if indeterminate:
        return CompletionResult(
            verdict=CompletionVerdict.UNABLE_TO_DETERMINE,
            rationale=(
                f"{len(indeterminate)} obligation(s) could not be classified from static "
                "evidence; deeper retrieval or execution would be needed to decide."
            ),
            limitations=[_STATIC_CAVEAT],
            escalation_candidates=indeterminate,
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
    return CompletionResult(
        verdict=CompletionVerdict.NO_MATERIAL_GAPS,
        rationale=rationale,
        limitations=[_POSITIVE_CAVEAT],
    )


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

"""§16 CLI report rendering (M0.6 skeleton; filled in by M7.4).

Renders a Review as the §16 layout: the completion verdict, the two review
axes as separate sections — implementation coverage (§9.2, "does the code
respond") and test evidence (§9.3, "do the tests discriminate") — advisory
unrequested changes, and the next-instruction pointer.

Every conclusion is labeled with its evidence tier (§8.1, §16): a static
inference is never presented as execution-confirmed. Test-evidence lines carry
both the §9.3 strength class and the tier that produced it.
"""

from __future__ import annotations

from acceptance.review_state import UNREQUESTED_CHANGE, Obligation, Review

_EMPTY = "  (none)"

# §16 obligation-coverage markers: addressed / not addressed / uncertain.
_COVERAGE_MARKER = {
    "addressed": "✓",
    "partially_addressed": "✗",
    "not_addressed": "✗",
    "unclear": "?",
    "requires_non_code_evidence": "?",
}

# §9.3 evidence classes that count as real support in the §16 test-evidence
# column; everything else is a gap the reader must see as unmet.
_EVIDENCE_MARKER = {
    "strongly_supported": "✓",
    "partially_supported": "✗",
    "nominally_supported": "✗",
    "unsupported": "✗",
    "requires_other_evidence": "?",
    "indeterminate": "?",
}


def render_report(review: Review) -> str:
    lines: list[str] = [f"Task completion: {_completion_status(review)}", ""]

    completion = review.completion
    if completion is not None and completion.rationale:
        lines.append(completion.rationale)
        lines.append("")

    lines.append("Obligation coverage:")
    if review.obligation_map:
        lines += [
            f"  {_COVERAGE_MARKER.get(o.coverage_status or '', '?')} {o.description}"
            for o in review.obligation_map
        ]
    else:
        lines.append(_EMPTY)
    lines.append("")

    lines.append("Test evidence:")
    if review.obligation_map:
        lines += [_evidence_line(o) for o in review.obligation_map]
    else:
        lines.append(_EMPTY)
    lines.append("")

    lines.append("Unrequested changes:")
    unrequested = [f for f in review.findings if f.type == UNREQUESTED_CHANGE]
    if unrequested:
        for finding in unrequested:
            disposition = finding.disposition.value if finding.disposition else "unclassified"
            lines.append(f"  ! [{disposition}] {finding.description}")
    else:
        lines.append(_EMPTY)
    lines.append("")

    if review.open_questions:
        lines.append("Open questions:")
        for question in review.open_questions:
            marker = "resolved" if question.resolved else "open"
            lines.append(f"  [{marker}] {question.question}")
        lines.append("")

    if review.recommendations:
        lines.append("Recommended tests:")
        for rec in review.recommendations:
            lines.append(f"  - {rec.criterion}")
            lines.append(f"      inputs: {rec.required_inputs}")
            lines.append(f"      detects: {rec.plausible_defect}")
        lines.append("")

    if completion is not None and completion.limitations:
        lines.append("Evidence limitations:")
        lines += [f"  - {limitation}" for limitation in completion.limitations]
        lines.append("")

    lines.append(f"Recommended next instruction: {review.recommendation or '(none)'}")

    return "\n".join(lines)


def _evidence_line(obligation: Obligation) -> str:
    """One §16 test-evidence line: marker, criterion, §9.3 class, and the §8.1
    tier that produced it — a static prediction is never shown as confirmed."""
    evidence = obligation.evidence_class
    marker = _EVIDENCE_MARKER.get(evidence or "", "?")
    label = (evidence or "unclassified").replace("_", " ")
    tier = obligation.achieved_evidence_tier
    tier_name = tier.name.lower().replace("_", "-") if tier is not None else "none"
    return f"  {marker} {obligation.description}  [{label}; tier: {tier_name}]"


def _completion_status(review: Review) -> str:
    """The M7.2 verdict, rendered as the §16 headline. A review with no
    computed verdict is honestly INDETERMINATE (§9.3) rather than assumed
    good — uncertainty is a first-class result."""
    if review.completion is None:
        return "INDETERMINATE"
    return review.completion.verdict.value.replace("_", "-").upper()

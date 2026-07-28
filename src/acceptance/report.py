"""§16 CLI report rendering (M0.6 skeleton; filled in and restructured by M7.4).

Renders a Review as a numbered, per-obligation report: each obligation is a
block carrying BOTH review axes beneath it — code evidence (§9.2, "does the
code respond") and test evidence (§9.3, "do the tests discriminate"). Grouping
by obligation keeps a criterion's two axes together, where a flat pair of
sections made the reader join them by eye.

Every line is numbered so a reader can refer to one precisely ("evidence 2.3",
"unrequested change 1"). Numbering is positional within a report — for a
stable cross-run handle, obligations also carry their `id` in the data model.

Status is stated in words, not symbols, and every evidence line carries its
§8.1 tier: a static inference is never presented as execution-confirmed.
"""

from __future__ import annotations

from acceptance.review_state import UNREQUESTED_CHANGE, Obligation, Review

_EMPTY = "  (none)"
_NO_CODE = "(no corresponding change)"
_NO_TESTS = "(no mapped test)"


def render_report(review: Review) -> str:
    lines: list[str] = [f"Task completion: {_completion_status(review)}", ""]

    completion = review.completion
    if completion is not None and completion.rationale:
        lines.append(completion.rationale)
        lines.append("")

    lines.append("Obligations:")
    if review.obligation_map:
        for index, obligation in enumerate(review.obligation_map, start=1):
            lines.append("")
            lines.extend(_obligation_block(index, obligation))
    else:
        lines.append(_EMPTY)
    lines.append("")

    lines.append("Unrequested changes:")
    unrequested = [f for f in review.findings if f.type == UNREQUESTED_CHANGE]
    if unrequested:
        for index, finding in enumerate(unrequested, start=1):
            disposition = finding.disposition.value if finding.disposition else "unclassified"
            lines.append(f"  {index}. [{disposition}] {finding.description}")
            for link in finding.links:
                lines.append(f"       {link.ref}")
    else:
        lines.append(_EMPTY)
    lines.append("")

    if review.open_questions:
        lines.append("Open questions:")
        for index, question in enumerate(review.open_questions, start=1):
            state = "resolved" if question.resolved else "open"
            lines.append(f"  {index}. [{state}] {question.question}")
            if question.resolved and question.resolution_rationale:
                lines.append(f"       {question.resolution_rationale}")
        lines.append("")

    if review.recommendations:
        lines.append("Recommended tests:")
        for index, rec in enumerate(review.recommendations, start=1):
            lines.append(f"  {index}. {rec.criterion}")
            lines.append(f"       inputs:  {rec.required_inputs}")
            lines.append(f"       detects: {rec.plausible_defect}")
        lines.append("")

    if completion is not None and completion.limitations:
        lines.append("Evidence limitations:")
        for index, limitation in enumerate(completion.limitations, start=1):
            lines.append(f"  {index}. {limitation}")
        lines.append("")

    lines.append(f"Recommended next instruction: {review.recommendation or '(none)'}")

    return "\n".join(lines)


def _obligation_block(index: int, obligation: Obligation) -> list[str]:
    """One numbered obligation with both evidence axes nested beneath it.

    Evidence items are numbered `<obligation>.<item>` continuously across both
    axes, so every citation in the report has a unique handle."""
    lines = [f"  {index}. {obligation.description}"]
    item = 0

    coverage = (obligation.coverage_status or "unclassified").replace("_", " ")
    lines.append(f"       code evidence: {coverage}")
    if obligation.coverage_refs:
        for ref in obligation.coverage_refs:
            item += 1
            lines.append(f"         {index}.{item}  {ref}")
    else:
        lines.append(f"         {_NO_CODE}")

    evidence = (obligation.evidence_class or "unclassified").replace("_", " ")
    tier = obligation.achieved_evidence_tier
    tier_name = tier.name.lower().replace("_", "-") if tier is not None else "none"
    lines.append(f"       test evidence: {evidence}  [tier: {tier_name}]")
    if obligation.test_evidence:
        for test_id in obligation.test_evidence:
            item += 1
            lines.append(f"         {index}.{item}  {test_id}")
    else:
        lines.append(f"         {_NO_TESTS}")

    return lines


def _completion_status(review: Review) -> str:
    """The M7.2 verdict, rendered as the §16 headline. A review with no
    computed verdict is honestly INDETERMINATE (§9.3) rather than assumed
    good — uncertainty is a first-class result."""
    if review.completion is None:
        return "INDETERMINATE"
    return review.completion.verdict.value.replace("_", "-").upper()

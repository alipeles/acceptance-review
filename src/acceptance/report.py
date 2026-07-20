"""§16 CLI report rendering (M0.6).

Renders a Review as the human-readable §16 shell — every section always
present, empty ones shown as "(none)". This is the walking skeleton's output:
with an empty Review it prints the full shape with nothing in it, and later
milestones (M3 coverage classification, M5 test evidence, M7 verdict and
next-instruction) fill the sections in.

The completion status is INDETERMINATE for a review with no analyzed
obligations — a first-class, valid outcome (§9.3), not a fabricated verdict.
M7.2 adds the real computed verdict.
"""

from __future__ import annotations

from acceptance.review_state import Review

_EMPTY = "  (none)"

# M3 replaces this with real ✓/✗/? coverage classification per obligation.
_OBLIGATION_MARKER = "?"


def render_report(review: Review) -> str:
    lines: list[str] = [f"Task completion: {_completion_status(review)}", ""]

    lines.append("Obligation coverage:")
    if review.obligation_map:
        lines += [f"  {_OBLIGATION_MARKER} {o.description}" for o in review.obligation_map]
    else:
        lines.append(_EMPTY)
    lines.append("")

    lines.append("Test evidence:")
    if review.findings:
        for finding in review.findings:
            tier = finding.evidence_tier.name.lower().replace("_", "-")
            lines.append(f"  - {finding.description} [{tier}]")
    else:
        lines.append(_EMPTY)
    lines.append("")

    lines.append("Unrequested changes:")
    # Unrequested-change detection is M3.2; the section is present but empty.
    lines.append(_EMPTY)
    lines.append("")

    lines.append(f"Recommended next instruction: {review.recommendation or '(none)'}")

    return "\n".join(lines)


def _completion_status(review: Review) -> str:
    # M7.2 computes the real verdict from obligation/finding state; until then a
    # review with nothing analyzed is honestly INDETERMINATE (§9.3).
    return "INDETERMINATE"

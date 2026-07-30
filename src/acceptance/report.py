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

from acceptance.review_state import (
    UNREQUESTED_CHANGE,
    CompletionVerdict,
    Obligation,
    Review,
)

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

    if review.delta is not None:
        lines.extend(_delta_block(review.delta))
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


def render_next_instruction(review: Review) -> str | None:
    """The §10.1 step-12 next instruction, or None when there is nothing to do.

    A deliberately thin projection of the same Review `render_report` renders —
    no new judgment, no model call, every line traced to a finding, an M7.1
    recommendation, or an unresolved open question. What it adds over the §16
    report is SELECTION and mood: the report says "here is everything I found,
    you judge"; this says "here is what to do next", addressed to the coding
    agent rather than the human reviewer. So it drops satisfied obligations,
    advisory unrequested changes, and evidence limitations.

    Kept beside `render_report` rather than in its own module because both are
    the same concern (render a Review for a consumer) — and kept a SEPARATE
    function because the two audiences diverge: terminal styling (M7.6) must
    never reach a file on disk, and reviewer-facing explanations (#143) are
    noise in an agent handoff.

    Produced only when gaps exist (§10.1 step 12), keyed off M7.2's verdict so
    there is no second definition of what counts as material.
    """
    if review.completion is not None and review.completion.verdict is CompletionVerdict.NO_MATERIAL_GAPS:
        return None

    gaps = [
        f.related_obligation
        for f in review.findings
        if f.type == "coverage_gap" and f.related_obligation is not None
    ]
    unresolved = [q.question for q in review.open_questions if not q.resolved]
    if not gaps and not review.recommendations and not unresolved:
        return None

    lines = ["# Next instruction", ""]
    if review.completion is not None:
        lines += [f"Review verdict: **{review.completion.verdict.value}**.", ""]

    if unresolved:
        lines.append("## Answer these first")
        lines += [f"{i}. {q}" for i, q in enumerate(unresolved, start=1)]
        lines += ["", "These are unresolved ambiguities in the task; the work cannot be "
                  "judged complete until they are settled.", ""]

    if gaps:
        lines.append("## Implement")
        lines += [f"{i}. {g}" for i, g in enumerate(gaps, start=1)]
        lines.append("")

    if review.recommendations:
        lines.append("## Add these tests")
        for i, rec in enumerate(review.recommendations, start=1):
            lines.append(f"{i}. **{rec.criterion}**")
            lines.append(f"   - Inputs: {rec.required_inputs}")
            if rec.boundary_conditions:
                lines.append(f"   - Boundaries: {rec.boundary_conditions}")
            lines.append(f"   - Expected: {rec.expected_output}")
            for assertion in rec.required_assertions:
                lines.append(f"   - Assert: {assertion}")
            lines.append(f"   - Must fail if: {rec.plausible_defect}")
            if rec.repo_conventions:
                lines.append(f"   - Conventions: {rec.repo_conventions}")
        lines.append("")

    lines.append("Update the builder declaration after the changes.")
    return "\n".join(lines)


def _short(revision: str) -> str:
    """Abbreviate a sha; leave a non-sha marker like `<working-tree>` alone."""
    return revision[:8] if len(revision) == 40 and revision.isalnum() else revision


def _verdict(value: str | None) -> str:
    return value.replace("_", "-").upper() if value else "INDETERMINATE"


def _movement(previous: str | None, current: str | None) -> str:
    before = (previous or "unclassified").replace("_", " ")
    after = (current or "unclassified").replace("_", " ")
    return f"{before} -> {after}"


def _delta_block(delta) -> list[str]:
    """What moved since the prior review this run built on (M7.5, §13.5 #9).

    Closed gaps lead, because that is the answer to the question the previous
    review posed — it told the agent what to fix, and this is whether it did.
    """
    lines = [f"Changes since {_short(delta.prior_reviewed_revision)}:"]

    closed = delta.closed_gaps()
    if closed:
        lines.append("  closed:")
        for change in closed:
            lines.append(f"    - {change.description}")
            lines.append(
                f"        code evidence: {_movement(change.previous_coverage_status, change.coverage_status)}"
            )
            lines.append(
                f"        test evidence: {_movement(change.previous_evidence_class, change.evidence_class)}"
            )

    remaining = [change for change in delta.obligation_changes if not change.closed_gap()]
    if remaining:
        lines.append("  moved:")
        for change in remaining:
            lines.append(f"    - {change.description}")
            if change.previous_coverage_status != change.coverage_status:
                lines.append(
                    f"        code evidence: {_movement(change.previous_coverage_status, change.coverage_status)}"
                )
            if change.previous_evidence_class != change.evidence_class:
                lines.append(
                    f"        test evidence: {_movement(change.previous_evidence_class, change.evidence_class)}"
                )

    if not delta.obligation_changes:
        lines.append("  no obligation changed status.")

    if delta.previous_verdict != delta.verdict:
        # Same spelling as the §16 headline (`_completion_status`), so the
        # movement reads as the same vocabulary the reader just saw at the top.
        before = _verdict(delta.previous_verdict)
        after = _verdict(delta.verdict)
        lines.append(f"  verdict: {before} -> {after}")

    if delta.carried_forward_obligation_ids:
        count = len(delta.carried_forward_obligation_ids)
        lines.append(
            f"  {count} obligation(s) carried forward unchanged — "
            "their code and tests were untouched by this work."
        )

    return lines


def _obligation_block(index: int, obligation: Obligation) -> list[str]:
    """One numbered obligation with both evidence axes nested beneath it.

    Evidence items are numbered `<obligation>.<item>` continuously across both
    axes, so every citation in the report has a unique handle."""
    lines = [f"  {index}. {obligation.description}"]
    item = 0

    # A carried-forward judgment is evidence about an OLDER head. Saying so on
    # the obligation itself, not only in the delta section, is what stops a
    # reader taking it as something this run checked (M7.5).
    if obligation.carried_forward_from is not None:
        lines.append(
            f"       [carried forward from {_short(obligation.carried_forward_from)}"
            " — not re-derived for this head]"
        )

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

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
    RequirementMap,
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
            lines.extend(_obligation_block(index, obligation, review.requirement_map))
    else:
        lines.append(_EMPTY)
    lines.append("")

    if review.requirement_map is not None:
        lines.extend(_mandate_coverage_block(review.requirement_map))
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
            # §9.5's single-iteration goal depends on the agent KNOWING the full
            # prescription exists. Naming the command per recommendation — rather
            # than once at the foot of the report — is what makes the pull happen
            # at the moment the reader decides to act on this criterion.
            lines.append(
                f"       full detail: acceptance recommendation --criterion {rec.obligation_id}"
            )
        lines.append("")

    if completion is not None and completion.limitations:
        lines.append("Evidence limitations:")
        for index, limitation in enumerate(completion.limitations, start=1):
            lines.append(f"  {index}. {limitation}")
        lines.append("")

    # A command, never a file (M7.3.r1). The artifact this used to name was
    # written speculatively and never cleaned up, so a clean run printed
    # "(none)" while a stale file on disk still asserted gaps. Pointing at a
    # command that reads current review state cannot go out of date.
    if _has_gaps(review):
        lines.append(
            "Next: retrieve a criterion's full recommendation with\n"
            "  acceptance recommendation --criterion <id>"
        )
    else:
        lines.append("Recommended next instruction: (none)")

    return "\n".join(lines)


def _has_gaps(review: Review) -> bool:
    """Whether there is anything for the next iteration to act on.

    Keyed off M7.2's verdict so there is no second definition of what counts as
    material — but a non-positive verdict is not sufficient on its own. A review
    with no obligations is `unable_to_determine` and has nothing to pull, so
    pointing it at the retrieval command would advertise detail that does not
    exist. Both conditions, exactly as the pushed instruction required them
    before it was removed.
    """
    if review.completion is None:
        return False
    if review.completion.verdict is CompletionVerdict.NO_MATERIAL_GAPS:
        return False
    # A review with no obligations is `unable_to_determine` because there was
    # nothing to assess, not because something is wrong — the one non-positive
    # verdict with nothing to pull.
    return bool(review.obligation_map)


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


def _mandate_coverage_block(requirement_map: RequirementMap) -> list[str]:
    """Which requirements of the mandate produced nothing (M1.2.r1, DR-202).

    This section exists because its absence was the defect. A requirement that
    yielded no obligation used simply not to appear anywhere in the review, so a
    breakdown covering 20 of 29 requirements read exactly like one covering all
    29 — the reader was told nothing was missing because nothing was there to
    say it. Rendering the empty case is the whole point: an `undisposed`
    requirement is a claim about the REVIEW, not about the code, and it belongs
    in front of the person who can act on it.
    """
    total = len(requirement_map.requirements)
    if not total:
        return []

    unyielding = requirement_map.unyielding()
    lines = [f"Mandate coverage: {total - len(unyielding)} of {total} requirements yielded obligations"]
    if not unyielding:
        lines.append(_EMPTY)
        return lines

    for index, entry in enumerate(unyielding, start=1):
        requirement = requirement_map.requirement_for(entry.requirement_id)
        text = requirement.text if requirement is not None else ""
        lines.append(f"  {index}. [{entry.disposition.value}] {entry.requirement_id}: {text}")
        if entry.reason:
            lines.append(f"       reason: {entry.reason}")
        if entry.open_question_ids:
            lines.append(f"       raised: {', '.join(entry.open_question_ids)}")
    return lines


def _obligation_block(
    index: int, obligation: Obligation, requirement_map: RequirementMap | None = None
) -> list[str]:
    """One numbered obligation with both evidence axes nested beneath it.

    Evidence items are numbered `<obligation>.<item>` continuously across both
    axes, so every citation in the report has a unique handle."""
    lines = [f"  {index}. {obligation.description}"]
    item = 0

    # Which requirements this obligation serves. Before M1.2.r1 the trace ran
    # one way and only to a character offset, so auditing a breakdown meant
    # reconciling obligations against the task file by hand.
    if requirement_map is not None:
        served = requirement_map.requirements_for_obligation(obligation.id)
        if served:
            lines.append(f"       requirements: {', '.join(served)}")

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

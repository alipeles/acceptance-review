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

from acceptance.defects.pair_mapping import derive_support
from acceptance.review_state import (
    UNREQUESTED_CHANGE,
    CompletionVerdict,
    DefectSet,
    MandateCoverage,
    Obligation,
    RequirementMap,
    Review,
    TestRecommendation,
    UnobtainedRecommendation,
)

_EMPTY = "  (none)"
_NO_CODE = "(no corresponding change)"
_NO_TESTS = "(no mapped test)"


def _not_required(obligation: Obligation) -> str:
    """The "this axis was not owed" line, with the reason that justifies it.

    Deliberately not phrased as an absence. "(no mapped test)" under such an
    obligation would read as a gap (#153), and "not applicable" on its own is an
    assertion a reader cannot argue with — which is what makes an incorrect one
    invisible. The reason is the argument (#266), so a reader who believes a test
    IS owed here has a specific sentence to disagree with.
    """
    reason = obligation.required_evidence_reason.strip()
    return f"not required — {reason}" if reason else "not required"


def _examined_claim(scope_examined: list[str]) -> str:
    """The non-violation claim, stated over the scope it actually covered.

    Names the number of changes and files compared rather than asserting
    "everything": the change set is itself filtered, so "everything" would claim
    more than was inspected. With nothing examined there is no claim to make —
    an empty diff cannot evidence non-violation, and saying so is the honest
    answer rather than a vacuous pass.
    """
    if not scope_examined:
        return "(no changes were examined — non-violation is not established)"
    files = {ref.split("#", 1)[0] for ref in scope_examined}
    changes = "change" if len(scope_examined) == 1 else "changes"
    file_word = "file" if len(files) == 1 else "files"
    return (
        f"examined {len(scope_examined)} {changes} across {len(files)} {file_word}; "
        "none breaches this boundary"
    )


def render_report(review: Review) -> str:
    lines: list[str] = [f"Task completion: {_completion_status(review)}", ""]

    completion = review.completion
    if completion is not None and completion.rationale:
        lines.append(completion.rationale)
        lines.append("")

    lines.append("Obligations:")
    if review.obligation_map:
        by_obligation = {rec.obligation_id: rec for rec in review.recommendations}
        unobtained = {rec.obligation_id: rec for rec in review.unobtained_recommendations}
        for index, obligation in enumerate(review.obligation_map, start=1):
            lines.append("")
            lines.extend(
                _obligation_block(
                    index,
                    obligation,
                    review.requirement_map,
                    by_obligation.get(obligation.id),
                    unobtained.get(obligation.id),
                )
            )
    else:
        lines.append(_EMPTY)
    lines.append("")

    if review.requirement_map is not None:
        lines.extend(
            _mandate_coverage_block(
                review.requirement_map,
                completion.mandate_coverage if completion is not None else None,
            )
        )
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

    if review.defect_sets:
        lines.extend(_defect_block(review.defect_sets))
        lines.append("")

    if review.pair_verdicts or review.unjudged_pairs:
        lines.extend(_pair_block(review))
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

    # No recommendations block. Each one renders inside the obligation it
    # explains (`_obligation_block`), per §16's rule that a criterion's axes sit
    # together rather than in separate lists joined by eye.

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


def _pair_block(review: Review) -> list[str]:
    """What the pair verdicts imply, beside what the review actually says (#314).

    **Advisory, and the comparison is the point.** Nothing here moved a rating;
    the block exists so a discrepancy between the two is visible while the
    baseline is still stable. #316 flips the review onto the derived column, and
    a difference it cannot explain now is a difference to explain before then.

    Every derived class is rendered with its denominator and never alone, per
    DR-312's resolved question 3: "strongly supported" over an enumeration of one
    claims more than it has, and the number lets a reader weigh that themselves.
    """
    derived = derive_support(review.defect_sets, review.pair_verdicts, review.unjudged_pairs)
    by_id = {obligation.id: obligation for obligation in review.obligation_map}

    heading = (
        "Support implied by test-to-defect pairs "
        "(advisory — the review's own ratings are unchanged):"
    )
    lines = [heading]
    disagreeing = []
    for entry in derived:
        obligation = by_id.get(entry.obligation_id)
        current = obligation.evidence_class if obligation else None
        pending = f", {entry.unjudged} pair(s) unjudged" if entry.unjudged else ""
        lines.append("")
        lines.append(f"  {entry.obligation_id}")
        lines.append(
            f"    implied by pairs: {entry.evidence_class} — kills "
            f"{entry.killed} of {entry.total} enumerated defects "
            f"(static prediction{pending})"
        )
        lines.append(f"    this review says: {current or 'not rated'}")
        if current is not None and current != entry.evidence_class:
            disagreeing.append(entry.obligation_id)

    lines.append("")
    if disagreeing:
        lines.append(f"  Criteria where the two disagree: {', '.join(disagreeing)}")
    else:
        lines.append("  Criteria where the two disagree: (none)")

    # Both causes are shown, and shown apart. A pair the filter proved unreachable
    # and one the judge was asked about and never answered are different failures
    # with opposite remedies, and DR-164's silent id filter is the precedent for
    # why neither may be left invisible.
    if review.unjudged_pairs:
        lines.append("")
        lines.append("  Pairs left unjudged:")
        for entry in review.unjudged_pairs:
            lines.append(f"    [{entry.cause.value}] {entry.defect_id} x {entry.test_id}")
            lines.append(f"      {entry.reason}")
    return lines


def _defect_block(defect_sets: list[DefectSet]) -> list[str]:
    """The enumerated ways the change could fail each criterion (#313).

    **Advisory.** Labelled so in the heading, because nothing here moved the
    verdict or any criterion's rating and a reader would otherwise reasonably
    assume it had. It is deliberately placed after the criteria and the mandate
    coverage: it is context for those judgements, not one of them.

    A set that was reused rather than produced again says so, per the mandate.
    A reader has to be able to tell which parts of a review are fresh — a
    carried set is a statement about an earlier head, and presenting it as
    current would overstate what this run examined.
    """
    lines = ["Ways the change could fail a criterion (advisory — no verdict depends on these):"]
    for entry in defect_sets:
        reused = "  (reused from an earlier run)" if entry.carried_from else ""
        lines.append("")
        lines.append(f"  {entry.obligation_id}{reused}")
        if not entry.defects:
            # An empty set is a result, not a blank. Rendering the reason is what
            # makes it one a reader can disagree with.
            lines.append(f"    none enumerated: {entry.reason}")
            continue
        for defect in entry.defects:
            lines.append(f"    [{defect.type.value}] {defect.id}")
            lines.append(f"      {defect.description}")
            for ref in defect.code_refs:
                lines.append(f"      {ref}")
    return lines


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


def _coverage_verdict_line(coverage: MandateCoverage | None) -> list[str]:
    """What the coverage figure meant for the verdict (#214).

    The count above says how many requirements yielded obligations; it does not
    say whether that was enough to judge the mandate, and those are different
    questions once a decline is trusted. Stated here rather than left for the
    reader to infer, because the whole defect was a review being confident about
    a shrinking fraction of the mandate without saying the fraction shrank.
    """
    if coverage is None:
        return []
    lines = []
    if coverage.declined_requirements:
        lines.append(
            f"  {len(coverage.declined_requirements)} deliberately declined, taken at "
            "face value and not counted against coverage"
        )
    if coverage.unjudged_requirements:
        lines.append(
            f"  {len(coverage.unjudged_requirements)} could not be judged "
            f"({', '.join(coverage.unjudged_requirements)}) — this bounds the verdict"
        )
    return lines


def _mandate_coverage_block(
    requirement_map: RequirementMap, coverage: MandateCoverage | None = None
) -> list[str]:
    """Which requirements of the mandate produced nothing (M1.2.r1, DR-202).

    This section exists because its absence was the defect. A requirement that
    yielded no obligation used simply not to appear anywhere in the review, so a
    breakdown covering 20 of 29 requirements read exactly like one covering all
    29 — the reader was told nothing was missing because nothing was there to
    say it. Rendering the empty case is the whole point: a requirement that
    produced nothing is a claim about the REVIEW, not about the code, and it
    belongs in front of the person who can act on it.

    Every entry here is now a decision the decomposer *made* — declined with a
    reason, or turned into an open question. A requirement it simply failed to
    address cannot appear, because that response no longer parses (M1.2.r2).
    """
    total = len(requirement_map.requirements)
    if not total:
        return []

    unyielding = requirement_map.unyielding()
    lines = [
        f"Mandate coverage: {total - len(unyielding)} of {total} requirements yielded obligations"
    ]
    lines.extend(_coverage_verdict_line(coverage))
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
    lines.extend(_unread_block(requirement_map))
    return lines


def _unread_block(requirement_map: RequirementMap) -> list[str]:
    """Task-file text no requirement was derived from.

    Reported alongside mandate coverage because it is the same question one step
    earlier — a review can only speak to text that reached the decomposer, and
    text the parse dropped is a limit on the review, not a property of the code.
    """
    if not requirement_map.unread_source:
        return []
    lines = [
        "",
        (
            f"  Not read as any requirement: {len(requirement_map.unread_source)} block(s)"
            " — outside every recognised section, so no obligation could derive from them."
        ),
    ]
    for span in requirement_map.unread_source:
        excerpt = " ".join(span.text.split())
        if len(excerpt) > 100:
            excerpt = excerpt[:97] + "..."
        lines.append(f"       - {excerpt}")
    return lines


def _obligation_block(
    index: int,
    obligation: Obligation,
    requirement_map: RequirementMap | None = None,
    recommendation: TestRecommendation | None = None,
    unobtained: UnobtainedRecommendation | None = None,
) -> list[str]:
    """One numbered obligation with both evidence axes nested beneath it, and
    the test recommendation that explains a weak one.

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

    if obligation.required_evidence.requires_code:
        coverage = (obligation.coverage_status or "unclassified").replace("_", " ")
        lines.append(f"       code evidence: {coverage}")
        if obligation.coverage_refs:
            for ref in obligation.coverage_refs:
                item += 1
                lines.append(f"         {index}.{item}  {ref}")
        elif obligation.satisfied_by_absence:
            # #153: one completeness claim over the examined set, never a listing.
            # Printing every hunk here would read as "these changes support the
            # obligation" when the claim is "these were checked and none breaches
            # it" — and under a boundary obligation that is the whole diff, which
            # is noise on top of being wrong. The count is what makes the claim
            # auditable: it says how much "none of them" ranged over.
            lines.append(f"         {_examined_claim(obligation.scope_examined)}")
        else:
            lines.append(f"         {_NO_CODE}")
    else:
        lines.append(f"       code evidence: {_not_required(obligation)}")

    # An obligation that requires no test evidence has no test axis to render.
    # Printing "test evidence: unsupported / no tests" under it is not merely
    # noise — it reads identically to a requirement whose tests are missing,
    # which is the distinction this line exists to preserve (#153). State
    # instead that none is required, and why (#266): the reason is what a reader
    # who thinks a test IS owed here can argue with, and without it the line is
    # an assertion rather than a claim.
    if not obligation.required_evidence.requires_tests:
        lines.append(f"       test evidence: {_not_required(obligation)}")
    else:
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

    # The recommendation belongs to the axis it explains. It used to render in a
    # separate block at the foot of the report, identified only by a
    # `--criterion` slug that appeared nowhere in this block — the "separate
    # lists the reader must join by eye" §16 exists to prevent, and a real cost:
    # CLAUDE.md requires reading the recommendation BEFORE judging a weak
    # obligation, which the old layout made a manual cross-reference.
    if recommendation is not None:
        lines.append(f"         recommended test: {recommendation.criterion}")
        lines.append(f"           inputs:  {recommendation.required_inputs}")
        lines.append(f"           detects: {recommendation.plausible_defect}")
        # §9.5's single-iteration goal depends on the agent KNOWING the full
        # prescription exists, at the moment it decides to act on this criterion.
        lines.append(
            "           full detail: acceptance recommendation "
            f"--criterion {recommendation.obligation_id}"
        )

    # A criterion the stage was asked about and returned nothing for (#275).
    # It renders where its prescription would have been, because that is where
    # a reader looks for one, and it says the prescription is MISSING rather
    # than absent — distinct from the `test evidence: not required (reason)`
    # line above, which is the tool's own settled decision that no test is owed.
    # One is "we decided you need nothing here"; this is "we asked and did not
    # find out".
    if unobtained is not None:
        lines.append("         recommended test: NOT OBTAINED — no prescription was produced")
        lines.append(f"           why: {unobtained.reason}")

    return lines


def _completion_status(review: Review) -> str:
    """The M7.2 verdict, rendered as the §16 headline. A review with no
    computed verdict is honestly INDETERMINATE (§9.3) rather than assumed
    good — uncertainty is a first-class result."""
    if review.completion is None:
        return "INDETERMINATE"
    return review.completion.verdict.value.replace("_", "-").upper()

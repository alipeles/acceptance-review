"""Mandate coverage bounds the completion verdict (#214).

The defect: `derive_verdict` never received the requirement map, so a
requirement that yielded no obligation reached none of its inputs and mandate
coverage could not move the verdict in either direction. A decomposer that
dropped requirements therefore scored *better*, because the requirements it
dropped could not generate gaps.

Each test here names the Acceptance item it demonstrates.
"""

from __future__ import annotations

import pytest

from acceptance.coverage.open_questions import (
    OpenQuestionResolution,
    derive_obligations,
    derived_obligation_id,
)
from acceptance.coverage.prompt import DiffRef
from acceptance.review_state import (
    CompletionVerdict,
    Disposition,
    Obligation,
    ObligationType,
    OpenQuestion,
    RequirementDisposition,
    RequirementMap,
    RequirementRef,
    RequirementSection,
)
from acceptance.source_ref import TextSpan
from acceptance.verdict import assess_mandate_coverage, derive_verdict


def _span(text: str = "some requirement text") -> TextSpan:
    return TextSpan(start=0, end=len(text), text=text)


def _requirement(requirement_id: str, section: RequirementSection, ordinal: int) -> RequirementRef:
    return RequirementRef(id=requirement_id, section=section, ordinal=ordinal, span=_span())


def _obligation(
    obligation_id: str, evidence_class: str | None = "strongly_supported"
) -> Obligation:
    return Obligation(
        id=obligation_id,
        description=f"description for {obligation_id}",
        type=ObligationType.FUNCTIONAL,
        importance="normal",
        explicit=True,
        observable_behavior=f"behavior for {obligation_id}",
        evidence_class=evidence_class,
        coverage_status="addressed",
    )


def _map(*dispositions: RequirementDisposition, unread: int = 0) -> RequirementMap:
    return RequirementMap(
        requirements=[
            _requirement(entry.requirement_id, RequirementSection.CONSTRAINT, index)
            for index, entry in enumerate(dispositions, start=1)
        ],
        dispositions=list(dispositions),
        unread_source=[_span(f"unread block {n}") for n in range(unread)],
    )


def _yielded(requirement_id: str, *obligation_ids: str) -> RequirementDisposition:
    return RequirementDisposition(
        requirement_id=requirement_id,
        disposition=Disposition.YIELDED,
        obligation_ids=list(obligation_ids),
    )


def _declined(
    requirement_id: str, reason: str = "A bare section marker."
) -> RequirementDisposition:
    return RequirementDisposition(
        requirement_id=requirement_id,
        disposition=Disposition.NO_OBLIGATION,
        reason=reason,
    )


def _questioned(requirement_id: str, *question_ids: str) -> RequirementDisposition:
    return RequirementDisposition(
        requirement_id=requirement_id,
        disposition=Disposition.OPEN_QUESTION,
        open_question_ids=list(question_ids),
    )


def _resolution(question_id: str, behavior: str, *, resolved: bool = True, cited: bool = True):
    return OpenQuestionResolution(
        question_id=question_id,
        resolved=resolved,
        rationale="what the diff shows",
        diff_refs=[DiffRef(file="pkg.py", hunk_header="0")] if cited else [],
        implemented_behavior=behavior,
    )


def _question(question_id: str, importance: str = "normal") -> OpenQuestion:
    return OpenQuestion(
        id=question_id,
        question=f"question {question_id}?",
        importance=importance,
        source_spans=[_span("the ambiguous text")],
    )


# --- Acceptance: a declined requirement does not count against coverage -------


def test_a_declined_requirement_does_not_count_against_coverage():
    """A decline is a decision the decomposer made and stated a reason for, so
    it is taken at face value. This is what keeps a bare section marker from
    being penalised — because of WHAT IT IS, not because of how short it is."""
    requirement_map = _map(_yielded("constraint-01", "o1"), _declined("completion-01"))

    coverage = assess_mandate_coverage(requirement_map, [_obligation("o1")])

    assert coverage.declined_requirements == ["completion-01"]
    assert coverage.unjudged_requirements == []
    assert coverage.complete is True


def test_a_decline_is_not_re_judged_even_when_the_text_reads_like_a_requirement():
    """The discriminating version of the test above.

    A decline of `- Implementation` is credited by any implementation, including
    one that re-reads the requirement and forms its own view — a bare marker
    looks declinable either way. So that case cannot tell a trusting
    implementation from a re-judging one. This one can: the requirement text is
    a plain, checkable-sounding statement, and only an implementation that takes
    the recorded disposition at face value credits it.
    """
    convincing = RequirementDisposition(
        requirement_id="constraint-02",
        disposition=Disposition.NO_OBLIGATION,
        reason="Restates constraint-01; adds no separate expectation.",
    )
    requirement_map = RequirementMap(
        requirements=[
            _requirement("constraint-01", RequirementSection.CONSTRAINT, 1),
            RequirementRef(
                id="constraint-02",
                section=RequirementSection.CONSTRAINT,
                ordinal=2,
                span=_span("Amounts are rounded to two decimal places."),
            ),
        ],
        dispositions=[_yielded("constraint-01", "o1"), convincing],
    )

    coverage = assess_mandate_coverage(requirement_map, [_obligation("o1")])

    assert coverage.declined_requirements == ["constraint-02"]
    assert coverage.unjudged_requirements == []
    assert coverage.complete is True


def test_a_review_whose_only_unyielding_requirement_is_declined_stays_positive():
    """The whole point of trusting the decline: it must not bound the verdict."""
    requirement_map = _map(_yielded("constraint-01", "o1"), _declined("completion-01"))

    result = derive_verdict([_obligation("o1")], [], [], requirement_map)

    assert result.verdict is CompletionVerdict.NO_MATERIAL_GAPS
    assert result.mandate_coverage.complete is True


# --- Acceptance: a resolved question yields a derived obligation --------------


def test_a_resolved_question_yields_an_obligation_stating_the_chosen_behavior():
    derived = derive_obligations(
        [_question("q-1")], [_resolution("q-1", "Retries use exponential backoff.")]
    )

    assert len(derived) == 1
    assert derived[0].description == "Retries use exponential backoff."
    assert derived[0].observable_behavior == "Retries use exponential backoff."
    # Inferred from the change, not stated in the mandate -- which is exactly
    # what `explicit` means.
    assert derived[0].explicit is False
    assert derived[0].type is ObligationType.FUNCTIONAL


def test_a_derived_obligation_is_addressed_and_cites_what_resolved_it():
    """Acceptance: reported as implemented, citing the change locations, never
    as a coverage gap. Resolution had to cite the hunks that answer the
    question, so the code is already located."""
    derived = derive_obligations(
        [_question("q-1")], [_resolution("q-1", "Retries use exponential backoff.")]
    )

    assert derived[0].coverage_status == "addressed"
    assert derived[0].coverage_refs == ["pkg.py#0"]
    # Links back to the ambiguous task text, so typed-and-linked still holds.
    assert derived[0].source_spans


def test_an_unresolved_question_yields_no_obligation():
    derived = derive_obligations(
        [_question("q-1")], [_resolution("q-1", "", resolved=False, cited=False)]
    )

    assert derived == []


def test_a_resolution_without_a_citation_yields_no_obligation():
    """A resolution the model asserted but did not evidence is a claim, not a
    finding. Building a test demand on it would manufacture an obligation the
    review could not substantiate."""
    derived = derive_obligations(
        [_question("q-1")], [_resolution("q-1", "Retries use backoff.", cited=False)]
    )

    assert derived == []


def test_a_derived_obligation_id_is_stable_across_runs():
    """Acceptance: identical across two runs over byte-identical input. Computed
    from the question id in code rather than minted per response (#231), which
    #180's carry-forward design also depends on."""
    first = derive_obligations([_question("q-1")], [_resolution("q-1", "Retries use backoff.")])
    second = derive_obligations([_question("q-1")], [_resolution("q-1", "Retries use backoff.")])

    assert first[0].id == second[0].id == derived_obligation_id("q-1")


def test_an_untested_derived_obligation_prevents_a_positive_verdict():
    """Acceptance: an implementation choice that settled an ambiguity cannot
    ship untested. It reaches the verdict through the ordinary weak-evidence
    path -- no new rule in the rollup."""
    derived = derive_obligations(
        [_question("q-1")], [_resolution("q-1", "Retries use exponential backoff.")]
    )
    derived[0] = derived[0].model_copy(update={"evidence_class": "unsupported"})
    requirement_map = _map(_yielded("constraint-01", "o1"), _questioned("constraint-02", "q-1"))

    result = derive_verdict(
        [_obligation("o1"), *derived],
        [],
        [_question("q-1").model_copy(update={"resolved": True})],
        requirement_map,
    )

    assert result.verdict is CompletionVerdict.INCOMPLETE
    assert derived[0].id in result.rationale


def test_a_requirement_whose_question_the_diff_resolved_counts_as_judged():
    requirement_map = _map(_yielded("constraint-01", "o1"), _questioned("constraint-02", "q-1"))
    derived = derive_obligations(
        [_question("q-1")], [_resolution("q-1", "Retries use exponential backoff.")]
    )

    coverage = assess_mandate_coverage(requirement_map, [_obligation("o1"), *derived])

    assert coverage.unjudged_requirements == []
    assert coverage.complete is True


def test_a_requirement_whose_question_produced_nothing_is_unjudged():
    requirement_map = _map(_yielded("constraint-01", "o1"), _questioned("constraint-02", "q-1"))

    coverage = assess_mandate_coverage(requirement_map, [_obligation("o1")])

    assert coverage.unjudged_requirements == ["constraint-02"]
    assert coverage.complete is False
    assert coverage.judged_requirements == 1


# --- Acceptance: unread source bounds the verdict -----------------------------


def test_task_text_that_yielded_no_requirement_prevents_a_positive_verdict():
    """What the struck `undisposed` bullet meant: text the parse never turned
    into a requirement is unambiguous loss, not a judgement call."""
    requirement_map = _map(_yielded("constraint-01", "o1"), unread=2)

    result = derive_verdict([_obligation("o1")], [], [], requirement_map)

    assert result.verdict is CompletionVerdict.UNABLE_TO_DETERMINE
    assert "no requirement at all" in result.rationale
    assert result.mandate_coverage.unread_source_blocks == 2


# --- Acceptance: coverage is recorded, and only ever bounds --------------------


def test_identical_evidence_with_different_coverage_differs_in_the_result():
    """Acceptance item 1. The figure is part of the result, so two reviews with
    identical obligation-level evidence are never the same result -- and here
    they also differ in the enum, because one would otherwise be positive."""
    obligations = [_obligation("o1")]
    covered = _map(_yielded("constraint-01", "o1"))
    short = _map(_yielded("constraint-01", "o1"), _questioned("constraint-02", "q-1"))

    full = derive_verdict(obligations, [], [], covered)
    partial = derive_verdict(obligations, [], [], short)

    assert full != partial
    assert full.verdict is CompletionVerdict.NO_MATERIAL_GAPS
    assert partial.verdict is CompletionVerdict.UNABLE_TO_DETERMINE


def test_coverage_is_recorded_even_when_complete():
    result = derive_verdict([_obligation("o1")], [], [], _map(_yielded("constraint-01", "o1")))

    assert result.mandate_coverage is not None
    assert result.mandate_coverage.total_requirements == 1
    assert result.mandate_coverage.judged_requirements == 1


def test_a_shortfall_never_improves_an_already_negative_verdict():
    """Acceptance: reduced coverage only ever bounds, never raises. A dropping
    decomposer must not be able to launder a known gap into a softer result."""
    weak = [_obligation("o1", evidence_class="unsupported")]
    short = _map(_yielded("constraint-01", "o1"), _questioned("constraint-02", "q-1"))

    result = derive_verdict(weak, [], [], short)

    assert result.verdict is CompletionVerdict.INCOMPLETE
    assert any("Mandate coverage" in limitation for limitation in result.limitations)


@pytest.mark.parametrize(
    "evidence_class, expected",
    [
        ("strongly_supported", CompletionVerdict.NO_MATERIAL_GAPS),
        ("unsupported", CompletionVerdict.INCOMPLETE),
    ],
)
def test_dropping_a_requirement_never_produces_a_better_verdict(evidence_class, expected):
    """The defect stated directly: a decomposer that drops requirements must
    score worse, never better. Dropping `constraint-02` removes nothing that
    could generate a gap, so without the bound the verdict would be unchanged
    or improved; with it, the dropped requirement is visible."""
    obligations = [_obligation("o1", evidence_class=evidence_class)]
    kept = _map(_yielded("constraint-01", "o1"), _yielded("constraint-02", "o2"))
    kept_obligations = [*obligations, _obligation("o2", evidence_class=evidence_class)]
    dropped = _map(_yielded("constraint-01", "o1"), _questioned("constraint-02", "q-1"))

    with_all = derive_verdict(kept_obligations, [], [], kept)
    with_dropped = derive_verdict(obligations, [], [], dropped)

    assert with_all.verdict is expected
    assert with_dropped.verdict is not CompletionVerdict.NO_MATERIAL_GAPS
    assert (
        with_dropped.mandate_coverage.judged_requirements
        < with_all.mandate_coverage.judged_requirements
    )


def test_the_report_states_the_same_coverage_the_result_carries():
    """Acceptance: recorded on the result AND stated in the report.

    Recording it without rendering it would leave the figure true and invisible,
    which is the defect one level down: a reader who cannot see the shortfall
    cannot act on it. Asserted against the numbers on the result rather than
    against fixed text, so the two cannot drift apart.
    """
    from acceptance.report import render_report
    from acceptance.review_state import Review

    requirement_map = _map(
        _yielded("constraint-01", "o1"),
        _declined("completion-01"),
        _questioned("constraint-02", "q-1"),
    )
    completion = derive_verdict([_obligation("o1")], [], [], requirement_map)
    review = Review(
        mode="local",
        reviewed_revision="deadbeef",
        obligation_map=[_obligation("o1")],
        requirement_map=requirement_map,
        completion=completion,
    )

    rendered = render_report(review)

    coverage = completion.mandate_coverage
    assert f"{len(coverage.declined_requirements)} deliberately declined" in rendered
    assert f"{len(coverage.unjudged_requirements)} could not be judged" in rendered
    # The requirement that could not be judged is named, not just counted.
    assert "constraint-02" in rendered
    assert "this bounds the verdict" in rendered


def test_no_requirement_map_leaves_the_verdict_untouched():
    """Back-compat: callers that pass no map get exactly the old behaviour, so
    the bound cannot silently change a review that never had coverage data."""
    result = derive_verdict([_obligation("o1")], [], [])

    assert result.verdict is CompletionVerdict.NO_MATERIAL_GAPS
    assert result.mandate_coverage is None

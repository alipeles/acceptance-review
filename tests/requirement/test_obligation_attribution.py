"""#244: an obligation is filed under the requirement its quotation comes from.

`_user_prompt` shows every call the whole registry, marks each requirement
`ANSWER FOR THIS` or `context only`, and asks the model not to derive obligations
for the ones another call owns. Nothing enforced that. The quotation was resolved
against the whole task file, so an obligation filed under one requirement while
quoting another's text produced a valid span and was accepted — misattribution
was undetectable by construction.

Observed in #180's Gate 1: a one-sentence Task requirement yielded seven
obligations, three of them the content of other requirements, which the linking
stage then reported as unreconcilable.

Responses are injected through the harness, per the replay-first invariant — no
live calls.
"""

from __future__ import annotations

from acceptance.requirement.obligations import decompose
from acceptance.requirement.task_file import parse_task_file
from acceptance.supplied_ids import UnusableAnswerLog
from tests.support import client_returning

# Two requirements whose wording does NOT overlap, so a quotation identifies its
# requirement unambiguously and a re-filing cannot be a coincidence of phrasing.
TASK = """# Task
Render each invoice line.

## Constraints
- Format money as USD with two decimals.
- Keep the existing CSV export unchanged.

## Completion expectations
- A test covers the rounding boundary at half a cent.
"""


def _obligation(oid: str, description: str, quote: str) -> dict:
    return {
        "id": oid,
        "description": description,
        "type": "functional",
        "importance": "normal",
        "explicit": True,
        "observable_behavior": "...",
        "source_quote": quote,
        # Requiring both is the safe default the stage itself applies (#266);
        # a fixture silent about which evidence is owed is not narrowing.
        "required_evidence": "code_and_tests",
        "required_evidence_reason": "",
    }


def _yielded(rid: str, *obligation_ids: str) -> dict:
    return {
        "requirement_id": rid,
        "disposition": "yielded",
        "obligation_id": obligation_ids[0],
        "more_obligation_ids": list(obligation_ids[1:]),
    }


def _declined(rid: str) -> dict:
    return {
        "requirement_id": rid,
        "disposition": "no_obligation",
        "reason": "Not applicable.",
    }


def _decompose(obligations: list[dict], dispositions: list[dict], log=None):
    response = {
        "obligations": obligations,
        "open_questions": [],
        "requirement_dispositions": dispositions,
    }
    return decompose(parse_task_file(TASK), client_returning(response), log)


def test_an_obligation_quoting_its_own_requirement_keeps_it():
    """The unchanged path, and the one that must not regress: correct
    attribution is the overwhelming majority of obligations."""
    result = _decompose(
        [
            _obligation("render", "Render each invoice line.", "Render each invoice line."),
            _obligation("usd", "Format money as USD.", "Format money as USD"),
            _obligation("csv", "Preserve the CSV export.", "existing CSV export"),
            _obligation("rounding", "A test covers the rounding boundary.", "rounding boundary"),
        ],
        [
            _yielded("task-01", "render"),
            _yielded("constraint-01", "usd"),
            _yielded("constraint-02", "csv"),
            _yielded("completion-01", "rounding"),
        ],
    )

    assert result.requirement_map.requirements_for_obligation("render") == ["task-01"]
    assert result.requirement_map.requirements_for_obligation("usd") == ["constraint-01"]
    assert result.requirement_map.requirements_for_obligation("csv") == ["constraint-02"]
    assert result.requirement_map.requirements_for_obligation("rounding") == ["completion-01"]


def test_an_obligation_quoting_another_requirement_is_refiled_under_it():
    """The #180 shape: `task-01` carries an obligation whose quotation is
    `constraint-01`'s text. It belongs to `constraint-01`."""
    result = _decompose(
        [
            _obligation("render", "Render each invoice line.", "Render each invoice line."),
            _obligation("strayed", "Format money as USD.", "Format money as USD"),
            _obligation("usd", "Money is formatted as USD.", "with two decimals"),
        ],
        [
            # Two obligations under task-01, the second quoting constraint-01.
            _yielded("task-01", "render", "strayed"),
            _yielded("constraint-01", "usd"),
            _declined("constraint-02"),
            _declined("completion-01"),
        ],
    )

    assert result.requirement_map.requirements_for_obligation("strayed") == ["constraint-01"]
    assert result.requirement_map.requirements_for_obligation("render") == ["task-01"]
    # The requirement it strayed from keeps only what genuinely quoted it.
    assert result.requirement_map.disposition_for("task-01").obligation_ids == ["render"]
    # And the one it landed on now carries both, which the linking stage can
    # merge — a two-on-one case, not the cross-requirement contradiction it
    # could not reconcile.
    assert result.requirement_map.disposition_for("constraint-01").obligation_ids == [
        "strayed",
        "usd",
    ]


def test_refiling_leaves_the_obligations_own_content_alone():
    """Re-filing changes which requirement claims an obligation and nothing
    else. A fix that rewrote the obligation would be inventing content."""
    result = _decompose(
        [
            _obligation("render", "Render each invoice line.", "Render each invoice line."),
            _obligation("strayed", "Format money as USD.", "Format money as USD"),
            _obligation("usd", "Money is formatted as USD.", "with two decimals"),
        ],
        [
            _yielded("task-01", "render", "strayed"),
            _yielded("constraint-01", "usd"),
            _declined("constraint-02"),
            _declined("completion-01"),
        ],
    )

    strayed = next(o for o in result.obligations if o.id == "strayed")
    assert strayed.description == "Format money as USD."
    assert strayed.type == "functional"
    assert strayed.observable_behavior == "..."
    assert strayed.explicit is True
    # The span now points inside the requirement it was re-filed under.
    assert [span.text for span in strayed.source_spans] == ["Format money as USD"]


def test_a_quotation_matching_no_requirement_is_recorded():
    """A quotation that lands in no requirement cannot corroborate the
    attribution. The obligation is kept — losing a requirement is the worse
    failure — but the discrepancy is recorded rather than passed over."""
    log = UnusableAnswerLog()
    result = _decompose(
        [
            _obligation("render", "Render each invoice line.", "Render each invoice line."),
            _obligation("invented", "Charge sales tax.", "## Constraints"),
        ],
        [
            _yielded("task-01", "render", "invented"),
            _declined("constraint-01"),
            _declined("constraint-02"),
            _declined("completion-01"),
        ],
        log,
    )

    assert [answer.returned_id for answer in log.answers] == ["invented"]
    assert log.answers[0].field == "source_quote"
    assert "not inside it" in (log.answers[0].reason or "")
    # Kept, not dropped.
    assert "invented" in [o.id for o in result.obligations]


def test_a_refiling_is_recorded_even_though_it_was_acted_on():
    """A re-filing is a disagreement between what the response said and what its
    own quotation shows. Acting on it silently would leave the decomposer's
    accuracy unmeasurable — the reason #211 exists."""
    log = UnusableAnswerLog()
    _decompose(
        [
            _obligation("render", "Render each invoice line.", "Render each invoice line."),
            _obligation("strayed", "Format money as USD.", "Format money as USD"),
            _obligation("usd", "Money is formatted as USD.", "with two decimals"),
        ],
        [
            _yielded("task-01", "render", "strayed"),
            _yielded("constraint-01", "usd"),
            _declined("constraint-02"),
            _declined("completion-01"),
        ],
        log,
    )

    assert [answer.returned_id for answer in log.answers] == ["strayed"]
    assert "re-filed" in (log.answers[0].reason or "")


def test_a_requirement_never_loses_its_last_obligation_to_refiling():
    """A completion expectation quoting the constraint it demands a test for is
    the DR-204 shape and is common. Moving its only obligation would leave a
    `yielded` requirement carrying none, which raises out of `_requirement_map`
    — turning a quoting slip into a failed review. The disposition is the
    stronger evidence where the two disagree.
    """
    log = UnusableAnswerLog()
    result = _decompose(
        [
            _obligation("render", "Render each invoice line.", "Render each invoice line."),
            _obligation("usd", "Format money as USD.", "Format money as USD"),
            # completion-01's only obligation, quoting constraint-01's text.
            _obligation("covered", "A test covers rounding.", "two decimals"),
        ],
        [
            _yielded("task-01", "render"),
            _yielded("constraint-01", "usd"),
            _declined("constraint-02"),
            _yielded("completion-01", "covered"),
        ],
        log,
    )

    assert result.requirement_map.requirements_for_obligation("covered") == ["completion-01"]
    assert result.requirement_map.disposition_for("completion-01").obligation_ids == ["covered"]
    # Not acted on, but not silent either.
    assert [answer.returned_id for answer in log.answers] == ["covered"]


def test_an_obligation_is_not_refiled_onto_a_requirement_that_declined():
    """Filing under a requirement disposed `no_obligation` would contradict that
    decline, and `_requirement_map` never reads the obligation ids of a declined
    requirement — so the obligation would end up linked to nothing."""
    result = _decompose(
        [
            _obligation("render", "Render each invoice line.", "Render each invoice line."),
            _obligation("strayed", "Format money as USD.", "Format money as USD"),
        ],
        [
            _yielded("task-01", "render", "strayed"),
            _declined("constraint-01"),
            _declined("constraint-02"),
            _declined("completion-01"),
        ],
    )

    assert result.requirement_map.requirements_for_obligation("strayed") == ["task-01"]
    assert "strayed" in [o.id for o in result.obligations]


def test_refiling_takes_the_satisfied_by_absence_of_the_requirement_it_lands_in():
    """Whether an obligation is satisfied by work NOT done is decided by the
    section it sits in (#153). An obligation re-filed into a scope exclusion is
    satisfied by an absence, exactly as one derived there directly would be —
    the section must follow the re-filing, or the field records the section the
    obligation only appeared to come from.

    Asserts the absence flag, not which evidence is required (#266). The two
    were one field until a scope exclusion naming a BEHAVIOUR turned out to want
    a regression test; the heading still settles the absence beyond argument,
    and that is now all it settles."""
    task = """# Task
Render each invoice line.

## Constraints
- Format money as USD with two decimals.

## Scope exclusions
- Changing the PDF renderer.
"""
    response = {
        "obligations": [
            _obligation("render", "Render each invoice line.", "Render each invoice line."),
            _obligation("pdf", "Preserve the PDF renderer.", "Changing the PDF renderer"),
            _obligation("excluded", "Preserve the PDF renderer.", "PDF renderer"),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _yielded("task-01", "render", "excluded"),
            {"requirement_id": "constraint-01", "disposition": "no_obligation", "reason": "n/a"},
            _yielded("exclusion-01", "pdf"),
        ],
    }
    result = decompose(parse_task_file(task), client_returning(response))

    assert result.requirement_map.requirements_for_obligation("excluded") == ["exclusion-01"]
    refiled = next(o for o in result.obligations if o.id == "excluded")
    assert refiled.satisfied_by_absence
    # The control: an obligation that stayed in the Task section does not pick
    # the flag up, so this is not passing because everything carries it.
    assert not next(o for o in result.obligations if o.id == "render").satisfied_by_absence


def test_a_quotation_matching_two_requirements_stays_with_the_one_it_was_attributed_to():
    """The case that makes searching the attributed requirement FIRST
    load-bearing rather than an optimisation.

    Both requirements contain the quoted sentence, so containment alone cannot
    decide between them. An implementation that scans the registry in order and
    re-files on the first containing requirement would move this obligation to
    `task-01`, which comes first — silently, and on a quotation that was never
    wrong.
    """
    task = """# Task
The export writes a header row naming every column.

## Constraints
- The export writes a header row naming every column.
"""
    response = {
        "obligations": [
            _obligation("prose", "Write a header row.", "writes a header row"),
            # Attributed to the SECOND requirement, quoting text both contain.
            _obligation("bullet", "Write a header row.", "writes a header row"),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _yielded("task-01", "prose"),
            _yielded("constraint-01", "bullet"),
        ],
    }
    log = UnusableAnswerLog()
    result = decompose(parse_task_file(task), client_returning(response), log)

    assert result.requirement_map.requirements_for_obligation("bullet") == ["constraint-01"]
    assert result.requirement_map.requirements_for_obligation("prose") == ["task-01"]
    assert log.answers == []
    # Each span points inside its own requirement, not at the first match in the file.
    bullet = next(o for o in result.obligations if o.id == "bullet")
    prose = next(o for o in result.obligations if o.id == "prose")
    assert bullet.source_spans[0].start > prose.source_spans[0].start


def test_a_quotation_is_found_across_a_line_break():
    """Task prose is hard-wrapped and bullets usually are not, so one sentence
    appears wrapped in one requirement and flat in another. Matching on the exact
    substring finds it only in the unwrapped one and re-files the obligation on
    the strength of a line break.

    Caught on `tests/prompts/test_linking_prompt.py`'s corpus, where it moved the
    Task prose's obligation onto the constraint restating it — deleting the
    cross-section duplicate that corpus exists to exercise.
    """
    task = """# Task
Export invoices to a CSV file. The export writes a header row naming every
column.

## Constraints
- The export writes a header row naming every column.
"""
    response = {
        "obligations": [
            # Quoted flat; in `task-01` the same sentence is broken after "every".
            _obligation("prose", "Write a header row.", "header row naming every column"),
            _obligation("bullet", "Write a header row.", "header row naming every column"),
        ],
        "open_questions": [],
        "requirement_dispositions": [
            _yielded("task-01", "prose"),
            _yielded("constraint-01", "bullet"),
        ],
    }
    log = UnusableAnswerLog()
    result = decompose(parse_task_file(task), client_returning(response), log)

    # Each stays with the requirement that derived it — the duplicate across two
    # sections survives for the linking stage to merge.
    assert result.requirement_map.requirements_for_obligation("prose") == ["task-01"]
    assert result.requirement_map.requirements_for_obligation("bullet") == ["constraint-01"]
    assert log.answers == []
    # And the wrapped occurrence is the one linked, newline included.
    prose = next(o for o in result.obligations if o.id == "prose")
    assert [span.text for span in prose.source_spans] == ["header row naming every\ncolumn"]


def test_two_runs_over_identical_task_text_produce_identical_review_state():
    """Attribution is decided from spans, which are a pure function of the
    parse — so adding this check cannot introduce a second draw."""
    obligations = [
        _obligation("render", "Render each invoice line.", "Render each invoice line."),
        _obligation("strayed", "Format money as USD.", "Format money as USD"),
        _obligation("usd", "Money is formatted as USD.", "with two decimals"),
    ]
    dispositions = [
        _yielded("task-01", "render", "strayed"),
        _yielded("constraint-01", "usd"),
        _declined("constraint-02"),
        _declined("completion-01"),
    ]

    first = _decompose(obligations, dispositions)
    second = _decompose(obligations, dispositions)

    assert first.model_dump_json() == second.model_dump_json()


# --- #266: which evidence an obligation requires ------------------------------


def _decompose_one(**overrides):
    """One obligation under `task-01`, with its evidence fields overridable."""
    result = _decompose(
        [
            {
                **_obligation("render", "Render each invoice line.", "Render each invoice line."),
                **overrides,
            }
        ],
        [_yielded("task-01", "render"), _declined("constraint-01"), _declined("constraint-02"),
         _declined("completion-01")],
    )
    return next(o for o in result.obligations if o.id == "render")


def test_a_narrowing_with_a_reason_is_kept():
    """The ordinary path: the model says less evidence is owed and says why, and
    both survive to review state."""
    obligation = _decompose_one(
        required_evidence="code_only",
        required_evidence_reason="a pinned version the source states outright",
    )

    assert obligation.required_evidence == "code_only"
    assert obligation.required_evidence_reason == "a pinned version the source states outright"


def test_a_narrowing_with_no_reason_is_discarded():
    """The false-green guard, and the reason it exists.

    Which evidence an obligation requires is a MODEL judgement now, where a
    section heading used to settle it. A wrong "no test is owed" silently removes
    the obligation from the axis the review measures it on, and nothing
    downstream can catch that — an obligation off the test axis produces no
    finding, by design.

    So an unreasoned narrowing is not honoured. It is indistinguishable from the
    question being skipped, and the safe reading of a skipped question is that
    every kind of evidence is still owed. Found by defect injection: removing
    this rule broke no test until this one existed.
    """
    obligation = _decompose_one(
        required_evidence="code_only",
        required_evidence_reason="",
    )

    assert obligation.required_evidence == "code_and_tests"
    assert obligation.required_evidence_reason == ""


def test_a_whitespace_only_reason_is_no_reason():
    """`""` is the obvious case and a bare truthiness check would catch it. A
    reason of spaces satisfies that check and says nothing, which is the same
    withheld judgement wearing a different shape."""
    obligation = _decompose_one(required_evidence="tests_only", required_evidence_reason="   \n ")

    assert obligation.required_evidence == "code_and_tests"


def test_a_reason_given_without_a_narrowing_is_dropped():
    """The mirror case. A reason on an obligation requiring both kinds explains
    nothing — there is no narrowing for it to justify — and carrying it would
    render an explanation under an obligation that was never narrowed."""
    obligation = _decompose_one(
        required_evidence="code_and_tests",
        required_evidence_reason="left over from somewhere",
    )

    assert obligation.required_evidence == "code_and_tests"
    assert obligation.required_evidence_reason == ""

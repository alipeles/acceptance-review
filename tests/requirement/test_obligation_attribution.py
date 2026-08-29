"""#244/#317: an obligation belongs to the requirement its call was asked about.

`_user_prompt` shows every call the whole registry, marks each requirement
`ANSWER FOR THIS` or `context only`, and asks the model not to derive obligations
for the ones another call owns. Nothing enforced that. The quotation was resolved
against the whole task file, so an obligation filed under one requirement while
quoting another's text produced a valid span and was accepted — misattribution
was undetectable by construction.

Observed in #180's Gate 1: a one-sentence Task requirement yielded seven
obligations, three of them the content of other requirements, which the linking
stage then reported as unreconcilable.

**#244 detected it afterwards; #317 makes it unsayable.** A call is asked about
one requirement and `source_quote` is an enum of that requirement's own spans, so
an obligation about another requirement has no quotation available to it. The
re-filing step that used to move such an obligation is gone with the ambiguity it
existed to resolve — and re-filing was itself a cost, because it manufactured a
duplicate of work the owning call had already done properly
(`docs/experiments/317-over-answering/findings.md` §4).

Responses are injected through the harness, per the replay-first invariant — no
live calls.
"""

from __future__ import annotations

import json

from acceptance.requirement.obligations import decompose
from acceptance.requirement.registry import build_registry
from acceptance.requirement.spans import quotable_spans
from acceptance.requirement.task_file import parse_task_file
from acceptance.supplied_ids import UnusableAnswerLog
from tests.support import (
    _fake_response,
    _supplied_enum,
    client_returning,
    covered_summary,
    model_client_with,
    uncovered_summary,
)

# Two requirements whose wording does NOT overlap, so a quotation identifies its
# requirement unambiguously and a misfiling cannot be a coincidence of phrasing.
TASK = """# Task
Render each invoice line.

## Constraints
- Format money as USD with two decimals.
- Keep the existing CSV export unchanged.

## Completion expectations
- A test covers the rounding boundary at half a cent.
"""

SUMMARY = uncovered_summary(["Render each invoice line."])


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


def _decompose(
    obligations: list[dict],
    dispositions: list[dict],
    log=None,
    task: str = TASK,
    summary: dict | None = None,
):
    """`summary` defaults to the covered answer, so the opening paragraph yields
    nothing and a fixture that says nothing about it stays well-formed. A fixture
    that DOES name `task-01` passes `SUMMARY`, which holds the whole paragraph
    uncovered and so routes that entry to the span authoring the summary."""
    response = {
        "obligations": obligations,
        "open_questions": [],
        "requirement_dispositions": dispositions,
    }
    return decompose(parse_task_file(task), client_returning(response, summary=summary), log)


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
        summary=SUMMARY,
    )

    assert result.requirement_map.requirements_for_obligation("render") == ["task-01"]
    assert result.requirement_map.requirements_for_obligation("usd") == ["constraint-01"]
    assert result.requirement_map.requirements_for_obligation("csv") == ["constraint-02"]
    assert result.requirement_map.requirements_for_obligation("rounding") == ["completion-01"]


def test_a_call_is_offered_only_its_own_requirements_quotations():
    """The guarantee, at the place it is made.

    An obligation about `constraint-01` is unrepresentable in a call about
    `constraint-02`, because the quotation that would have to source it is not
    among the values `source_quote` may take. That is the `DR-163` set applied to
    the field that actually carries the violation: `requirement_id` was already an
    enum when the model wrote eleven entries about the Constraints section and
    labelled all of them `task-01`, because an enum restricts the label, not what
    the entry is about.
    """
    parsed = parse_task_file(TASK)
    offered: dict[str, list[str]] = {}

    def completion_fn(**kwargs):
        if kwargs["response_format"]["json_schema"]["name"] == "_SummarySpans":
            return _fake_response(json.dumps(covered_summary(**kwargs)))
        asked = _supplied_enum("requirement_id", **kwargs)[0]
        offered[asked] = _supplied_enum("source_quote", **kwargs)
        return _fake_response(
            json.dumps(
                {
                    "open_questions": [],
                    "requirement_disposition": {
                        "requirement_id": asked,
                        "disposition": "no_obligation",
                        "reason": "Not applicable.",
                    },
                }
            )
        )

    decompose(parsed, model_client_with(completion_fn))

    by_id = {r.id: r for r in build_registry(parsed)}
    for requirement_id, quotes in offered.items():
        assert quotes == quotable_spans(by_id[requirement_id].text)

    # Concretely: the call about the CSV bullet cannot quote the USD bullet.
    assert not any("USD" in quote for quote in offered["constraint-02"])
    assert any("USD" in quote for quote in offered["constraint-01"])
    # And the summary is never in an ordinary call's answering set.
    assert "task-01" not in offered


def test_an_obligation_quoting_another_requirement_stays_where_it_was_derived():
    """The #180 shape, and what now happens to it.

    A provider that ignored the enum can still return `constraint-01`'s text from
    a call about `task-01`. The obligation is kept — losing a requirement is the
    worse failure — and it stays under the requirement whose call derived it.

    Moving it is what has been retired. Re-filing looked like a repair and was
    not: the requirement it moved onto had answered for itself in its own call, so
    the move manufactured a second obligation saying what that call had already
    said, which is precisely the unmerged-duplicate input the linking stage
    struggles with.
    """
    log = UnusableAnswerLog()
    result = _decompose(
        [
            _obligation("usd", "Format money as USD.", "Format money as USD"),
            # constraint-02's call, quoting constraint-01's text.
            _obligation("strayed", "Format money as USD.", "Format money as USD"),
        ],
        [
            _yielded("constraint-01", "usd"),
            _yielded("constraint-02", "strayed"),
            _declined("completion-01"),
        ],
        log,
    )

    assert result.requirement_map.requirements_for_obligation("strayed") == ["constraint-02"]
    assert result.requirement_map.requirements_for_obligation("usd") == ["constraint-01"]
    # Kept, and recorded rather than passed over.
    assert [answer.returned_id for answer in log.answers] == ["strayed"]
    assert log.answers[0].field == "source_quote"
    assert "only text this call was offered" in (log.answers[0].reason or "")
    # It carries no span, because the text it quoted is not in its requirement.
    strayed = next(o for o in result.obligations if o.id == "strayed")
    assert strayed.source_spans == []


def test_a_quotation_matching_no_requirement_at_all_is_recorded():
    """A quotation that lands nowhere cannot corroborate the attribution. The
    obligation is kept — losing a requirement is the worse failure — but the
    discrepancy is recorded rather than passed over."""
    log = UnusableAnswerLog()
    result = _decompose(
        [
            _obligation("usd", "Format money as USD.", "Format money as USD"),
            _obligation("invented", "Charge sales tax.", "## Constraints"),
        ],
        [
            _yielded("constraint-01", "usd", "invented"),
            _declined("constraint-02"),
            _declined("completion-01"),
        ],
        log,
    )

    assert [answer.returned_id for answer in log.answers] == ["invented"]
    assert log.answers[0].field == "source_quote"
    assert "invented" in [o.id for o in result.obligations]


def test_the_obligations_own_content_is_left_alone():
    """The stage records where a quotation landed and changes nothing else. A fix
    that rewrote the obligation would be inventing content."""
    result = _decompose(
        [
            _obligation("usd", "Format money as USD.", "Format money as USD"),
        ],
        [
            _yielded("constraint-01", "usd"),
            _declined("constraint-02"),
            _declined("completion-01"),
        ],
    )

    usd = next(o for o in result.obligations if o.id == "usd")
    assert usd.description == "Format money as USD."
    assert usd.type == "functional"
    assert usd.observable_behavior == "..."
    assert usd.explicit is True
    assert [span.text for span in usd.source_spans] == ["Format money as USD"]


def test_satisfied_by_absence_comes_from_the_answering_requirements_section():
    """Whether an obligation is satisfied by work NOT done is decided by the
    section it sits in (#153), and the section is now the answering
    requirement's own — there is no re-filing for it to have to follow.

    Asserts the absence flag, not which evidence is required (#266). The two
    were one field until a scope exclusion naming a BEHAVIOUR turned out to want
    a regression test; the heading still settles the absence beyond argument,
    and that is now all it settles.
    """
    task = """# Task
Render each invoice line.

## Constraints
- Format money as USD with two decimals.

## Scope exclusions
- Changing the PDF renderer.
"""
    result = _decompose(
        [
            _obligation("usd", "Format money as USD.", "Format money as USD"),
            _obligation("pdf", "Preserve the PDF renderer.", "Changing the PDF renderer"),
        ],
        [
            _yielded("constraint-01", "usd"),
            _yielded("exclusion-01", "pdf"),
        ],
        task=task,
    )

    assert next(o for o in result.obligations if o.id == "pdf").satisfied_by_absence
    # The control, so this is not passing because everything carries the flag.
    assert not next(o for o in result.obligations if o.id == "usd").satisfied_by_absence


def test_the_same_sentence_in_two_requirements_stays_with_each_ones_own_call():
    """The case that used to make search order load-bearing.

    Both requirements contain the quoted sentence, so containment alone cannot
    decide between them — which is why the retired resolver had to search the
    attributed requirement first, and why getting that order wrong silently moved
    a correctly attributed obligation. With one requirement per call there is
    nothing to decide: each obligation is located inside the requirement its own
    call was asked about.
    """
    task = """# Task
The export writes a header row naming every column.

## Constraints
- The export writes a header row naming every column.
"""
    log = UnusableAnswerLog()
    result = decompose(
        parse_task_file(task),
        client_returning(
            {
                "obligations": [
                    _obligation("prose", "Write a header row.", "writes a header row"),
                    _obligation("bullet", "Write a header row.", "writes a header row"),
                ],
                "open_questions": [],
                "requirement_dispositions": [
                    _yielded("task-01", "prose"),
                    _yielded("constraint-01", "bullet"),
                ],
            },
            summary=uncovered_summary(["The export writes a header row naming every column."]),
        ),
        log,
    )

    assert result.requirement_map.requirements_for_obligation("bullet") == ["constraint-01"]
    assert result.requirement_map.requirements_for_obligation("prose") == ["task-01"]
    assert log.answers == []
    # Each span points inside its own requirement, not at the first match in the
    # file.
    bullet = next(o for o in result.obligations if o.id == "bullet")
    prose = next(o for o in result.obligations if o.id == "prose")
    assert bullet.source_spans[0].start > prose.source_spans[0].start


def test_a_quotation_is_found_across_a_line_break():
    """Task prose is hard-wrapped and bullets usually are not, so one sentence
    appears wrapped in one requirement and flat in another. Matching on the exact
    substring finds it only in the unwrapped one, and the obligation in the
    wrapped requirement is left with no span at all.

    Caught on `tests/prompts/test_linking_prompt.py`'s corpus. The spans a call is
    OFFERED are whitespace-normalised for the same reason, so the model is never
    asked to reproduce a line break to be believed.
    """
    task = """# Task
Export invoices to a CSV file. The export writes a header row naming every
column.

## Constraints
- The export writes a header row naming every column.
"""
    result = decompose(
        parse_task_file(task),
        client_returning(
            {
                "obligations": [
                    # Quoted flat; in `task-01` the same sentence is broken after
                    # "every".
                    _obligation("prose", "Write a header row.", "header row naming every column"),
                    _obligation("bullet", "Write a header row.", "header row naming every column"),
                ],
                "open_questions": [],
                "requirement_dispositions": [
                    _yielded("task-01", "prose"),
                    _yielded("constraint-01", "bullet"),
                ],
            },
            summary=uncovered_summary(["The export writes a header row naming every column."]),
        ),
    )

    prose = next(o for o in result.obligations if o.id == "prose")
    bullet = next(o for o in result.obligations if o.id == "bullet")
    assert prose.source_spans and bullet.source_spans
    assert prose.source_spans[0].start < bullet.source_spans[0].start
    # The wrapped one carries the source's own bytes, newline included, so
    # `text == source[start:end]` still holds.
    assert "\n" in prose.source_spans[0].text

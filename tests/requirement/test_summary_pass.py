"""The step that accounts for the mandate's opening summary (#317).

The summary is the parent of every other requirement rather than a peer, so
asked about directly it answers for the whole mandate: over the recorded corpus,
8 of 35 calls with a `task-*` requirement in their answering set derived
obligations for requirements they had only been shown, against 0 of 68 without
one (`docs/experiments/317-over-answering/findings.md` §2).

So it is accounted for last, by a step that divides it into spans of its own
words and decides each against the obligations the rest of the mandate already
produced. Two things make that safe, and both are asserted here: the step yields
no obligations itself, and a partition it cannot honour stops the run rather
than being quietly repaired.

Responses are injected through the harness, per the replay-first invariant — no
live calls.
"""

from __future__ import annotations

import json

import pytest

from acceptance.llm import SchemaValidationError
from acceptance.requirement.obligations import decompose
from acceptance.requirement.summary import SUMMARY_STAGE
from acceptance.requirement.task_file import parse_task_file
from acceptance.supplied_ids import UnusableAnswerLog
from tests.support import _fake_response, _supplied_enum, model_client_with

# Two spans in the opening paragraph, and a bullet that requires the first of
# them. So one span is genuinely already required and the other is genuinely not,
# and a step that answered the same way to both would fail whichever answer it
# gave.
TASK = """# Task
The export writes a header row. The export runs nightly.

## Constraints
- The export writes a header row naming every column.
"""

_COVERED_SPAN = "The export writes a header row."
_UNCOVERED_SPAN = "The export runs nightly."


def _obligation(oid: str, description: str, quote: str) -> dict:
    return {
        "id": oid,
        "description": description,
        "type": "functional",
        "importance": "normal",
        "explicit": True,
        "observable_behavior": "...",
        "source_quote": quote,
        "required_evidence": "code_and_tests",
        "required_evidence_reason": "",
    }


def _client(summary_answer, *, decline_spans: bool = False, calls: list | None = None):
    """A double answering the bullet, then the summary, then any span.

    `summary_answer` is the raw `_SummarySpans` payload, so a test states the
    partition and the verdicts it wants to exercise rather than reverse-
    engineering them.
    """

    def completion_fn(**kwargs):
        name = kwargs["response_format"]["json_schema"]["name"]
        if calls is not None:
            calls.append((name, kwargs["model"], _supplied_enum("requirement_id", **kwargs)))
        if name == "_SummarySpans":
            return _fake_response(json.dumps(summary_answer))

        asked = _supplied_enum("requirement_id", **kwargs)[0]
        if asked == "constraint-01":
            disposition = {
                "requirement_id": asked,
                "disposition": "yielded",
                "obligation": _obligation(
                    "header-row",
                    "The export writes a header row naming every column.",
                    "The export writes a header row naming every column.",
                ),
                "more_obligations": [],
            }
        elif decline_spans:
            disposition = {
                "requirement_id": asked,
                "disposition": "no_obligation",
                "reason": "declined, which contradicts the step that sent this span here",
            }
        else:
            disposition = {
                "requirement_id": asked,
                "disposition": "yielded",
                "obligation": _obligation(
                    "runs-nightly",
                    "The export runs nightly.",
                    _supplied_enum("source_quote", **kwargs)[0],
                ),
                "more_obligations": [],
            }
        return _fake_response(
            json.dumps({"open_questions": [], "requirement_disposition": disposition})
        )

    return model_client_with(completion_fn)


def _spans(*entries) -> dict:
    """A partition and its verdicts, from `(span, disposition)` pairs."""
    return {
        "spans": [span for span, _ in entries],
        "span_dispositions": [
            {
                "span_index": index,
                "nearest": ["header-row"] if verdict == "covered" else [],
                "counterexample": (
                    "none"
                    if verdict == "covered"
                    else "a change writing the header row but running on demand"
                ),
                "disposition": verdict,
            }
            for index, (_, verdict) in enumerate(entries)
        ],
    }


# --- the partition must be honourable ---------------------------------------


def test_a_span_that_is_not_a_substring_of_the_summary_is_refused():
    """A span the summary does not contain cannot be quoted from it, so an
    obligation derived from it would trace to text that is not there — the
    typed-and-linked invariant broken at the source."""
    answer = _spans(("The export writes a footer row.", "uncovered"))

    with pytest.raises(SchemaValidationError) as raised:
        decompose(parse_task_file(TASK), _client(answer))

    assert "not a substring of the summary" in str(raised.value)


def test_a_span_decided_twice_is_refused():
    """Two verdicts for one span is a response contradicting itself, and taking
    either one silently would make the answer depend on ordering."""
    answer = _spans((_COVERED_SPAN, "covered"), (_UNCOVERED_SPAN, "uncovered"))
    answer["span_dispositions"].append(dict(answer["span_dispositions"][0]))

    with pytest.raises(SchemaValidationError) as raised:
        decompose(parse_task_file(TASK), _client(answer))

    assert "decided 2 times" in str(raised.value)


def test_a_span_left_undecided_is_refused():
    """The failure the partition exists to make visible: a property of the
    summary that nothing said anything about. Under the shape this replaces, the
    division happened in the model's head and only its conclusions were visible,
    so a span it silently skipped was indistinguishable from one it never saw."""
    answer = _spans((_COVERED_SPAN, "covered"), (_UNCOVERED_SPAN, "uncovered"))
    answer["span_dispositions"] = answer["span_dispositions"][:1]

    with pytest.raises(SchemaValidationError) as raised:
        decompose(parse_task_file(TASK), _client(answer))

    assert "decided 0 times" in str(raised.value)


def test_a_verdict_disagreeing_with_its_own_counterexample_is_refused():
    """`counterexample` is written before `disposition` so the verdict follows
    the argument. That only means something if the two are held to agree — the
    union shape, where the verdict came first, answered `covered` on every span
    of every draw while its own prose named the gap."""
    answer = _spans((_COVERED_SPAN, "covered"), (_UNCOVERED_SPAN, "uncovered"))
    answer["span_dispositions"][0]["counterexample"] = "a change that omits the header row"

    with pytest.raises(SchemaValidationError) as raised:
        decompose(parse_task_file(TASK), _client(answer))

    assert "covered but its counterexample is not the single word 'none'" in str(raised.value)


def test_nearest_naming_an_obligation_that_was_not_shown_is_refused():
    """The supplied-id guarantee (#163) for this step. `nearest` is what the
    coverage claim rests on, so a claim resting on an obligation that does not
    exist is not a weaker claim — it is no claim."""
    answer = _spans((_COVERED_SPAN, "covered"), (_UNCOVERED_SPAN, "uncovered"))
    answer["span_dispositions"][0]["nearest"] = ["no-such-obligation"]

    with pytest.raises(SchemaValidationError) as raised:
        decompose(parse_task_file(TASK), _client(answer))

    assert "was not on the list shown" in str(raised.value)


# --- what each verdict yields ------------------------------------------------


def test_a_span_the_derived_obligations_require_yields_no_obligation():
    """The whole point. The bullet already requires the header row, so the
    paragraph must not derive a second obligation saying so — that duplicate is
    what the linking stage then has to merge, and what it sometimes fails to."""
    result = decompose(
        parse_task_file(TASK),
        _client(_spans((_COVERED_SPAN, "covered"), (_UNCOVERED_SPAN, "uncovered"))),
    )

    summary_ids = result.requirement_map.disposition_for("task-01").obligation_ids
    descriptions = [o.description for o in result.obligations if o.id in summary_ids]
    assert descriptions == ["The export runs nightly."]
    assert not any("header row" in d for d in descriptions)


def test_a_covered_span_is_recorded_with_what_was_held_to_require_it():
    """Deriving no duplicate is the improvement; losing the record of why would
    be a regression hidden inside it. Under the shape this replaces, the fact
    that both requirements demanded the header row was recorded — as a merge."""
    result = decompose(
        parse_task_file(TASK),
        _client(_spans((_COVERED_SPAN, "covered"), (_UNCOVERED_SPAN, "uncovered"))),
    )

    reason = result.requirement_map.disposition_for("task-01").reason or ""
    assert _COVERED_SPAN in reason
    assert "already required by header-row" in reason
    assert f"{_UNCOVERED_SPAN!r} not already required" in reason


def test_a_span_they_do_not_require_yields_an_obligation_quoting_that_span():
    """And the quotation is taken from the mandate rather than from the answer
    that named it: the model repairs a task file's grammar when it quotes, and a
    repaired quotation stops matching the source it claims to come from."""
    parsed = parse_task_file(TASK)
    result = decompose(
        parsed, _client(_spans((_COVERED_SPAN, "covered"), (_UNCOVERED_SPAN, "uncovered")))
    )

    nightly = next(o for o in result.obligations if o.id == "runs-nightly")
    assert [span.text for span in nightly.source_spans] == [_UNCOVERED_SPAN]
    span = nightly.source_spans[0]
    assert parsed.source[span.start : span.end] == span.text


def test_an_uncovered_span_that_yields_nothing_stops_the_run():
    """It was reached only because the step before it argued, with a
    counterexample, that the derived obligations do not require this property. A
    step that then declines it has contradicted the one that sent it, and the
    property would be lost in the gap between them."""
    answer = _spans((_COVERED_SPAN, "covered"), (_UNCOVERED_SPAN, "uncovered"))

    with pytest.raises(SchemaValidationError) as raised:
        decompose(parse_task_file(TASK), _client(answer, decline_spans=True))

    message = str(raised.value)
    assert "neither an obligation nor an open question" in message
    assert _UNCOVERED_SPAN in message


def test_the_deciding_step_yields_no_obligations_itself():
    """Obligations for uncovered spans are authored by a SEPARATE call, asked
    about that span alone — the ordinary per-requirement shape, which
    `findings.md` §2 measures as over-answering 0 times in 68 non-task batches.
    The deciding step's own response has no field to put an obligation in."""
    from acceptance.requirement.summary import _SummarySpans

    assert set(_SummarySpans.model_fields) == {"spans", "span_dispositions"}
    verdict = _SummarySpans.model_fields["span_dispositions"].annotation.__args__[0]
    # `disposition` LAST, so the verdict follows the argument rather than being
    # justified backwards from it.
    assert list(verdict.model_fields) == [
        "span_index",
        "nearest",
        "counterexample",
        "disposition",
    ]
    assert "obligation" not in verdict.model_fields


# --- the whole path, and which model ran each step ---------------------------


def test_the_whole_path_runs_from_the_mandate_through_to_the_obligations():
    """Not any one step alone. A mandate goes in, and what comes out is every
    requirement accounted for, with the summary settled against the obligations
    the bullets produced — so a change that passes the focused tests while
    breaking the join between them fails here."""
    result = decompose(
        parse_task_file(TASK),
        _client(_spans((_COVERED_SPAN, "covered"), (_UNCOVERED_SPAN, "uncovered"))),
    )

    assert [d.requirement_id for d in result.requirement_map.dispositions] == [
        "task-01",
        "constraint-01",
    ]
    assert [o.id for o in result.obligations] == ["runs-nightly", "header-row"]
    assert result.requirement_map.unyielding() == []
    # Registry order, so the summary's obligation leads even though it was
    # derived last.
    assert result.requirement_map.requirements_for_obligation("runs-nightly") == ["task-01"]
    assert result.requirement_map.requirements_for_obligation("header-row") == ["constraint-01"]


def test_the_summary_step_runs_on_the_model_it_names_and_the_rest_on_the_runs():
    """A step may name its own model, and one that names none uses the run's.
    Counted off the requests as sent, not off configuration: what a reader needs
    is the judge that actually answered."""
    calls: list = []
    client = _client(
        _spans((_COVERED_SPAN, "covered"), (_UNCOVERED_SPAN, "uncovered")), calls=calls
    )
    client._stage_models = {SUMMARY_STAGE: "openai/some-larger-model"}

    decompose(parse_task_file(TASK), client)

    by_schema = {name: model for name, model, _ in calls}
    assert by_schema["_SummarySpans"] == "openai/some-larger-model"
    assert by_schema["_Decomposition"] == client.model
    # And the run reports it, per stage, observed from the calls.
    assert client.stage_models_in_force == {
        "decompose": client.model,
        SUMMARY_STAGE: "openai/some-larger-model",
    }


def test_an_unusable_partition_is_recorded_before_it_stops_the_run():
    """The refusal is loud, and it also leaves a record naming the summary and
    the reason — an abort with nothing written down is a review that cannot be
    diagnosed afterwards."""
    log = UnusableAnswerLog()
    answer = _spans((_COVERED_SPAN, "covered"), (_UNCOVERED_SPAN, "uncovered"))
    answer["span_dispositions"] = answer["span_dispositions"][:1]

    with pytest.raises(SchemaValidationError):
        decompose(parse_task_file(TASK), _client(answer), log)

    recorded = [a for a in log.answers if a.stage == SUMMARY_STAGE]
    assert recorded and recorded[0].returned_id == "task-01"
    assert "decided 0 times" in (recorded[0].reason or "")

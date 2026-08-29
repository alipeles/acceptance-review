"""Obligation derivation issues one call per requirement (#204, DR-204, #317).

One call over the whole registry sheds work the way DR-164 measured a stage
later: an observed run over ~36 requirements at ~2.5k input tokens produced no
obligation for 9 of them, in a schema-valid response nothing downstream could
question. Size was never the binding constraint — the number of independent
judgments in one response is.

#204 partitioned the requirements into batches. #317 narrowed the batch to one,
which is not a further turn of the same dial: it is what lets `source_quote` be
an enum of the answering requirement's own spans, so an obligation about another
requirement becomes unsayable rather than detected afterwards.

The call scopes what must be ANSWERED FOR, never what may be READ.

Responses are injected through the harness's completion_fn per the replay-first
invariant — no live calls.
"""

from __future__ import annotations

import json

import pytest

from acceptance.config import RunConfig
from acceptance.llm import SchemaValidationError
from acceptance.requirement.obligations import (
    ONE_REQUIREMENT_PER_CALL,
    _Decomposition,
    decompose,
)
from acceptance.requirement.summary import SUMMARY_STAGE
from acceptance.requirement.task_file import parse_task_file
from acceptance.supplied_ids import UnusableAnswerLog
from tests.support import _completed, _fake_response, _supplied_enum, model_client_with


def _task(n: int) -> str:
    bullets = "\n".join(f"- Constraint number {i} holds." for i in range(1, n + 1))
    return f"# Task\nDo the thing.\n\n## Constraints\n{bullets}\n"


def _declining(**kwargs) -> dict:
    """A well-formed response that declines the requirement the call asked about.

    Declining rather than yielding keeps the response valid without inventing
    obligation ids, which is not what these tests are about — they are about how
    the work is SPLIT. The summary pass gets the covered answer from `_completed`,
    so the opening paragraph yields nothing and issues no further call.
    """
    return _completed(
        {"obligations": [], "open_questions": [], "requirement_dispositions": []},
        **kwargs,
    )


def _client(calls: list[dict]):
    """Records every ordinary decompose request and declines its requirement."""

    def completion_fn(**kwargs):
        if kwargs["response_format"]["json_schema"]["name"] == "_Decomposition":
            calls.append(kwargs)
        return _fake_response(json.dumps(_declining(**kwargs)))

    return model_client_with(completion_fn)


# --- how the work is split --------------------------------------------------


@pytest.mark.parametrize("constraints", [1, 3, 8, 20])
def test_a_task_file_of_n_requirements_produces_one_call_per_requirement(constraints):
    """The opening paragraph is not among them: it is accounted for by the
    summary step, which has its own call and its own schema."""
    calls: list[dict] = []
    parsed = parse_task_file(_task(constraints))

    decompose(parsed, _client(calls))

    assert len(calls) == constraints
    for call in calls:
        assert len(_supplied_enum("requirement_id", **call)) == 1


def test_no_ordinary_call_is_asked_to_account_for_the_opening_summary():
    """The whole reason the summary has a step of its own. Asked about directly
    it answers for the mandate: 8 of 35 recorded calls with a `task-*`
    requirement in their answering set derived obligations for requirements they
    had only been shown, against 0 of 68 without one."""
    calls: list[dict] = []

    decompose(parse_task_file(_task(6)), _client(calls))

    answered = [_supplied_enum("requirement_id", **call)[0] for call in calls]
    assert not any(rid.startswith("task-") for rid in answered)
    assert sorted(answered) == sorted(f"constraint-{i:02d}" for i in range(1, 7))


def test_every_requirement_carries_a_disposition_after_the_merge():
    """The property splitting must not cost. Splitting the work is only safe if
    the merged result still accounts for the whole mandate — otherwise it trades
    one silent loss for another."""
    parsed = parse_task_file(_task(20))

    result = decompose(parsed, _client([]))

    registry_ids = [r.id for r in result.requirement_map.requirements]
    disposed = [d.requirement_id for d in result.requirement_map.dispositions]
    assert disposed == registry_ids
    assert len(registry_ids) == 21  # 20 constraints + the Task paragraph


def test_a_call_answers_for_one_requirement_and_reads_them_all():
    """#204 deliverable 2. Every call sees the whole task file; only the
    answering is split. A call shown just its own bullet could not notice that a
    later section settles a term an earlier one leaves open (#178)."""
    calls: list[dict] = []
    parsed = parse_task_file(_task(20))

    decompose(parsed, _client(calls))

    assert len(calls) == 20
    for call in calls:
        prompt = call["messages"][-1]["content"]
        # Every requirement's text, in every call.
        for i in range(1, 21):
            assert f"Constraint number {i} holds." in prompt
        # But exactly one of them is asked for.
        assert prompt.count("[ANSWER FOR THIS]") == 1
        assert "[context only]" in prompt

    # Between them the calls answer for every bullet exactly once.
    answered = [
        line.split("]")[0].lstrip("[")
        for call in calls
        for line in call["messages"][-1]["content"].splitlines()
        if "[ANSWER FOR THIS]" in line
    ]
    assert sorted(answered) == sorted(set(answered))
    assert len(answered) == 20


# --- the partition descriptor is a determinism control ----------------------


def test_changing_the_partition_size_changes_the_request_key():
    """A determinism control in the same sense as the seed: it changes what is
    asked of the model, so recordings made under the old partitioning must be
    re-verified rather than silently replayed. That is why derivation still
    carries a descriptor now that the size is fixed at one — a transcript
    recorded when it was eight must not replay as though nothing had moved."""
    client = RunConfig().build_client()
    messages = [{"role": "user", "content": "batch"}]

    at_one = client.build_request(messages, _Decomposition, {"size": 1})
    at_eight = client.build_request(messages, _Decomposition, {"size": 8})

    assert at_one["partition"] == {"size": 1}
    assert at_one != at_eight


def test_the_batch_index_and_count_never_enter_the_request():
    """Left out for the opposite reason to `size`: the messages already differ
    between batches, so including them would buy no distinguishing power while
    making a batch's key depend on how many batches follow it. Appending one
    requirement would then invalidate the FIRST batch's transcript even though
    its content is unchanged."""
    from acceptance.partition import partition

    batches = partition(list(range(20)), 8, key=lambda i: i)

    assert [b.request_partition() for b in batches] == [{"size": 8}] * 3
    assert {b.index for b in batches} == {0, 1, 2}
    assert all(b.count == 3 for b in batches)


def test_provenance_reports_the_derivation_size_observed_from_the_calls():
    """#160: provenance describes the run that happened, not the run that was
    configured."""
    from acceptance.config import provenance_for

    calls: list[dict] = []
    client = _client(calls)
    decompose(parse_task_file(_task(20)), client)

    assert provenance_for(client).request_partition_sizes == {"decompose": ONE_REQUIREMENT_PER_CALL}


def test_provenance_reports_the_model_each_step_used():
    """A step may name its own model (#317), so the run's model is no longer the
    whole answer. Observed from the calls for the same reason the partition size
    is: a reader asking which judge produced a finding needs the one that
    answered, not the one that was configured."""
    from acceptance.config import provenance_for

    client = _client([])
    decompose(parse_task_file(_task(4)), client)

    stage_models = provenance_for(client).stage_models
    assert set(stage_models) == {"decompose", SUMMARY_STAGE}
    assert stage_models["decompose"] == client.model
    assert stage_models[SUMMARY_STAGE] == client.model_for(SUMMARY_STAGE)


# --- a call may only answer for the requirement it was asked about ------------


def test_a_disposition_for_a_requirement_the_call_was_not_asked_about_is_recorded():
    """Not silently filed. The requirement belongs to another call, which answers
    for it; letting this one through would make the merged result depend on which
    call returned last.

    Unreachable under constrained decoding, where `requirement_id` is a
    single-valued enum — which is why the local check has to exist anyway (#163):
    the harness deliberately runs against providers whose structured-output
    support differs.
    """
    parsed = parse_task_file(_task(6))
    unusable = UnusableAnswerLog()

    def completion_fn(**kwargs):
        payload = _declining(**kwargs)
        asked = _supplied_enum("requirement_id", **kwargs)
        if asked and asked[0] == "constraint-03":
            # Answer for a requirement this call was not asked about.
            payload["requirement_disposition"] = {
                "requirement_id": "constraint-01",
                "disposition": "no_obligation",
                "reason": "overstepping",
            }
        return _fake_response(json.dumps(payload))

    with pytest.raises(SchemaValidationError) as raised:
        decompose(parsed, model_client_with(completion_fn), unusable)

    # The requirement whose answer was displaced is the one reported missing.
    assert "constraint-03" in str(raised.value)
    overstepped = [a for a in unusable.answers if a.returned_id == "constraint-01"]
    assert overstepped, "a call answering outside its own id must be recorded"
    assert all(a.stage == "decompose" for a in overstepped)
    assert any("not asked about" in (a.reason or "") for a in overstepped)


# --- ids are minted per call, so resolution must be per call -----------------


def test_two_calls_minting_the_same_obligation_id_stay_separate():
    """The mis-link splitting the work is supposed to make impossible.

    Each response mints its own obligation ids, so two calls can both return
    `shared-slug` meaning different things. `_unique` renames the second, but a
    GLOBAL model-id -> final-id map would resolve the second call's disposition
    onto the FIRST call's obligation — a requirement silently attached to an
    obligation derived from another requirement, which is exactly what DR-204
    forbids.
    """
    parsed = parse_task_file(_task(2))

    def completion_fn(**kwargs):
        if kwargs["response_format"]["json_schema"]["name"] == "_SummarySpans":
            return _fake_response(json.dumps(_declining(**kwargs)))
        asked = _supplied_enum("requirement_id", **kwargs)[0]
        return _fake_response(
            json.dumps(
                {
                    "open_questions": [],
                    "requirement_disposition": {
                        "requirement_id": asked,
                        "disposition": "yielded",
                        # Carried, not referenced — each call mints its own.
                        "obligation": {
                            "id": "shared-slug",
                            "description": f"Derived for {asked}.",
                            "type": "functional",
                            "importance": "normal",
                            "explicit": True,
                            "observable_behavior": "...",
                            "source_quote": _supplied_enum("source_quote", **kwargs)[0],
                            "required_evidence": "code_and_tests",
                            "required_evidence_reason": "",
                        },
                        "more_obligations": [],
                    },
                }
            )
        )

    result = decompose(parsed, model_client_with(completion_fn))

    # Renamed, not merged.
    assert [o.id for o in result.obligations] == ["shared-slug", "shared-slug-2"]
    # And each requirement holds ITS OWN call's obligation, not the first one's.
    claimed = {
        d.requirement_id: d.obligation_ids
        for d in result.requirement_map.dispositions
        if d.obligation_ids
    }
    assert {tuple(v) for v in claimed.values()} == {("shared-slug",), ("shared-slug-2",)}
    # No obligation serves two requirements.
    for obligation in result.obligations:
        owners = result.requirement_map.requirements_for_obligation(obligation.id)
        assert len(owners) == 1

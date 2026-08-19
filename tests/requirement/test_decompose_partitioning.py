"""Obligation derivation is partitioned by requirement batch (#204, DR-204).

One call over the whole registry sheds work the way DR-164 measured a stage
later: an observed run over ~36 requirements at ~2.5k input tokens produced no
obligation for 9 of them, in a schema-valid response nothing downstream could
question. Size was never the binding constraint — the number of independent
judgments in one response is.

The batch scopes what a call must ANSWER FOR, never what it may READ.

Responses are injected through the harness's completion_fn per the replay-first
invariant — no live calls.
"""

from __future__ import annotations

import json

import pytest

from acceptance.config import RunConfig
from acceptance.llm import SchemaValidationError
from acceptance.requirement.obligations import _Decomposition, decompose
from acceptance.requirement.task_file import parse_task_file
from acceptance.supplied_ids import UnusableAnswerLog
from tests.support import _completed, _fake_response, _supplied_enum, model_client_with


def _task(n: int) -> str:
    bullets = "\n".join(f"- Constraint number {i} holds." for i in range(1, n + 1))
    return f"# Task\nDo the thing.\n\n## Constraints\n{bullets}\n"


def _declining(**kwargs) -> dict:
    """A well-formed response that declines each batch's own ids.

    Declining rather than yielding keeps the response valid without inventing
    obligation ids, which is not what these tests are about — they are about how
    the work is SPLIT.
    """
    return _completed(
        {"obligations": [], "open_questions": [], "requirement_dispositions": []},
        **kwargs,
    )


def _client(calls: list[dict]):
    """Records every decompose request and declines each batch's own ids."""

    def completion_fn(**kwargs):
        if kwargs["response_format"]["json_schema"]["name"] == "_Decomposition":
            calls.append(kwargs)
        return _fake_response(json.dumps(_declining(**kwargs)))

    return model_client_with(completion_fn)


# --- how the work is split --------------------------------------------------


@pytest.mark.parametrize(
    "constraints, size, expected_calls",
    [
        # N constraints is N+1 requirements: the Task paragraph is one too.
        (3, 8, 1),  # 4 requirements, fewer than one batch
        (7, 8, 1),  # 8 requirements, exactly one batch
        (8, 8, 2),  # 9 requirements, one over
        (20, 8, 3),  # 21 requirements, ceil(21 / 8)
        (5, 1, 6),  # 6 requirements, one call each
    ],
)
def test_a_task_file_of_n_requirements_produces_ceil_n_over_size_calls(
    constraints, size, expected_calls
):
    calls: list[dict] = []
    parsed = parse_task_file(_task(constraints))

    decompose(parsed, _client(calls), batch_size=size)

    assert len(calls) == expected_calls


def test_every_requirement_carries_a_disposition_after_the_merge():
    """The property partitioning must not cost. Splitting the work is only safe
    if the merged result still accounts for the whole mandate — otherwise it
    trades one silent loss for another."""
    parsed = parse_task_file(_task(20))

    result = decompose(parsed, _client([]), batch_size=8)

    registry_ids = [r.id for r in result.requirement_map.requirements]
    disposed = [d.requirement_id for d in result.requirement_map.dispositions]
    assert disposed == registry_ids
    assert len(registry_ids) == 21  # 20 constraints + the Task paragraph


def test_the_batch_scopes_what_a_call_answers_for_not_what_it_reads():
    """#204 deliverable 2. Every call sees the whole task file; only the
    answering is split. A call shown just its own bullets could not notice that
    a later section settles a term an earlier one leaves open (#178)."""
    calls: list[dict] = []
    parsed = parse_task_file(_task(20))

    decompose(parsed, _client(calls), batch_size=8)

    assert len(calls) == 3
    for call in calls:
        prompt = call["messages"][-1]["content"]
        # Every requirement's text, in every call.
        for i in range(1, 21):
            assert f"Constraint number {i} holds." in prompt
        # But each call is told to answer for only some of them.
        assert prompt.count("[ANSWER FOR THIS]") <= 8
        assert "[context only]" in prompt

    # Between them the calls answer for every requirement exactly once.
    answered = [
        line.split("]")[0].lstrip("[")
        for call in calls
        for line in call["messages"][-1]["content"].splitlines()
        if "[ANSWER FOR THIS]" in line
    ]
    assert sorted(answered) == sorted(set(answered))
    assert len(answered) == 21


# --- the batch size is a determinism control --------------------------------


def test_changing_the_batch_size_changes_the_request_key():
    """A determinism control in the same sense as the seed: it changes what is
    asked of the model, so recordings made under the old partitioning must be
    re-verified rather than silently replayed."""
    client = RunConfig().build_client()
    messages = [{"role": "user", "content": "batch"}]

    at_eight = client.build_request(messages, _Decomposition, {"size": 8})
    at_twelve = client.build_request(messages, _Decomposition, {"size": 12})

    assert at_eight["partition"] == {"size": 8}
    assert at_eight != at_twelve


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
    decompose(parse_task_file(_task(20)), client, batch_size=8)

    assert provenance_for(client).request_partition_sizes == {"decompose": 8}


# --- a batch may only answer for its own requirements ------------------------


def test_a_disposition_for_a_requirement_the_call_was_not_given_is_recorded():
    """Not silently filtered. The requirement belongs to another batch, which
    answers for it; letting this one through would make the merged result depend
    on which batch returned last."""
    parsed = parse_task_file(_task(20))
    unusable = UnusableAnswerLog()

    def completion_fn(**kwargs):
        payload = _declining(**kwargs)
        # Answer for a requirement this call was NOT given. Added only where it
        # really is outside the call's share — adding it to the batch that owns
        # it would be a duplicate disposition, a different rejection.
        if "constraint-01" not in _supplied_enum("requirement_id", **kwargs):
            payload["requirement_dispositions"] = list(payload["requirement_dispositions"]) + [
                {
                    "requirement_id": "constraint-01",
                    "disposition": "no_obligation",
                    "reason": "overstepping this batch",
                }
            ]
        return _fake_response(json.dumps(payload))

    result = decompose(parsed, model_client_with(completion_fn), unusable, batch_size=8)

    overstepped = [a for a in unusable.answers if a.returned_id == "constraint-01"]
    assert overstepped, "a batch answering outside its own ids must be recorded"
    assert all(a.stage == "decompose" for a in overstepped)
    # `scan` also records it as an id the call was not supplied, without a
    # reason; the batch-scoping rejection is the one that explains itself.
    assert any("not asked to answer for" in (a.reason or "") for a in overstepped)

    # And the requirement is not treated as disposed by a call that did not own
    # it: constraint-01's disposition is the one its OWN batch returned.
    assert result.requirement_map.disposition_for("constraint-01") is not None


def test_an_id_outside_the_registry_entirely_is_still_refused_by_name():
    """Distinct from overstepping a batch: that is a call answering for another
    call's requirement, this is a response inventing one. The first is recorded
    and dropped; the second is a malformed response and is refused loudly, so
    the error names the id rather than reporting some other requirement as
    unaccounted for."""
    parsed = parse_task_file(_task(3))

    def completion_fn(**kwargs):
        payload = _declining(**kwargs)
        payload["requirement_dispositions"] = list(payload["requirement_dispositions"]) + [
            {
                "requirement_id": "constraint-99",
                "disposition": "no_obligation",
                "reason": "no such requirement",
            }
        ]
        return _fake_response(json.dumps(payload))

    with pytest.raises(SchemaValidationError) as raised:
        decompose(parsed, model_client_with(completion_fn), batch_size=8)

    assert "constraint-99" in str(raised.value)


# --- ids are minted per call, so resolution must be per call -----------------


def test_two_batches_minting_the_same_obligation_id_stay_separate():
    """The mis-link partitioning is supposed to make impossible.

    Each response mints its own obligation ids, so two batches can both return
    `shared-slug` meaning different things. `_unique` renames the second, but a
    GLOBAL model-id -> final-id map would resolve the second batch's disposition
    onto the FIRST batch's obligation — a requirement silently attached to an
    obligation derived from another requirement, which is exactly what DR-204
    forbids and what partitioning is meant to make unrepresentable.
    """
    parsed = parse_task_file(_task(12))  # 13 requirements -> 2 batches at size 8

    def completion_fn(**kwargs):
        supplied = _supplied_enum("requirement_id", **kwargs)
        payload = {
            "open_questions": [],
            "requirement_dispositions": [
                {
                    "requirement_id": supplied[0],
                    "disposition": "yielded",
                    # Carried, not referenced — each batch mints its own.
                    "obligation": {
                        "id": "shared-slug",
                        "description": f"Derived for {supplied[0]}.",
                        "type": "functional",
                        "importance": "normal",
                        "explicit": True,
                        "observable_behavior": "...",
                        "source_quote": "Do the thing.",
                        "required_evidence": "code_and_tests",
                        "required_evidence_reason": "",
                    },
                    "more_obligations": [],
                }
            ]
            + [
                {
                    "requirement_id": rid,
                    "disposition": "no_obligation",
                    "reason": "not this test's subject",
                }
                for rid in supplied[1:]
            ],
        }
        return _fake_response(json.dumps(payload))

    result = decompose(parsed, model_client_with(completion_fn), batch_size=8)

    # Renamed, not merged.
    assert [o.id for o in result.obligations] == ["shared-slug", "shared-slug-2"]
    # And each requirement holds ITS OWN batch's obligation, not the first one's.
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

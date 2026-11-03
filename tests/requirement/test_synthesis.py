"""Synthesis: obligations built from claims (#437).

These inject the synthesis answer, so they test the code around the call: how
citations become claim references, what is done with a citation the call never
supplied, the rules the type settles, and that the pipeline and the `decompose`
command actually call the step. What the model SYNTHESIZES from real mandates is
in `tests/prompts/test_synthesis_prompt.py`.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from acceptance.change.diff import extract_change_set
from acceptance.pipeline import run_review
from acceptance.requirement.claims import build_claims
from acceptance.requirement.synthesis import SYNTHESIS_STAGE, synthesize
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import ObligationType, Reference, RequiredEvidence
from acceptance.serialization import canonical_json
from acceptance.supplied_ids import UnusableAnswerLog
from tests.requirement.test_claims import _MANDATE, _all, _repo
from tests.support import (
    _fake_response,
    _supplied_enum,
    client_dispatching,
    make_obligation,
    model_client_with,
)


def _claims():
    return build_claims(parse_task_file(_MANDATE), _all("feeds"))


def _claim_with(claim_set, fragment):
    return next(claim for claim in claim_set.claims if fragment in claim.text)


def _answer(**overrides):
    entry = {
        "id": "dates-in-utc",
        "reason": "r",
        "claim_id": "",
        "more_claim_ids": [],
        "type": "requested_behavior",
        "description": "The export writes every date in UTC.",
        "observable_behavior": "exported dates end in Z",
        "explicit": True,
        "importance": "normal",
    }
    entry.update(overrides)
    return entry


def _client(answers, calls: list | None = None):
    """A client answering synthesis with `answers(supplied_claim_ids)`."""

    def completion_fn(**kwargs):
        if calls is not None:
            calls.append(kwargs)
        supplied = _supplied_enum("claim_id", **kwargs)
        return _fake_response(json.dumps({"obligations": answers(supplied)}))

    return model_client_with(completion_fn)


def test_an_obligation_cites_its_claims_in_mandate_order_with_their_spans():
    claim_set = _claims()
    utc = _claim_with(claim_set, "UTC")
    z = _claim_with(claim_set, "ends in Z")

    [obligation] = synthesize(
        claim_set,
        _client(lambda ids: [_answer(claim_id=z.id, more_claim_ids=[utc.id, z.id])]),
    )

    assert obligation.claims == [
        Reference(kind="claim", id=utc.id),
        Reference(kind="claim", id=z.id),
    ]
    assert obligation.source_spans == [utc.span, z.span]
    assert obligation.provenance == "stated"
    assert obligation.type is ObligationType.REQUESTED_BEHAVIOR


def test_one_claim_can_support_two_obligations():
    claim_set = _claims()
    clock = _claim_with(claim_set, "clock module")

    obligations = synthesize(
        claim_set,
        _client(
            lambda ids: [
                _answer(id="utc", claim_id=clock.id),
                _answer(id="uses-clock", claim_id=clock.id, type="constraint"),
            ]
        ),
    )

    assert [o.id for o in obligations] == ["utc", "uses-clock"]
    assert all(o.claims == [Reference(kind="claim", id=clock.id)] for o in obligations)


def test_the_call_offers_only_the_mandates_claim_ids():
    claim_set = _claims()
    calls: list = []
    synthesize(claim_set, _client(lambda ids: [], calls))

    assert len(calls) == 1
    assert _supplied_enum("claim_id", **calls[0]) == [c.id for c in claim_set.claims]


def test_the_prompt_gives_each_claim_as_typed_fields_not_the_mandate():
    claim_set = _claims()
    calls: list = []
    synthesize(claim_set, _client(lambda ids: [], calls))

    prompt = "\n".join(m["content"] for m in calls[0]["messages"] if isinstance(m["content"], str))
    clock = _claim_with(claim_set, "clock module")
    assert f"[{clock.id}] line {clock.line}, under: Constraints" in prompt
    assert "## Constraints" not in prompt


def test_an_unsupplied_claim_id_is_dropped_from_the_citation_and_recorded():
    claim_set = _claims()
    utc = _claim_with(claim_set, "UTC")
    log = UnusableAnswerLog()

    [obligation] = synthesize(
        claim_set,
        _client(lambda ids: [_answer(claim_id=utc.id, more_claim_ids=["claim-99"])]),
        log,
    )

    assert obligation.claims == [Reference(kind="claim", id=utc.id)]
    assert [(a.stage, a.returned_id) for a in log.answers] == [(SYNTHESIS_STAGE, "claim-99")]


def test_an_obligation_citing_no_supplied_claim_is_dropped_and_recorded():
    claim_set = _claims()
    log = UnusableAnswerLog()

    obligations = synthesize(
        claim_set, _client(lambda ids: [_answer(id="invented", claim_id="claim-99")]), log
    )

    assert obligations == []
    assert any(a.returned_id == "invented" and "cites no claim" in a.reason for a in log.answers)


@pytest.mark.parametrize(
    ("kind", "evidence", "absence"),
    [
        ("requested_behavior", RequiredEvidence.CODE_AND_TESTS, False),
        ("constraint", RequiredEvidence.CODE_ONLY, False),
        ("scope_exclusion", RequiredEvidence.CODE_ONLY, True),
        ("test_deliverable", RequiredEvidence.TESTS_ONLY, False),
    ],
)
def test_the_type_settles_the_evidence_and_whether_absence_satisfies_it(kind, evidence, absence):
    claim_set = _claims()
    utc = _claim_with(claim_set, "UTC")

    [obligation] = synthesize(claim_set, _client(lambda ids: [_answer(claim_id=utc.id, type=kind)]))

    assert obligation.required_evidence is evidence
    assert obligation.satisfied_by_absence is absence
    assert bool(obligation.required_evidence_reason) is (
        evidence is not RequiredEvidence.CODE_AND_TESTS
    )


def test_repeated_ids_are_made_unique_and_slugged():
    claim_set = _claims()
    utc = _claim_with(claim_set, "UTC")

    obligations = synthesize(
        claim_set,
        _client(lambda ids: [_answer(id="Dates in UTC", claim_id=utc.id)] * 2),
    )

    assert [o.id for o in obligations] == ["dates-in-utc", "dates-in-utc-2"]


def test_no_claims_makes_no_call():
    calls: list = []
    assert synthesize(None, _client(lambda ids: [], calls)) == []
    assert calls == []


def test_the_same_answer_yields_byte_identical_obligations():
    def run():
        claim_set = _claims()
        utc = _claim_with(claim_set, "UTC")
        return canonical_json(
            [
                o.to_dict()
                for o in synthesize(claim_set, _client(lambda ids: [_answer(claim_id=utc.id)]))
            ]
        )

    assert run() == run()


# --- the obligation record ---------------------------------------------------


def test_a_synthesized_obligation_citing_no_claim_is_rejected():
    with pytest.raises(ValidationError, match="cites no claim"):
        make_obligation("o", "d", ObligationType.REQUESTED_BEHAVIOR)


def test_an_obligation_from_the_per_requirement_path_may_still_cite_none():
    assert make_obligation("o", "d", ObligationType.FUNCTIONAL).claims == []


def test_only_a_scope_exclusion_is_satisfied_by_absence():
    cite = [Reference(kind="claim", id="claim-01")]
    obligation = make_obligation("o", "d", ObligationType.FUNCTIONAL)
    base = {**obligation.to_dict(), "claims": [c.to_dict() for c in cite]}

    with pytest.raises(ValidationError, match="satisfied by absence"):
        type(obligation).model_validate({**base, "type": "scope_exclusion"})
    with pytest.raises(ValidationError, match="satisfied by absence"):
        type(obligation).model_validate(
            {**base, "type": "constraint", "satisfied_by_absence": True}
        )


# --- wiring -----------------------------------------------------------------


def test_the_pipeline_synthesizes_and_records_the_obligations(tmp_path):
    """Fails if `run_review` stops calling `synthesize` or stops storing it."""
    repo, base, head = _repo(tmp_path)
    review = run_review(
        task_text=_MANDATE,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=client_dispatching(
            {
                "_Synthesis": {
                    "obligations": [_answer(claim_id="claim-01", more_claim_ids=[])],
                }
            }
        ),
        reviewed_revision=head,
    )

    assert [o.id for o in review.synthesized_obligations] == ["dates-in-utc"]
    assert review.synthesized_obligations[0].claims == [Reference(kind="claim", id="claim-01")]
    restored = type(review).model_validate(review.to_dict())
    assert restored.synthesized_obligations == review.synthesized_obligations

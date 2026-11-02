"""Claims: verbatim, line-anchored spans of the mandate (#436).

These inject the unit-classification answer, so they test the code around the
call: how the mandate is split, how decisions become claims, what happens to a
unit the answer leaves out, and that the pipeline actually calls the step. What
the model DECIDES about real mandates is in `tests/prompts/test_claims_prompt.py`.
"""

from __future__ import annotations

import json
import subprocess

import pytest
from pydantic import ValidationError

from acceptance.change.diff import extract_change_set
from acceptance.pipeline import run_review
from acceptance.requirement.claims import UNIT_STAGE, build_claims, split_units
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import ObligationType, Reference, UnitDecision
from acceptance.serialization import canonical_json
from acceptance.supplied_ids import UnusableAnswerLog
from tests.support import (
    _fake_response,
    _supplied_enum,
    client_dispatching,
    make_obligation,
    model_client_with,
)

_MANDATE = """\
Found while looking at the export.

# Task
The export writes dates in local time today. Make it write them in UTC.
- A bullet under Task, which the parser files as unclaimed.

## Constraints
- Implement the change using the existing clock module.

## Context
The clock module was added last year.

## Acceptance
- Every exported date ends in Z.
"""


def _client(decide, calls: list | None = None):
    """A client answering unit classification with `decide(unit_id, prompt)`.

    `decide` returns a decision, or None to leave the unit out of the answer.
    """

    def completion_fn(**kwargs):
        if calls is not None:
            calls.append(kwargs)
        prompt = "\n".join(
            m["content"] for m in kwargs["messages"] if isinstance(m["content"], str)
        )
        decisions = []
        for unit_id in _supplied_enum("unit_id", **kwargs):
            decision = decide(unit_id, prompt)
            if decision is not None:
                decisions.append({"unit_id": unit_id, "reason": "r", "decision": decision})
        return _fake_response(json.dumps({"decisions": decisions}))

    return model_client_with(completion_fn)


def _all(decision):
    return _client(lambda unit_id, prompt: decision)


def _unit_with(units, fragment):
    return next(unit for unit in units if fragment in unit.span.text)


def test_every_unit_is_a_verbatim_span_with_its_line():
    parsed = parse_task_file(_MANDATE)
    units = split_units(parsed)

    assert units, "the mandate produced no units"
    for unit in units:
        assert _MANDATE[unit.span.start : unit.span.end] == unit.span.text
        assert unit.line == _MANDATE.count("\n", 0, unit.span.start) + 1
    assert [unit.span.start for unit in units] == sorted(unit.span.start for unit in units)


def test_a_paragraph_is_split_into_sentences_and_each_sentence_is_one_unit():
    units = split_units(parse_task_file(_MANDATE))

    texts = [unit.span.text for unit in units]
    assert "The export writes dates in local time today." in texts
    assert "Make it write them in UTC." in texts


def test_a_sentence_saying_two_things_is_one_unit():
    units = split_units(parse_task_file(_MANDATE))

    assert "Implement the change using the existing clock module." in [
        unit.span.text for unit in units
    ]


def test_blocks_the_parser_cannot_place_still_become_units():
    """#373: a bullet under Task, text before any heading, and text under an
    unrecognised heading are all filed as unclaimed by the parser. Each must
    still reach the decision."""
    units = split_units(parse_task_file(_MANDATE))
    texts = [unit.span.text for unit in units]

    assert "Found while looking at the export." in texts
    assert "A bullet under Task, which the parser files as unclaimed." in texts
    assert "Every exported date ends in Z." in texts
    assert "The clock module was added last year." in texts


def test_each_unit_carries_the_heading_it_sits_under():
    units = split_units(parse_task_file(_MANDATE))

    assert _unit_with(units, "Found while").heading is None
    assert _unit_with(units, "local time").heading == "Task"
    assert _unit_with(units, "clock module was added").heading == "Context"
    assert _unit_with(units, "ends in Z").heading == "Acceptance"


def test_a_unit_marked_background_yields_no_claim_and_unsure_yields_one():
    def decide(unit_id, prompt):
        units = split_units(parse_task_file(_MANDATE))
        text = next(unit.span.text for unit in units if unit.id == unit_id)
        if "local time today" in text:
            return "background"
        if "added last year" in text:
            return "unsure"
        return "feeds"

    claim_set = build_claims(parse_task_file(_MANDATE), _client(decide))
    claimed = [claim.text for claim in claim_set.claims]

    assert "The export writes dates in local time today." not in claimed
    assert "Make it write them in UTC." in claimed
    assert "The clock module was added last year." in claimed
    assert _unit_with(claim_set.units, "local time").decision is UnitDecision.BACKGROUND
    assert _unit_with(claim_set.units, "added last year").decision is UnitDecision.UNSURE


def test_a_claim_is_its_units_span_word_for_word_and_shares_its_number():
    claim_set = build_claims(parse_task_file(_MANDATE), _all("feeds"))

    assert len(claim_set.claims) == len(claim_set.units)
    by_unit = {unit.id: unit for unit in claim_set.units}
    for claim in claim_set.claims:
        unit = by_unit[claim.unit_id]
        assert claim.span == unit.span
        assert claim.line == unit.line
        assert claim.id.removeprefix("claim-") == unit.id.removeprefix("unit-")
        assert _MANDATE[claim.span.start : claim.span.end] == claim.text


def test_a_claims_id_does_not_move_when_another_units_decision_changes():
    everything = build_claims(parse_task_file(_MANDATE), _all("feeds"))
    first_dropped = build_claims(
        parse_task_file(_MANDATE),
        _client(lambda unit_id, prompt: "background" if unit_id == "unit-01" else "feeds"),
    )

    ids_before = {claim.text: claim.id for claim in everything.claims}
    for claim in first_dropped.claims:
        assert ids_before[claim.text] == claim.id


def test_a_unit_the_answer_leaves_out_feeds_claims_and_is_recorded():
    log = UnusableAnswerLog()
    claim_set = build_claims(
        parse_task_file(_MANDATE),
        _client(lambda unit_id, prompt: None if unit_id == "unit-02" else "background"),
        log,
    )

    missing = next(unit for unit in claim_set.units if unit.id == "unit-02")
    assert missing.decided is False
    assert missing.decision is UnitDecision.FEEDS
    assert [claim.unit_id for claim in claim_set.claims] == ["unit-02"]
    assert [(a.stage, a.returned_id) for a in log.answers] == [(UNIT_STAGE, "unit-02")]


def test_a_unit_decided_twice_is_background_only_if_both_answers_say_so():
    def completion_fn(**kwargs):
        ids = _supplied_enum("unit_id", **kwargs)
        decisions = [{"unit_id": i, "reason": "r", "decision": "background"} for i in ids]
        decisions.append({"unit_id": ids[0], "reason": "r2", "decision": "feeds"})
        decisions.append({"unit_id": ids[1], "reason": "r2", "decision": "background"})
        return _fake_response(json.dumps({"decisions": decisions}))

    log = UnusableAnswerLog()
    claim_set = build_claims(parse_task_file(_MANDATE), model_client_with(completion_fn), log)

    first, second = claim_set.units[0], claim_set.units[1]
    assert first.decision is UnitDecision.FEEDS and not first.decided
    assert second.decision is UnitDecision.BACKGROUND and not second.decided
    assert [claim.unit_id for claim in claim_set.claims] == [first.id]
    assert {a.returned_id for a in log.answers} == {first.id, second.id}


def test_the_call_offers_only_the_mandates_unit_ids():
    calls: list = []
    build_claims(parse_task_file(_MANDATE), _client(lambda u, p: "feeds", calls))

    assert len(calls) == 1
    units = split_units(parse_task_file(_MANDATE))
    assert _supplied_enum("unit_id", **calls[0]) == [unit.id for unit in units]


def test_a_mandate_with_no_units_makes_no_call():
    calls: list = []
    claim_set = build_claims(parse_task_file("# Task\n"), _client(lambda u, p: "feeds", calls))

    assert calls == []
    assert claim_set.units == [] and claim_set.claims == []


def test_the_same_mandate_twice_yields_byte_identical_claims():
    def once():
        decide = _client(lambda unit_id, prompt: "background" if unit_id == "unit-03" else "feeds")
        return canonical_json(build_claims(parse_task_file(_MANDATE), decide).to_dict())

    assert once() == once()


def test_an_obligation_cites_claims_and_refuses_to_cite_an_obligation_there():
    obligation = make_obligation("o", "d", ObligationType.FUNCTIONAL)
    assert obligation.claims == []

    cited = obligation.model_copy(update={"claims": [Reference(kind="claim", id="claim-02")]})
    assert type(cited).model_validate(cited.to_dict()).claims[0].id == "claim-02"

    with pytest.raises(ValidationError):
        type(obligation).model_validate(
            {**obligation.to_dict(), "claims": [{"kind": "obligation", "id": "o2"}]}
        )


# --- wiring -----------------------------------------------------------------


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


def _repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "clock.py").write_text("def now():\n    return 0\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "clock.py").write_text("def now():\n    return 1\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")
    return repo, base, _git(repo, "rev-parse", "HEAD")


def test_the_pipeline_builds_claims_and_records_them_in_review_state(tmp_path):
    """Fails if `run_review` stops calling `build_claims` or stops storing it."""
    repo, base, head = _repo(tmp_path)
    review = run_review(
        task_text=_MANDATE,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=client_dispatching({}),
        reviewed_revision=head,
    )

    assert review.claim_set is not None
    assert [unit.id for unit in review.claim_set.units] == [
        unit.id for unit in split_units(parse_task_file(_MANDATE))
    ]
    assert len(review.claim_set.claims) == len(review.claim_set.units)
    restored = type(review).model_validate(review.to_dict())
    assert restored.claim_set == review.claim_set

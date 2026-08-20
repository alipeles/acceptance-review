"""The stage-agnostic carry rule (#251, #286).

#269 built carry-forward for decomposition; #251 is the second stage to need it,
so the rule moved into `acceptance.carry` and both stages consume it. These tests
cover the rule itself, the guard that moving it changed nothing for
decomposition, and the wiring — a rule two stages are supposed to share is worth
nothing if one of them still decides for itself.
"""

from __future__ import annotations

import pytest

from acceptance.carry import Refusal, carry_key, decide
from acceptance.requirement import carry as requirement_carry
from acceptance.requirement.ledger import (
    DECOMPOSE_STAGE_LOGIC_VERSION,
    Derivation,
    LedgerEntry,
    RequirementDerivation,
)
from acceptance.requirement.ledger import carry_key as decompose_carry_key
from acceptance.review_state import (
    Disposition,
    Obligation,
    ObligationType,
    RequirementRef,
    TextSpan,
)

CONTROLS = {
    "system_prompt": "you decompose task files",
    "response_schema": {"type": "object", "properties": {"obligations": {"type": "array"}}},
    "model": "openai/gpt-5.4-mini",
    "temperature": 0.0,
    "seed": 0,
    "stage_logic_version": 1,
}

REQUIREMENT_TEXT = "A carried obligation keeps its identifier."

# Computed with #269's payload — the decompose-specific one that named
# `requirement_text` directly, before the rule moved into `acceptance.carry`.
# Pinned as a literal rather than recomputed, because a test that recomputes it
# from the code under test would agree with any change that broke it.
KEY_269 = "8e27b8094d97e9b3c1a7c3133e9c6641981198dd2b7f530d7f1b35f1e79fba01"


def test_moving_the_rule_left_the_decompose_carry_key_byte_identical():
    """The one guard `constraint-19` rests on.

    Every ledger entry already on disk holds a key computed by #269. If the
    payload shape moved, none of them would match, every requirement would be
    re-derived, and the churn this whole mechanism exists to remove would come
    back — while the feature still looked like it was working.
    """
    assert (
        decompose_carry_key(**CONTROLS, requirement_text=REQUIREMENT_TEXT)  # type: ignore[arg-type]
        == KEY_269
    )


def test_the_shared_key_spreads_a_stage_s_inputs_rather_than_nesting_them():
    """Which is *why* the decompose key survived: a stage naming
    `{"requirement_text": ...}` hashes exactly what #269 hashed."""
    assert (
        carry_key(**CONTROLS, inputs={"requirement_text": REQUIREMENT_TEXT})  # type: ignore[arg-type]
        == KEY_269
    )


def test_the_key_moves_when_the_unit_s_own_input_moves():
    assert carry_key(**CONTROLS, inputs={"requirement_text": "something else"}) != KEY_269  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "override",
    [
        {"model": "anthropic/claude-sonnet-5"},
        {"temperature": 0.7},
        {"seed": 42},
        {"stage_logic_version": 2},
        {"system_prompt": "a different instruction"},
        {"response_schema": {"type": "object", "properties": {}}},
    ],
)
def test_the_key_moves_when_any_determinism_control_moves(override):
    controls = {**CONTROLS, **override}
    assert carry_key(**controls, inputs={"requirement_text": REQUIREMENT_TEXT}) != KEY_269  # type: ignore[arg-type]


def test_a_unit_with_nothing_stored_is_not_carried():
    decision = decide("obligation-1", prior=None)

    assert not decision.carried
    assert decision.refusal is Refusal.NO_PRIOR


def test_a_unit_whose_stage_logic_moved_is_not_carried():
    decision = decide(
        "obligation-1", prior="stored", prior_key="k", current_key="k", stage_logic_matches=False
    )

    assert not decision.carried
    assert decision.refusal is Refusal.STAGE_LOGIC_MOVED


def test_a_unit_whose_request_would_differ_is_not_carried():
    decision = decide("obligation-1", prior="stored", prior_key="old", current_key="new")

    assert not decision.carried
    assert decision.refusal is Refusal.REQUEST_MOVED


def test_a_stage_can_refuse_a_carry_whose_key_still_matches():
    """The fourth check exists because only the stage can make it — decompose
    uses it for an obligation quoting text its requirement no longer has."""
    decision = decide(
        "obligation-1", prior="stored", prior_key="k", current_key="k", still_applies=False
    )

    assert not decision.carried
    assert decision.refusal is Refusal.NOT_APPLICABLE


def test_a_unit_passing_every_check_is_carried_with_its_stored_result():
    decision = decide("obligation-1", prior="stored", prior_key="k", current_key="k")

    assert decision.carried
    assert decision.refusal is None
    assert decision.prior == "stored"


def test_a_missing_prior_is_reported_as_missing_rather_than_as_a_key_mismatch():
    """Refusals are ordered most-fundamental-first, so a reader is told the
    useful thing when more than one holds."""
    decision = decide("obligation-1", prior=None, prior_key=None, current_key="new")

    assert decision.refusal is Refusal.NO_PRIOR


def _requirement() -> RequirementRef:
    return RequirementRef(
        id="constraint-01",
        section="constraint",
        ordinal=1,
        span=TextSpan(text=REQUIREMENT_TEXT, start=0, end=len(REQUIREMENT_TEXT)),
    )


def _derivation(text: str, key: str) -> RequirementDerivation:
    return RequirementDerivation(
        requirement_id="constraint-01",
        text=text,
        carry_key=key,
        derivation=Derivation.DERIVED,
        disposition=Disposition.YIELDED,
        obligations=[
            Obligation(
                id="keeps-its-identifier",
                description=text,
                type=ObligationType.FUNCTIONAL,
                importance="normal",
                explicit=True,
                observable_behavior="the identifier is unchanged",
                source_spans=[TextSpan(text=text, start=0, end=len(text))],
            )
        ],
    )


def test_decomposition_reaches_its_carry_verdict_through_the_shared_rule(monkeypatch):
    """The wiring, not the function.

    Defect injection has repeatedly found a helper with a good unit test that the
    pipeline never calls (`CLAUDE.md`). `constraint-18` says decomposition carries
    forward *through* the shared definition, so this fails if `plan_carry` goes
    back to deciding for itself — even while still producing the right answer.
    """
    calls = []
    real = requirement_carry.decide

    def spy(identity, **kwargs):
        calls.append(identity)
        return real(identity, **kwargs)

    monkeypatch.setattr(requirement_carry, "decide", spy)

    key = decompose_carry_key(**CONTROLS, requirement_text=REQUIREMENT_TEXT)  # type: ignore[arg-type]
    registry = [_requirement()]
    prior = LedgerEntry(
        run_id="abc123",
        stage_logic_version=DECOMPOSE_STAGE_LOGIC_VERSION,
        derivations=[_derivation(REQUIREMENT_TEXT, key)],
    )

    plan = requirement_carry.plan_carry(registry, prior, {"constraint-01": key})

    assert calls == ["constraint-01"]
    assert set(plan.carried) == {"constraint-01"}


def test_a_requirement_whose_key_moved_is_derived_rather_than_carried():
    """The same path, checked on its answer rather than its route: a stale key
    must still fall through to a fresh derivation."""
    registry = [_requirement()]
    prior = LedgerEntry(
        run_id="abc123",
        stage_logic_version=DECOMPOSE_STAGE_LOGIC_VERSION,
        derivations=[_derivation(REQUIREMENT_TEXT, "a-key-from-an-older-prompt")],
    )

    plan = requirement_carry.plan_carry(registry, prior, {"constraint-01": "todays-key"})

    assert not plan.carried
    assert plan.derived == ("constraint-01",)

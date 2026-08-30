"""The stage-agnostic carry rule (#251, #286).

#269 built carry-forward for decomposition; #251 is the second stage to need it,
so the rule moved into `acceptance.carry` and both stages consume it. These tests
cover the rule itself, the guard that moving it changed nothing for
decomposition, and the wiring — a rule two stages are supposed to share is worth
nothing if one of them still decides for itself.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from acceptance import carry as shared_carry
from acceptance.carry import Decision, Refusal, carry_key, decide
from acceptance.llm import UNKNOWN_STAGE
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
from tests.support import client_dispatching

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


def test_matching_a_reworded_requirement_attributes_its_model_call_to_a_stage():
    """The wiring, not the scan (#313's Gate 1).

    `plan_carry` reaches into the benchmark harness for `align_obligations` to
    tell a reworded requirement from a new one. That call named no stage, so
    every continued run whose requirement text moved grew an `unknown` row in
    its per-stage cost footer — the one bucket `llm.py` says a review-pipeline
    call site may never land in (#264). `tests/test_stage_attribution.py` scans
    for the omission statically; this drives the path that produced it, because
    a call site can pass `stage=` to a client that never records it.
    """
    reworded = "A carried obligation keeps the identifier it was given."
    registry = [
        RequirementRef(
            id="constraint-01",
            section="constraint",
            ordinal=1,
            span=TextSpan(text=reworded, start=0, end=len(reworded)),
        )
    ]
    prior = LedgerEntry(
        run_id="abc123",
        stage_logic_version=DECOMPOSE_STAGE_LOGIC_VERSION,
        derivations=[_derivation(REQUIREMENT_TEXT, "any-key")],
    )
    client = client_dispatching(
        {"_Alignment": {"matches": [{"ground_truth": "g0", "reviewer": "r0"}]}}
    )

    plan = requirement_carry.plan_carry(registry, prior, {"constraint-01": "todays-key"}, client)

    # The alignment really did run and really did match, so the assertion below
    # is about an attributed call rather than about a call that never happened.
    assert set(plan.revised) == {"constraint-01"}
    assert client.observed_calls
    assert not [call for call in client.observed_calls if call["stage"] == UNKNOWN_STAGE]


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


# A stage the rule must not know about. Split on `_` and matched as whole words,
# so `stage_logic_version` passes — the rule may speak of *a* stage generically,
# it just may not name a particular one.
STAGE_VOCABULARY = frozenset(
    {
        "requirement",
        "requirements",
        "obligation",
        "obligations",
        "criterion",
        "criteria",
        "evidence",
        "decompose",
        "decomposition",
        "coverage",
        "mapping",
        "discrimination",
        "recommendation",
        "declaration",
        "verdict",
    }
)

STAGE_PACKAGES = frozenset({"requirement", "evidence", "coverage", "change"})


def _names_a_stage(name: str) -> bool:
    return bool(set(name.lower().split("_")) & STAGE_VOCABULARY)


def test_the_shared_rule_imports_nothing_from_a_stage():
    """The rule is stated in one place that names no stage — checked first on its
    imports, because a module that reaches into `requirement/` or `evidence/` has
    a stage baked into it whatever its parameters are called."""
    tree = ast.parse(Path(shared_carry.__file__).read_text(encoding="utf-8"))

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)

    offenders = {
        module
        for module in imported
        if module.split(".")[:1] == ["acceptance"]
        and module.split(".")[1:2]
        and module.split(".")[1] in STAGE_PACKAGES
    }

    assert not offenders, f"the shared rule imports from a stage: {sorted(offenders)}"


def test_no_name_in_the_shared_rule_s_api_names_a_stage():
    """The second half of the same claim: the rule's own vocabulary. A parameter
    called `requirement_text` or a refusal called `OBLIGATION_MOVED` would put a
    stage back into the rule without any import to show for it."""
    names = {field for field in Decision.__dataclass_fields__}
    names |= {member.name for member in Refusal}
    names |= {str(member.value) for member in Refusal}
    for function in (decide, carry_key):
        names |= set(inspect.signature(function).parameters)

    offenders = {name for name in names if _names_a_stage(name)}

    assert not offenders, f"the shared rule's API names a stage: {sorted(offenders)}"

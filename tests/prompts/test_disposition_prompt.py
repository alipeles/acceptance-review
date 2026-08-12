"""Prompt-quality tests: assertions over REAL recorded model responses (#146).

Every other capability test injects a hand-authored response, so it verifies
plumbing and cannot fail when a prompt is edited (#138). These replay a
committed corpus of real model output instead, so the assertions are about what
the model actually does.

Editing a prompt changes the request, changes its hash, and therefore misses
the corpus — the test fails with a message telling you to re-record. Recording
makes live calls AND runs these assertions, so a prompt that degrades quality
fails rather than silently re-recording:

    ACCEPTANCE_RECORD=1 pytest tests/prompts -q

Recorded against archetype fixtures only: a transcript embeds the full request,
so recording a dogfood run would commit this repo's own diffs into fixtures.
"""

from pathlib import Path

import pytest

from acceptance.benchmark.fixtures import materialize_archetype
from acceptance.change.diff import extract_change_set
from acceptance.config import ScopeExpansionPolicy
from acceptance.coverage.disposition import classify_dispositions
from acceptance.coverage.prompt import DiffRef
from acceptance.coverage.unrequested import UnrequestedChange, UnrequestedChangeKind
from acceptance.review_state import Obligation, ObligationType
from tests.support import recorded_client

ARCHETYPES = Path(__file__).resolve().parents[1] / "fixtures" / "archetypes"


def _adjacent_edit_case(tmp_path: Path):
    """Archetype #8-risky-adjacent: the task asked only for `cancel_order`, but
    `ship_order` — existing, adjacent behaviour — also changed.

    `orders.py` is MODIFIED, so no deterministic fast-path claims it and the
    judgment genuinely reaches the model. (The `separable` sibling archetype
    adds a new file, which the pure-addition fast-path resolves without ever
    consulting the prompt, so it cannot test prompt quality.)
    """
    fixture = materialize_archetype(
        ARCHETYPES / "08-unrequested-change-risky-adjacent", tmp_path / "repo"
    )
    change_set = extract_change_set(fixture.repo_path, fixture.base_sha, fixture.head_sha)
    orders = next(f for f in change_set.files if f.path.endswith("orders.py"))

    obligations = [
        Obligation(
            id="cancel-order",
            description='Mark the order\'s status as "cancelled" and return True',
            type=ObligationType.FUNCTIONAL,
            importance="critical",
            explicit=True,
            observable_behavior="cancel_order sets status and returns True",
        )
    ]
    change = UnrequestedChange(
        kind=UnrequestedChangeKind.ADJACENT_BEHAVIOR,
        rationale="ship_order gained shipped_count tracking though only cancel_order was requested.",
        diff_refs=[DiffRef(file=orders.path, hunk_header=orders.hunks[0].header)],
    )
    return change, obligations, change_set


GPT_MINI = "openai/gpt-5.4-mini"
CLAUDE_SONNET = "anthropic/claude-sonnet-5"


@pytest.mark.parametrize(
    ("model", "policy", "expected"),
    [
        # Was xfailed as #152 "the policy knob never reaches the model". It was
        # not a prompt defect and not a model limitation: the harness hid the
        # enum behind a schema reference, and inlining it flipped this from
        # `separable` 3/3 to `risky` 3/3 on the same model and prompt (#158).
        (GPT_MINI, ScopeExpansionPolicy.STRICT, "risky"),
        (GPT_MINI, ScopeExpansionPolicy.LOOSE, "separable"),
        # The provider-agnosticism claim (M0.4), held to the same recorded-
        # evidence standard as every other capability. Asserting it by hand was
        # what let the harness sit OpenAI-only behind a provider-agnostic
        # dependency until #158.
        (CLAUDE_SONNET, ScopeExpansionPolicy.STRICT, "risky"),
    ],
)
def test_the_policy_knob_actually_changes_the_models_disposition(tmp_path, model, policy, expected):
    """The prompt says a STRICT policy treats an edit to existing adjacent
    behaviour as `risky`, and a LOOSE one as merely `separable`.

    Asserting the REAL model honours that is the whole point: the same diff and
    the same obligations, differing only in the policy line, must produce
    different dispositions. An injected-response test cannot check this at all —
    it would be asserting the answer the test itself supplied.

    STRICT/risky is archetype #8-risky-adjacent's ground truth.
    """
    change, obligations, change_set = _adjacent_edit_case(tmp_path)

    result = classify_dispositions(
        [change], obligations, [], change_set, policy, recorded_client(model)
    )[0]

    assert result.decided_by == "model"  # no fast-path claimed it
    assert result.disposition.value == expected

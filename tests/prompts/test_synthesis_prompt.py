"""Prompt-quality tests for synthesis (#437), over REAL responses.

`tests/requirement/test_synthesis.py` injects the answer, so it cannot fail when
the prompt is edited. These replay the committed corpus, so they assert what the
model actually synthesizes. Re-record with:

    ACCEPTANCE_RECORD=1 pytest tests/prompts/test_synthesis_prompt.py -q

Each mandate runs claims then synthesis, as the pipeline does. Three are under
`tests/fixtures/synthesis/`, one per behaviour #437's Acceptance names; the
fourth is `tests/fixtures/claims/unrecognised-headings.md`, which stands in for
#432's issue body as filed (the corpus never records this repository's own text).
"""

from __future__ import annotations

import pathlib

import pytest

from acceptance.requirement.claims import build_claims
from acceptance.requirement.synthesis import synthesize
from acceptance.requirement.task_file import parse_task_file
from acceptance.review_state import ObligationType
from tests.support import recorded_client

_FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"


def _synthesize(path: str):
    text = (_FIXTURES / path).read_text(encoding="utf-8")
    client = recorded_client()
    claim_set = build_claims(parse_task_file(text), client)
    return text, claim_set, synthesize(claim_set, client)


@pytest.fixture(scope="module")
def one_claim_two_things():
    return _synthesize("synthesis/one-claim-two-things.md")


@pytest.fixture(scope="module")
def two_claims_one_behaviour():
    return _synthesize("synthesis/two-claims-one-behaviour.md")


@pytest.fixture(scope="module")
def crud():
    return _synthesize("synthesis/crud.md")


@pytest.fixture(scope="module")
def unrecognised_headings():
    return _synthesize("claims/unrecognised-headings.md")


def _cited(obligation) -> set[str]:
    return {reference.id for reference in obligation.claims}


def _claim_with(claim_set, fragment: str):
    return next(claim for claim in claim_set.claims if fragment in claim.text)


def test_a_claim_saying_two_things_yields_a_behaviour_and_a_constraint(one_claim_two_things):
    _, claim_set, obligations = one_claim_two_things
    claim = _claim_with(claim_set, "report writer")
    citing = [o for o in obligations if claim.id in _cited(o)]
    types = {o.type for o in citing}

    assert ObligationType.REQUESTED_BEHAVIOR in types, [(o.type, o.description) for o in citing]
    assert ObligationType.CONSTRAINT in types, [(o.type, o.description) for o in citing]
    [constraint] = [o for o in citing if o.type is ObligationType.CONSTRAINT]
    assert "report writer" in constraint.description.lower()


def test_two_claims_about_one_behaviour_yield_one_obligation_citing_both(
    two_claims_one_behaviour,
):
    _, claim_set, obligations = two_claims_one_behaviour
    task = _claim_with(claim_set, "reset a forgotten password")
    acceptance = _claim_with(claim_set, "can reset it")

    both = [o for o in obligations if {task.id, acceptance.id} <= _cited(o)]
    assert len(both) == 1, [(o.id, sorted(_cited(o))) for o in obligations]
    only_one = [o for o in obligations if len(_cited(o) & {task.id, acceptance.id}) == 1]
    assert not only_one, [(o.id, o.description) for o in only_one]


def test_a_crud_interface_entails_delete_stated_with_no_question(crud):
    _, claim_set, obligations = crud
    claim = _claim_with(claim_set, "CRUD")
    deletes = [o for o in obligations if "delet" in o.description.lower()]

    assert len(deletes) == 1, [o.description for o in obligations]
    [delete] = deletes
    assert _cited(delete) == {claim.id}
    assert delete.provenance == "stated"
    assert delete.type is ObligationType.REQUESTED_BEHAVIOR


def _acceptance_bullets(text: str) -> list[tuple[int, int]]:
    """(start, end) offsets of each bullet under `## Acceptance`."""
    start = text.index("## Acceptance")
    bullets = []
    offset = start
    for line in text[start:].splitlines(keepends=True):
        if line.startswith("- "):
            bullets.append((offset, offset + len(line.rstrip("\n"))))
        offset += len(line)
    return bullets


def test_every_acceptance_bullet_under_an_unrecognised_heading_yields_an_obligation(
    unrecognised_headings,
):
    text, claim_set, obligations = unrecognised_headings
    cited = set().union(*(_cited(o) for o in obligations)) if obligations else set()
    bullets = _acceptance_bullets(text)

    assert len(bullets) == 4
    for start, end in bullets:
        inside = {c.id for c in claim_set.claims if start <= c.span.start and c.span.end <= end}
        assert inside & cited, f"no obligation cites Acceptance bullet: {text[start:end]!r}"


def test_every_obligation_cites_a_claim_of_its_own_mandate(
    one_claim_two_things, two_claims_one_behaviour, crud, unrecognised_headings
):
    for _, claim_set, obligations in (
        one_claim_two_things,
        two_claims_one_behaviour,
        crud,
        unrecognised_headings,
    ):
        ids = {claim.id for claim in claim_set.claims}
        assert obligations
        for obligation in obligations:
            assert obligation.claims and _cited(obligation) <= ids

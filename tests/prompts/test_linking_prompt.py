"""Prompt-quality tests for obligation linking (#144), over REAL responses.

`tests/requirement/test_linking.py` supplies the links and asserts what the code
does with them. That is the right test for the merge, and no test for the
judgement: a fixture that states "these two are duplicates" and then checks they
were merged is asserting itself.

These replay a committed corpus instead, so the assertions are about what the
model actually decides. Re-record with:

    ACCEPTANCE_RECORD=1 pytest tests/prompts/test_linking_prompt.py -q

The task file is about exporting invoices, deliberately. #204 measured that a
control task file on unrelated subject matter reproduced a decomposition defect
exactly, which is what ruled out dogfood contamination as the cause — and a
transcript embeds its whole request, so recording against this repo's own task
files would commit its diffs into fixtures.
"""

from __future__ import annotations

import pytest

from acceptance.requirement.linking import link_duplicate_obligations
from acceptance.requirement.obligations import decompose
from acceptance.requirement.task_file import parse_task_file
from tests.support import recorded_client

# Three properties in one file, so one recording covers all of them:
#
#   * The Task prose and `constraint-01` demand the SAME behaviour — the header
#     row — in two sections. That is the true duplicate this issue exists for.
#   * `completion-01` asks for a TEST of that behaviour. Not the same
#     requirement: code that already writes the header row with nobody having
#     written the test satisfies one and violates the other.
#   * `constraint-02` shares vocabulary with `constraint-01` ("row") while
#     demanding something different — the over-merge trap.
#   * `constraint-02` carries a trailing reason clause. The reason is not a
#     second requirement.
#   * `constraint-04` (formatting) beside `constraint-05` (the library) is the
#     behaviour-versus-technology trap.
_TASK = """# Task
Export invoices to a CSV file. The export writes a header row naming every
column.

## Constraints
- The export writes a header row naming every column.
- The export writes one row per invoice, so a reader can count invoices without
  parsing any amounts.
- The export escapes embedded commas in the customer name.
- The amount column is written with exactly two decimal places.
- The file is produced with Python's standard-library csv module.

## Completion expectations
- A test asserts that the export writes a header row naming every column.
- A test asserts that an embedded comma in the customer name is escaped.
"""


@pytest.fixture(scope="module")
def linked():
    client = recorded_client()
    derived = decompose(parse_task_file(_TASK), client)
    return derived, link_duplicate_obligations(derived, client)


def _obligations_of(decomposition, requirement_id: str) -> list[str]:
    disposition = decomposition.requirement_map.disposition_for(requirement_id)
    return list(disposition.obligation_ids) if disposition else []


def test_one_behaviour_demanded_in_two_sections_ends_on_one_obligation(linked):
    """The headline judgement. The Task prose and `constraint-01` demand the same
    thing — a header row naming every column — so they are one requirement stated
    twice, and the surviving obligation is named by both."""
    _, after = linked

    prose = _obligations_of(after, "task-01")
    constraint = _obligations_of(after, "constraint-01")

    assert prose and constraint
    assert set(prose) & set(constraint)


def test_a_behaviour_and_a_requirement_to_test_it_are_not_merged(linked):
    """`constraint-01` demands the header row; `completion-01` demands a test of
    it. Code that already writes the header row, with nobody having written the
    test, satisfies one and violates the other — so they are different
    requirements, and adding each is separate work.

    This case used to be listed in the prompt as one that SHOULD merge, which
    contradicted the prompt's own criterion. Flipping it is what this asserts."""
    _, after = linked

    behaviour = _obligations_of(after, "constraint-01")
    its_test = _obligations_of(after, "completion-01")

    assert behaviour and its_test
    assert set(behaviour).isdisjoint(its_test)


def test_two_requirements_sharing_vocabulary_are_not_merged(linked):
    """The over-merge trap. `constraint-01` and `constraint-02` are both about
    rows in the same CSV export; they demand different things, and merging them
    would destroy one requirement silently — the failure this product exists to
    catch, so the bias toward under-merging has to hold here."""
    _, after = linked

    header_row = _obligations_of(after, "constraint-01")
    one_row_each = _obligations_of(after, "constraint-02")

    assert header_row and one_row_each
    assert set(header_row).isdisjoint(one_row_each)


def test_a_requirement_and_its_reason_clause_are_one_requirement(linked):
    """`constraint-02` is a demand followed by the reason for it. The reason is
    not separately checkable, so it must not become a second obligation."""
    _, after = linked

    assert len(_obligations_of(after, "constraint-02")) == 1


def test_linking_reduces_the_obligation_count_it_was_given(linked):
    """Stage 1 and stage 2 are separately observable, and the pass did work."""
    before, after = linked

    assert len(after.obligations) < len(before.obligations)


def test_every_requirement_still_names_an_obligation_after_linking(linked):
    """A merge must never leave a requirement holding nothing — that is the
    lossy failure DR-204 moved out of derivation, and it must not reappear."""
    _, after = linked

    for disposition in after.requirement_map.dispositions:
        if disposition.disposition.value == "yielded":
            assert disposition.obligation_ids, disposition.requirement_id


def test_a_behavior_and_the_technology_implementing_it_are_not_merged(linked):
    """The over-merge observed on this repo's own task file at #144 Gate 2 run 1:
    "the links are typed fields" was merged with "typed schemas are pydantic
    models" — a demanded behavior and the library used to express it.

    `constraint-04` (two decimal places) and `constraint-05` (the csv module) are
    that shape. Either can hold while the other fails, and no single test shows
    both, so the sameness criterion must keep them apart."""
    _, after = linked

    formatting = _obligations_of(after, "constraint-04")
    library = _obligations_of(after, "constraint-05")

    assert formatting and library
    assert set(formatting).isdisjoint(library)

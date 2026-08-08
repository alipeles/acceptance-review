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
#   * `constraint-01` and `completion-01` state ONE requirement (the header row)
#     in two sections — the case this issue exists for.
#   * `constraint-02` shares vocabulary with `constraint-01` ("row") while
#     demanding something different — the over-merge trap.
#   * `constraint-02` carries a trailing reason clause. The reason is not a
#     second requirement.
_TASK = """# Task
Export invoices to a CSV file.

## Constraints
- The export writes a header row naming every column.
- The export writes one row per invoice, so a reader can count invoices without
  parsing any amounts.
- The export escapes embedded commas in the customer name.

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


def test_one_requirement_stated_in_two_sections_ends_on_one_obligation(linked):
    """The headline judgement: a constraint and the acceptance criterion that
    restates it are one requirement, and the model recognises it."""
    _, after = linked

    constraint = _obligations_of(after, "constraint-01")
    completion = _obligations_of(after, "completion-01")

    assert constraint and completion
    assert constraint == completion


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

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
from acceptance.review_state import ObligationType
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


def test_one_behaviour_demanded_in_two_sections_yields_one_obligation(linked):
    """The headline judgement, and #317 moved where it is made.

    The Task prose and `constraint-01` demand the same thing — a header row
    naming every column. That used to produce two obligations which linking then
    merged, so the survivor was named by both requirements. Now the summary step
    decides the paragraph span by span against the obligations the bullets
    already produced, finds that span already required, and derives no duplicate
    at all.

    So the assertion is on the outcome rather than on the merge: exactly one
    obligation in the whole set demands the header row, and the summary's
    disposition records that its span was already required and by what. A
    duplicate that is never created cannot be lost by a merge that misfires,
    which is the failure `#242` and `#304` are about.
    """
    _, after = linked

    by_id = {obligation.id: obligation for obligation in after.obligations}
    # Behaviour obligations only. `completion-01` demands a TEST of the header
    # row, which is a different requirement and must stay separate — the very
    # thing `test_a_behaviour_and_a_requirement_to_test_it_are_not_merged`
    # asserts, so counting it here would contradict that test.
    header_row = [
        obligation
        for obligation in after.obligations
        if "header row" in obligation.description.lower()
        and obligation.type is not ObligationType.TEST_DEMAND
    ]
    assert len(header_row) == 1, [o.description for o in header_row]

    # It belongs to the bullet, and the Task prose does not restate it.
    assert header_row[0].id in _obligations_of(after, "constraint-01")
    assert header_row[0].id not in _obligations_of(after, "task-01")

    # And the summary says why it derived nothing for that span, rather than
    # simply being silent about it.
    summary = after.requirement_map.disposition_for("task-01")
    assert summary is not None and summary.reason
    assert "already required by" in summary.reason
    assert header_row[0].id in summary.reason
    # The Task prose still yields what only IT states, so this is not the
    # paragraph being silenced.
    assert _obligations_of(after, "task-01")
    assert all("csv" in by_id[i].description.lower() for i in _obligations_of(after, "task-01"))


def test_a_behaviour_and_a_requirement_to_test_it_are_not_merged(linked):
    """`constraint-01` demands the header row; `completion-01` demands a test of
    it. Code that already writes the header row, with nobody having written the
    test, satisfies one and violates the other — so they are different
    requirements, and adding each is separate work.

    This case used to be listed in the prompt as one that SHOULD merge, which
    contradicted the prompt's own criterion. Flipping it is what this asserts.

    Disjointness alone is a weak assertion, and #232 is why: it passes whenever
    linking merges nothing at all. This bundle's Gate 1 run 2 produced exactly
    that — an 8-obligation transitive clique was contradicted, so #144's clique
    rule suppressed every merge in it, and the pair came back disjoint while
    both obligations had lost the distinction the test is named after. So also
    assert the framing is still there for linking to key on."""
    _, after = linked

    behaviour = _obligations_of(after, "constraint-01")
    its_test = _obligations_of(after, "completion-01")

    assert behaviour and its_test
    assert set(behaviour).isdisjoint(its_test)

    by_id = {obligation.id: obligation for obligation in after.obligations}
    assert any(by_id[i].type is ObligationType.TEST_DEMAND for i in its_test), (
        "completion-01 demands a TEST; nothing survived typed test_demand, so "
        f"the non-merger above is not evidence: {[by_id[i].type for i in its_test]}"
    )


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


def test_linking_swept_every_pair_and_found_nothing_to_merge(linked):
    """Stage 1 and stage 2 are separately observable, and the pass ran.

    This used to assert the count DROPPED, because derivation reliably handed
    linking a cross-section duplicate to merge. Since #317 it does not: the
    summary step finds the Task prose's header-row span already required and
    derives no second obligation for it, so on this fixture there is nothing left
    to merge and a count drop would mean linking had merged two obligations that
    are not the same requirement — the silent-destruction failure this stage errs
    against.

    So assert the pass did its work rather than that it changed the answer: every
    pair was judged, and every judgement was `not the same requirement`. A pass
    that returned early, or that was never called, produces no verdicts at all
    and fails here.
    """
    before, after = linked

    assert len(after.obligations) == len(before.obligations)
    assert after.merge_decisions, "the linking sweep recorded no judgement at all"
    assert not any(decision.same_requirement for decision in after.merge_decisions)
    # A complete sweep over N obligations is N*(N-1)/2 pairs, minus the pairs
    # settled in code — a `test_demand` obligation beside a behaviour one cannot
    # merge, so it is never asked about (DR-232).
    assert len(after.merge_decisions) > len(after.obligations)


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

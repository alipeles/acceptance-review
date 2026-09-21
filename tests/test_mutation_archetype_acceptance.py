"""#45's Acceptance, against the real archetype rather than a miniature of it.

`tests/fixtures/archetypes/03-superficial-test` is the amortization case: the
function is implemented correctly and its only test asserts that the schedule is
a list of the right length with positive values, never the payment amounts. Its
`labels.json` already records, per defect, which tests kill it — two with an
empty list and one naming the test. That is human-authored ground truth for
exactly what this stage must observe.

**Both outcomes are required, and that is why this fixture was chosen.** A
runner that reported survival for everything would satisfy the two empty lists
and fail the third. A runner that reported a kill for everything would do the
opposite.

What is stubbed and what is not: the descriptor stage's *judgement* is supplied
here, because asking a model for it needs a recorded transcript and the prompt's
quality is a separate question. Everything else is real — the region resolution,
the four validity checks, the copy, the sandboxed pytest run, and the reading of
its outcomes.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from acceptance.benchmark.fixtures import materialize_archetype
from acceptance.change.diff import extract_change_set
from acceptance.evidence_tier import EvidenceTier
from acceptance.mutation.attempt import MutationDescriptor, MutationOutcomeKind
from acceptance.mutation.baseline import establish_baseline
from acceptance.mutation.runner import run_mutations
from acceptance.mutation.verdicts import pairs_not_worth_asking, verdicts_from
from acceptance.review_state import Defect, DefectSet, DefectType

FIXTURE = Path(__file__).parent / "fixtures" / "archetypes" / "03-superficial-test"

TEST_ID = "test_loan.py::test_returns_a_payment_for_each_month"

#: The edit that makes each labelled defect true, by its id. Each replaces one
#: line of `head/loan.py`, whose body is:
#:
#:   1 def amortize(principal, annual_rate, months):
#:   2     monthly_rate = annual_rate / 12
#:   3     if monthly_rate == 0:
#:   4         payment = principal / months
#:   5     else:
#:   6         payment = principal * monthly_rate / (1 - (1 + monthly_rate) ** -months)
#:   7     return [round(payment, 2) for _ in range(months)]
_EDITS = {
    # "varies the payment from month to month instead of equal payments"
    "d-payments-not-equal": (7, 7, "    return [round(payment + i, 2) for i in range(months)]\n"),
    # "one entry fewer than the number of months requested"
    "d-one-entry-short": (7, 7, "    return [round(payment, 2) for _ in range(months - 1)]\n"),
    # "principal divided by months, ignoring interest entirely"
    "d-interest-ignored": (6, 6, "        payment = principal / months\n"),
}


@pytest.fixture(scope="module")
def labels() -> dict:
    return json.loads((FIXTURE / "labels.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ground_truth(labels) -> dict[str, list[str]]:
    """Each labelled defect's killing tests, as recorded by hand."""
    return {defect["id"]: defect["killed_by"] for defect in labels["defects"]}


@pytest.fixture(scope="module")
def materialized(tmp_path_factory):
    return materialize_archetype(FIXTURE, tmp_path_factory.mktemp("archetype") / "repo")


@pytest.fixture(scope="module")
def change_set(materialized):
    return extract_change_set(materialized.repo_path, materialized.base_sha, materialized.head_sha)


@pytest.fixture(scope="module")
def defect_sets(labels, change_set) -> list[DefectSet]:
    """The labelled defects, pointed at the changed region of `loan.py`.

    The enumeration stage is not run: this test is about whether injection
    reproduces the ground truth, and enumerating the defects with a model first
    would make a failure ambiguous between the two stages.
    """
    label = next(
        f"{file.path}#{index}"
        for file in change_set.files
        if file.path == "loan.py"
        for index in range(len(file.hunks))
    )
    return [
        DefectSet(
            obligation_id="equal-payments",
            defects=[
                Defect(
                    id=entry["id"],
                    obligation_id="equal-payments",
                    type=DefectType.OTHER,
                    description=entry["description"],
                    code_refs=[label],
                )
                for entry in labels["defects"]
            ],
        )
    ]


def _build(defect, regions, _sources) -> MutationDescriptor | None:
    start, end, replacement = _EDITS[defect.id]
    return MutationDescriptor(
        path="loan.py",
        start_line=start,
        end_line=end,
        replacement=replacement,
        region_label=regions[0].label,
    )


@pytest.fixture(scope="module")
def attempts(materialized, change_set, defect_sets):
    baseline = establish_baseline([TEST_ID], materialized.repo_path)
    assert baseline.usable_tests == [TEST_ID], baseline.set_aside
    return run_mutations(defect_sets, change_set, materialized.repo_path, baseline, _build)


@pytest.fixture(scope="module")
def by_id(attempts) -> dict:
    return {attempt.defect_id: attempt for attempt in attempts}


class TestTheGroundTruthIsReproduced:
    def test_every_labelled_defect_got_an_attempt(self, by_id, ground_truth):
        assert set(by_id) == set(ground_truth)

    def test_every_attempt_was_observed_by_execution(self, by_id):
        """None of the three is `not_mutable` or `not_attempted`. If one were,
        the comparison below would be vacuous for it."""
        assert all(attempt.observed for attempt in by_id.values())

    @pytest.mark.parametrize(
        "defect_id", ["d-payments-not-equal", "d-one-entry-short", "d-interest-ignored"]
    )
    def test_the_killing_tests_match_the_labels(self, by_id, ground_truth, defect_id):
        assert by_id[defect_id].killing_tests == ground_truth[defect_id]


class TestTheUpgradeThisMilestoneExistsFor:
    def test_a_defect_the_test_cannot_catch_is_observed_to_survive(self, by_id):
        """The static "this assertion looks non-discriminating" becoming "the
        payment formula was broken and the mapped test stayed green" — §13.5
        scenario 14, and the reason M8.4 exists."""
        attempt = by_id["d-interest-ignored"]
        assert attempt.outcome is MutationOutcomeKind.SURVIVED
        assert attempt.tests_run == [TEST_ID]

    def test_the_defect_the_test_can_catch_is_observed_to_die(self, by_id):
        """The control. Without it a runner that reported survival for
        everything would pass every other assertion here."""
        attempt = by_id["d-one-entry-short"]
        assert attempt.outcome is MutationOutcomeKind.KILLED
        assert attempt.killing_tests == [TEST_ID]

    def test_the_injected_edit_is_recorded_for_each(self, by_id):
        for attempt in by_id.values():
            assert attempt.descriptor is not None
            assert attempt.descriptor.replacement.strip()

    def test_the_verdicts_reach_the_executed_tier_once_the_edits_are_verified(
        self, attempts, defect_sets
    ):
        """The edits here were written by hand to match each labelled defect,
        so they stand in for a passed verification."""
        verified = [attempt.model_copy(update={"verified": True}) for attempt in attempts]
        verdicts = verdicts_from(verified, defect_sets)
        assert len(verdicts) == 3
        assert all(v.tier is EvidenceTier.DEFECT_KILLED for v in verdicts)
        assert [v.defect_id for v in verdicts if v.kills] == ["d-one-entry-short"]

    def test_without_verification_nothing_reaches_the_executed_tier(self, attempts, defect_sets):
        assert verdicts_from(attempts, defect_sets) == []
        assert all(attempt.tier is EvidenceTier.STATIC for attempt in attempts)


class TestRoutingChangesNothingHereButTheCost:
    """#340's archetype acceptance, against the same hand-authored ground truth.

    This fixture is the one place the routing decision can be checked against
    labels a person wrote. Its shape is also the awkward case: of three labelled
    defects only `d-one-entry-short` is killed at all, and it is killed by the
    fixture's single candidate test — so that defect has no passing test to hold
    back, and the two survivors hold nothing back either. Routing is therefore a
    no-op here, and saying so is the assertion: the saving must not come at the
    price of moving a result on a case whose answer is known.
    """

    def test_routing_holds_nothing_back_on_this_fixture(self, attempts):
        """Every defect is either a survival, which skips nothing by rule, or a
        kill whose only candidate test is the killing one."""
        assert pairs_not_worth_asking(attempts) == {}

    def test_the_labelled_kill_is_untouched(self, by_id, ground_truth):
        """#340 asks for this by name: `d-one-entry-short` is still shown killed
        by the test the labels name, with routing in force."""
        attempt = by_id["d-one-entry-short"]
        assert attempt.killing_tests == ground_truth["d-one-entry-short"]
        assert attempt.defect_id not in {
            defect_id for defect_id, _ in pairs_not_worth_asking(attempts_of(by_id))
        }

    def test_a_survivor_holds_nothing_back_even_with_a_passing_test(self, by_id):
        """The rule that makes the no-op above a guarantee rather than an
        accident of this fixture's single test. Both survivors ran the candidate
        test and it passed; an edit nothing failed under still skips nothing."""
        survivors = [a for a in by_id.values() if a.outcome is MutationOutcomeKind.SURVIVED]
        assert survivors, "the fixture must carry survivors, or this asserts nothing"
        assert all(a.tests_run for a in survivors)
        assert pairs_not_worth_asking(survivors) == {}


def attempts_of(by_id) -> list:
    return list(by_id.values())

"""An unverified mutation attempt cannot reach a rating, a class, or a prescription.

The standing boundary this file enforces, stated once: **a result observed by
running tests against an injected edit is evidence only if something verified
that the edit made the named defect true.** Measured on #45's own review, about
half the edits did not — they repaired a defect the code already had, changed
something other than the defect, or broke far more than it. An unverified result
is therefore recorded and reported, and nothing else.

`MutationAttempt.settled` is the gate, and `verdicts_from` is the one place it is
consulted. That is exactly the shape CLAUDE.md warns about: a correct one-line
property that every guarantee depends on the rest of the pipeline honouring. So
these assertions do not test the property. They test the three things that must
never see an unverified attempt:

- the **evidence class** and the **achieved tier** a criterion is rated at
  (`defects/support.py::derive_support`),
- the **prescriptions** the recommendation stage writes
  (`defects/support.py::uncovered_defects`, that stage's whole input),
- the **static pair judgement**, which must not be anchored on a result that is
  wrong half the time — *not even as a hint*.

All three take one `list[PairVerdict]`, so the structural guarantee is that an
unverified attempt contributes no verdict. The last group runs through
`run_review` and looks at what the model was actually given.
"""

from __future__ import annotations

import subprocess

import pytest

from acceptance.change.diff import extract_change_set
from acceptance.defects.support import derive_support, uncovered_defects
from acceptance.evidence_tier import EvidenceTier
from acceptance.mutation.attempt import (
    MutationAttempt,
    MutationDescriptor,
    MutationOutcomeKind,
)
from acceptance.mutation.settings import ExecutionSettings
from acceptance.mutation.verdicts import remaining_defect_sets, verdicts_from
from acceptance.pipeline import run_review
from acceptance.report import render_report
from acceptance.review_state import (
    Defect,
    DefectSet,
    DefectType,
    Obligation,
    ObligationType,
)
from tests.support import client_dispatching

# --- the chokepoint ---------------------------------------------------------

_EDIT = MutationDescriptor(
    path="loan.py",
    start_line=2,
    end_line=2,
    replacement="    payment = principal / months * 3\n",
    region_label="loan.py#0",
    original="    payment = principal / months\n",
)


def _sets(*defect_ids: str) -> list[DefectSet]:
    return [
        DefectSet(
            obligation_id="o1",
            defects=[
                Defect(
                    id=defect_id,
                    obligation_id="o1",
                    type=DefectType.OTHER,
                    description=f"description of {defect_id}",
                )
                for defect_id in defect_ids
            ],
        )
    ]


def _obligation() -> Obligation:
    return Obligation(
        id="o1",
        description="d",
        type=ObligationType.FUNCTIONAL,
        importance="normal",
        explicit=True,
        observable_behavior="b",
    )


def _attempt(outcome: MutationOutcomeKind, *, verified: bool) -> MutationAttempt:
    observed = outcome in {MutationOutcomeKind.KILLED, MutationOutcomeKind.SURVIVED}
    return MutationAttempt(
        defect_id="d1",
        outcome=outcome,
        descriptor=_EDIT if observed else None,
        tests_run=["t::a", "t::b"] if observed else [],
        killing_tests=["t::a"] if outcome is MutationOutcomeKind.KILLED else [],
        reason="" if observed else "no span to replace",
        verified=verified,
    )


_UNVERIFIED = [
    pytest.param(MutationOutcomeKind.KILLED, id="an unverified kill"),
    pytest.param(MutationOutcomeKind.SURVIVED, id="an unverified survival"),
    pytest.param(MutationOutcomeKind.NOT_MUTABLE, id="no edit could be built"),
    pytest.param(MutationOutcomeKind.NOT_ATTEMPTED, id="nothing was run"),
    pytest.param(MutationOutcomeKind.ALREADY_PRESENT, id="the code already has it"),
    pytest.param(MutationOutcomeKind.NOT_A_CODE_PROPERTY, id="not about any code"),
]


@pytest.mark.parametrize("outcome", _UNVERIFIED)
def test_an_unverified_attempt_contributes_no_verdict(outcome):
    """The structural guarantee the rest of this file rests on: the record the
    rating, the class and the prescriptions all read gains nothing from it."""
    assert verdicts_from([_attempt(outcome, verified=False)], _sets("d1")) == []


def test_a_verified_attempt_does_contribute_verdicts():
    """The control. Without it every assertion above would pass on a
    `verdicts_from` that returned nothing at all."""
    verdicts = verdicts_from([_attempt(MutationOutcomeKind.KILLED, verified=True)], _sets("d1"))
    assert [v.test_id for v in verdicts] == ["t::a", "t::b"]
    assert all(v.tier is EvidenceTier.DEFECT_KILLED for v in verdicts)


# --- the three consumers ----------------------------------------------------


@pytest.mark.parametrize("outcome", _UNVERIFIED)
class TestNothingDerivesFromIt:
    """Each assertion compares the review WITH the unverified attempt against a
    review that ran no execution at all. Equal is the requirement: an unverified
    result must be inert, not merely weighted down."""

    def _both(self, outcome):
        attempts = [_attempt(outcome, verified=False)]
        return verdicts_from(attempts, _sets("d1")), attempts

    def test_the_evidence_class_is_unchanged(self, outcome):
        executed, _ = self._both(outcome)
        with_it = derive_support([_obligation()], _sets("d1"), executed, [])
        without = derive_support([_obligation()], _sets("d1"), [], [])
        assert with_it[0].evidence_class == without[0].evidence_class

    def test_the_rating_stays_at_the_static_tier(self, outcome):
        executed, _ = self._both(outcome)
        (result,) = derive_support([_obligation()], _sets("d1"), executed, [])
        assert result.achieved_tier is EvidenceTier.STATIC

    def test_no_test_is_credited_to_the_criterion(self, outcome):
        """A test named by an unverified kill must not appear as evidence."""
        executed, _ = self._both(outcome)
        (result,) = derive_support([_obligation()], _sets("d1"), executed, [])
        assert result.test_links == []
        assert result.covered == 0

    def test_the_defect_still_owes_a_prescription(self, outcome):
        """The recommendation stage's whole input. A defect an unverified kill
        'covered' would silently lose its recommended test."""
        executed, _ = self._both(outcome)
        assert uncovered_defects(_sets("d1"), executed) == [("o1", "d1")]

    def test_the_defect_still_reaches_the_static_judge(self, outcome):
        _, attempts = self._both(outcome)
        remaining = remaining_defect_sets(attempts, _sets("d1"))
        assert [d.id for d in remaining[0].defects] == ["d1"]


# --- through the pipeline ---------------------------------------------------

_TASK = (
    "# Task\nThe schedule pays the loan off in equal monthly payments.\n\n"
    "## Constraints\n- Every monthly payment is the same amount\n"
)
_BASE = "def amortize(principal, months):\n    raise NotImplementedError\n"
_HEAD = (
    "def amortize(principal, months):\n"
    "    payment = principal / months\n"
    "    return [payment for _ in range(months)]\n"
)
_TEST = (
    "from loan import amortize\n\n\n"
    "def test_returns_a_payment_for_each_month():\n"
    "    schedule = amortize(1200.0, 12)\n"
    "    assert len(schedule) == 12\n"
)

#: The edit drops a month from the schedule, which the test DOES assert about,
#: so the run observes a kill. Nothing verifies it.
#:
#: A kill rather than a survival, deliberately: an unverified kill is the case
#: that inflates a rating, because a covered defect takes the strongest tier
#: among the verdicts that kill it. An unverified survival leaves the defect
#: uncovered, and an uncovered defect takes the weakest tier across all its
#: verdicts — so it cannot inflate anything, and a fixture built on one passes
#: these assertions even with the gate removed. I verified that too.
_JUDGMENTS = {
    "_Decomposition": {
        "obligations": [
            {
                "id": "equal-payments",
                "description": "Every monthly payment is the same amount",
                "type": "functional",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "amortize returns equal payments",
                "source_quote": "Every monthly payment is the same amount",
            }
        ],
        "open_questions": [],
        "requirement_dispositions": [
            {
                "requirement_id": "task-01",
                "disposition": "no_obligation",
                "reason": "Restates the constraint below.",
            },
            {
                "requirement_id": "constraint-01",
                "disposition": "yielded",
                "obligation_id": "equal-payments",
                "more_obligation_ids": [],
            },
        ],
    },
    "_Enumeration": {
        "obligation_id": "equal-payments",
        "defects": [
            {
                "slug": "wrong-payment-amount",
                "expected_behavior": "each payment repays an equal share",
                "defective_behavior": "the payment amount is tripled",
                "type": "other",
                "description": "The payment amount is wrong.",
                "code_refs": ["loan.py#0"],
            }
        ],
        "reason": "",
    },
    "_Descriptor": {
        "code_currently_does": "expected",
        "region_label": "loan.py#0",
        "start_line": 3,
        "end_line": 3,
        "replacement": "    return [payment for _ in range(months - 1)]\n",
        "decline": "none",
        "reason": "",
    },
    # The static judge answers, and says the test does not catch the defect.
    # Load-bearing for the comparison below: with no answer here the pair is
    # recorded unanswered, which pins the criterion at `indeterminate` and the
    # static tier whatever execution produced — so the comparison would pass
    # even with the gate removed. I verified that, and it is why this is here.
    "_PairVerdicts": {
        "tests": [
            {
                "test_id": "test_loan.py::test_returns_a_payment_for_each_month",
                "defects": [{"defect_id": "equal-payments/wrong-payment-amount", "fails": False}],
            }
        ]
    },
    # Verification runs -- the tier runs only when it is on -- and REFUSES this
    # edit. That is what makes an observed-but-unverified result reachable
    # through the pipeline at all, since `decide_execution` declines the run
    # when verification is off.
    "_Verification": {
        "before_does": "expected",
        "after_does": "other",
        "reason": "the edit changes nothing the defect names",
    },
    "_Coverage": {
        "classifications": [
            {
                "obligation_id": "equal-payments",
                "status": "addressed",
                "rationale": "loan.py implements it.",
                "diff_refs": [],
            }
        ]
    },
}


def _git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "loan.py").write_text(_BASE)
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "base")
    base = _git(root, "rev-parse", "HEAD")
    (root / "loan.py").write_text(_HEAD)
    (root / "test_loan.py").write_text(_TEST)
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "head")
    return root, base, _git(root, "rev-parse", "HEAD")


_VERIFIED = {
    **_JUDGMENTS,
    "_Verification": {
        "before_does": "expected",
        "after_does": "defective",
        "reason": "line 3 now returns one entry fewer",
    },
}


def _review(repo, *, execution, capture=None, judgments=None):
    root, base, head = repo
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(root, base, head),
        repo=root,
        client=client_dispatching(judgments or _JUDGMENTS, capture=capture),
        reviewed_revision=head,
        execution=execution,
    )


class TestThroughTheWholeReview:
    def test_the_criterion_is_rated_as_if_execution_had_not_run(self, repo):
        """Nothing verifies edits by default, so a review that injected and
        observed must land exactly where one that did not injects lands."""
        executed = _review(repo, execution=ExecutionSettings(verify_edits=True))
        static_only = _review(repo, execution=None)
        (with_it,) = [o for o in executed.obligation_map if o.id == "equal-payments"]
        (without,) = [o for o in static_only.obligation_map if o.id == "equal-payments"]
        assert with_it.achieved_evidence_tier is without.achieved_evidence_tier
        assert with_it.evidence_class == without.evidence_class
        assert with_it.test_evidence == without.test_evidence

    def test_the_observation_was_really_made(self, repo):
        """The control for the test above: if no edit ran, that equality would
        hold for an uninteresting reason."""
        review = _review(repo, execution=ExecutionSettings(verify_edits=True))
        (attempt,) = review.mutation_attempts
        assert attempt.observed is True
        assert attempt.verified is False
        assert attempt.tests_run

    def test_no_stored_verdict_claims_the_executed_tier(self, repo):
        review = _review(repo, execution=ExecutionSettings(verify_edits=True))
        assert all(v.tier is EvidenceTier.STATIC for v in review.pair_verdicts)

    def test_the_static_judge_is_told_nothing_about_the_edit(self, repo):
        """The boundary, asserted on the request as sent: half of these edits
        are wrong, so the judge must not be anchored on one — not even as a
        hint. It is given the defect, and no trace of what was injected or of
        what the tests did about it."""
        capture: list = []
        _review(repo, execution=ExecutionSettings(verify_edits=True), capture=capture)
        prompts = [c["prompt"] for c in capture if c["schema"] == "_PairVerdicts"]
        assert prompts, "the static judge was never asked, so there is no request to inspect"
        for prompt in prompts:
            assert "months - 1" not in prompt, "the injected replacement reached the judge"
            assert "killed" not in prompt
            assert "injected" not in prompt

    def test_the_report_says_the_result_is_not_counted(self, repo):
        report = render_report(_review(repo, execution=ExecutionSettings(verify_edits=True)))
        # The outcome label itself, so the mark cannot be missed by a reader who
        # reads "[killed]" and "caught by" and stops there.
        assert "[killed, NOT COUNTED]" in report
        assert "edit NOT verified to make the defect true" in report
        assert "this result is not counted" in report
        assert "tier: static" in report

    def test_a_verified_result_carries_no_such_mark(self, repo):
        """The control: the mark must distinguish, not decorate every result."""
        judgments = {
            **_JUDGMENTS,
            "_Verification": {
                "before_does": "expected",
                "after_does": "defective",
                "reason": "line 3 now returns one entry fewer",
            },
        }
        root, base, head = repo
        review = run_review(
            task_text=_TASK,
            change_set=extract_change_set(root, base, head),
            repo=root,
            client=client_dispatching(judgments),
            reviewed_revision=head,
            execution=ExecutionSettings(verify_edits=True),
        )
        report = render_report(review)
        assert "[killed]" in report
        assert "NOT COUNTED" not in report

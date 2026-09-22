"""The pipeline actually runs the execution tier, and it runs it FIRST.

Separate from the other mutation tests deliberately. Every one of those calls
the mutation modules directly and would still pass if `run_review` never called
any of them — the exact shape of hole defect injection keeps finding in this
repo: a well-tested helper the pipeline does not use. These fail if the wiring
is removed.

Two claims matter and they are different. That injection happens at all, and
that the static pair judgement is asked only about what injection could not
settle — DR-171 Decision 7 as revised, where the whole saving lives. A version
that ran injection and then judged every pair anyway would satisfy the first and
fail the second, while costing more than not running injection at all.

The repository is the amortization case from
`tests/fixtures/archetypes/03-superficial-test` in miniature: a payment function
whose only test asserts the schedule's length and that its values are positive,
never the amounts.
"""

from __future__ import annotations

import subprocess
from typing import ClassVar

from acceptance.change.diff import extract_change_set
from acceptance.evidence_tier import EvidenceTier
from acceptance.execution.sandbox import SandboxConfig
from acceptance.mutation.attempt import (
    MutationOutcomeKind,
    RepairCorroboration,
    VerificationStep,
)
from acceptance.mutation.settings import ExecutionSettings
from acceptance.pipeline import run_review
from acceptance.report import render_report
from acceptance.review_state import UnjudgedCause
from tests.support import client_dispatching

_TASK = (
    "# Task\nThe schedule pays the loan off in equal monthly payments.\n\n"
    "## Constraints\n- Every monthly payment is the same amount\n"
)

_BASE = "def amortize(principal, months):\n    raise NotImplementedError\n"

_HEAD = """def amortize(principal, months):
    payment = principal / months
    return [payment for _ in range(months)]
"""

_TEST = """from loan import amortize


def test_returns_a_payment_for_each_month():
    schedule = amortize(1200.0, 12)
    assert isinstance(schedule, list)
    assert len(schedule) == 12
    assert all(payment > 0 for payment in schedule)
"""

_TEST_ID = "test_loan.py::test_returns_a_payment_for_each_month"

_JUDGMENTS = {
    "_Decomposition": {
        "obligations": [
            {
                "id": "equal-payments",
                "description": "Every monthly payment is the same amount",
                "type": "functional",
                "importance": "critical",
                "explicit": True,
                "observable_behavior": "amortize returns equal payments that repay the loan",
                "source_quote": "Every monthly payment is the same amount",
            }
        ],
        "open_questions": [],
        "requirement_dispositions": [
            {
                "requirement_id": "task-01",
                "disposition": "no_obligation",
                "reason": "Restates the constraint below; imposes nothing of its own.",
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
                "expected_behavior": "the code behaves as the criterion requires",
                "defective_behavior": "the code behaves as this defect describes",
                "type": "other",
                "description": "The payment amount is wrong, so the loan is not repaid.",
                "code_refs": ["loan.py#0"],
            }
        ],
        "reason": "",
    },
    # The edit lands on the payment line, which the test never asserts about.
    "_Descriptor": {
        "code_currently_does": "expected",
        "region_label": "loan.py#0",
        "start_line": 2,
        "end_line": 2,
        "replacement": "    payment = principal / months * 3\n",
        "decline": "none",
        "reason": "",
    },
    # The tier runs only when verification is on (`decide_execution`), so every
    # fixture that exercises it needs an answer here. This one verifies the edit.
    "_Verification": {
        "before_does": "expected",
        "after_does": "defective",
        "reason": "line 2 now triples the payment",
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


def _repo(tmp_path, *, head_test: str = _TEST):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "loan.py").write_text(_BASE)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / "loan.py").write_text(_HEAD)
    (repo / "test_loan.py").write_text(head_test)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "head")
    return repo, base, _git(repo, "rev-parse", "HEAD")


def _review(
    tmp_path,
    *,
    execution: ExecutionSettings | None,
    head_test: str = _TEST,
    capture=None,
    judgments: dict | None = None,
):
    repo, base, head = _repo(tmp_path, head_test=head_test)
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(repo, base, head),
        repo=repo,
        client=client_dispatching(judgments or _JUDGMENTS, capture=capture),
        reviewed_revision=head,
        execution=execution,
    )


#: A descriptor answer that declines: no single contiguous edit expresses this
#: defect. The runner turns it into `not_mutable`, which is the routing
#: instruction that hands the defect to the static judge.
_DECLINING = {
    **_JUDGMENTS,
    "_Descriptor": {
        "code_currently_does": "expected",
        "region_label": "",
        "start_line": 0,
        "end_line": 0,
        "replacement": "",
        "decline": "not_one_contiguous_edit",
        "reason": "the behaviour is absent, so there is no span to replace",
    },
}

#: A descriptor answer saying the delivered code already has the defect, with no
#: repair edit given.
_ALREADY_PRESENT = {
    **_DECLINING,
    "_Descriptor": {
        **_DECLINING["_Descriptor"],
        "code_currently_does": "defective",
        "decline": "none",
        "reason": "line 2 already divides without interest",
    },
}

#: The same claim with a repair edit that no candidate test notices: the test
#: asserts only the schedule's length and positivity.
_ALREADY_PRESENT_WITH_REPAIR = {
    **_JUDGMENTS,
    "_Descriptor": {
        **_JUDGMENTS["_Descriptor"],
        "code_currently_does": "defective",
        "replacement": "    payment = round(principal / months, 2)\n",
        "reason": "line 2 already divides without interest",
    },
}

#: A repair the candidate test does notice, so it asserts the defective behaviour.
_ALREADY_PRESENT_REPAIR_FAILS_A_TEST = {
    **_JUDGMENTS,
    "_Descriptor": {
        **_JUDGMENTS["_Descriptor"],
        "code_currently_does": "defective",
        "start_line": 3,
        "end_line": 3,
        "replacement": "    return [payment for _ in range(months + 1)]\n",
        "reason": "line 3 already returns one entry per month",
    },
}


def _schemas(capture) -> list[str]:
    return [call["schema"] for call in capture]


class TestTheTierRuns:
    def test_the_enumerated_behaviours_reach_the_descriptor_request(self, tmp_path):
        """Through the real pipeline: the two behaviours the listing step
        returns are what the edit-building call is shown, rather than being
        dropped on the way through the review state."""
        capture: list = []
        _review(tmp_path, execution=ExecutionSettings(verify_edits=True), capture=capture)
        (prompt,) = [call["prompt"] for call in capture if call["schema"] == "_Descriptor"]
        assert "EXPECTED: the code behaves as the criterion requires" in prompt
        assert "DEFECTIVE: the code behaves as this defect describes" in prompt

    def test_the_descriptor_request_carries_the_surrounding_code(self, tmp_path):
        """Through the real pipeline: M2.2's retrieval reaches the edit-building
        call — the enclosing definition, numbered with the file's own lines."""
        capture: list = []
        _review(tmp_path, execution=ExecutionSettings(verify_edits=True), capture=capture)
        (prompt,) = [call["prompt"] for call in capture if call["schema"] == "_Descriptor"]
        assert "## Surrounding code (enclosing definitions and their callers)" in prompt
        assert "function amortize — loan.py lines 1-3" in prompt

    def test_the_descriptor_stage_is_called(self, tmp_path):
        """Acceptance, by the same path a review run takes: the pipeline asks
        for a mutant, rather than merely being able to."""
        capture: list = []
        _review(tmp_path, execution=ExecutionSettings(verify_edits=True), capture=capture)
        assert "_Descriptor" in _schemas(capture)

    def test_the_survival_is_observed_and_recorded(self, tmp_path):
        """The test runs the mutated line and still passes."""
        review = _review(tmp_path, execution=ExecutionSettings(verify_edits=True))
        (attempt,) = review.mutation_attempts
        assert attempt.outcome is MutationOutcomeKind.SURVIVED
        assert attempt.observed is True


class TestVerification:
    """The verifier through the real pipeline. Off by default; when switched on,
    its answer decides whether an observed result counts."""

    _VERIFIED: ClassVar[dict] = {
        **_JUDGMENTS,
        "_Verification": {
            "before_does": "expected",
            "after_does": "defective",
            "reason": "line 2 now triples the payment",
        },
    }
    _REFUSED: ClassVar[dict] = {
        **_JUDGMENTS,
        "_Verification": {
            "before_does": "expected",
            "after_does": "other",
            "reason": "the edit changes nothing the defect names",
        },
    }

    def test_nothing_runs_at_all_when_no_consumer_wants_it(self, tmp_path):
        """No consumer switched on, so `decide_execution` declines the whole run
        — no control run, no descriptor, no verification.

        This used to be the DEFAULT. Since #340 routing is on by default and is a
        consumer, so reaching this state takes turning both off. What the test
        pins is unchanged: a declined run touches nothing.
        """
        capture: list = []
        settings = ExecutionSettings(verify_edits=False, route_pairs=False)
        review = _review(tmp_path, execution=settings, capture=capture)
        assert "_Verification" not in _schemas(capture)
        assert "_Descriptor" not in _schemas(capture)
        assert review.mutation_attempts == []
        assert review.execution_decision.run is False
        assert "no result could have counted" in review.execution_decision.reason

    def test_the_default_runs_but_verifies_nothing(self, tmp_path):
        """#340's default, and the line it must not cross.

        The run happens, so pairs can be routed. Verification does not, so no
        attempt is settled and nothing reaches `defect-killed` — the tier gate
        `tests/test_unverified_mutation_is_inert.py` owns is untouched by making
        the run happen more often.
        """
        capture: list = []
        review = _review(tmp_path, execution=ExecutionSettings(), capture=capture)
        assert review.execution_decision.run is True
        assert "_Descriptor" in _schemas(capture), "the run must actually inject"
        assert "_Verification" not in _schemas(capture)
        assert review.mutation_attempts
        assert not any(attempt.settled for attempt in review.mutation_attempts)

    def test_a_verified_edit_reaches_the_executed_tier(self, tmp_path):
        """#45's Acceptance, visible in the pipeline's own output — once an
        edit is verified."""
        capture: list = []
        review = _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=True),
            capture=capture,
            judgments=self._VERIFIED,
        )
        (obligation,) = [o for o in review.obligation_map if o.id == "equal-payments"]
        assert obligation.achieved_evidence_tier is EvidenceTier.DEFECT_KILLED
        assert obligation.evidence_class == "unsupported"
        assert "_PairVerdicts" not in _schemas(capture)

    def test_a_refused_edit_stays_static_and_goes_to_the_static_judge(self, tmp_path):
        capture: list = []
        review = _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=True),
            capture=capture,
            judgments=self._REFUSED,
        )
        (attempt,) = review.mutation_attempts
        assert attempt.verified is False
        assert "the edit changes nothing the defect names" in attempt.verification_reason
        assert "_PairVerdicts" in _schemas(capture)

    def test_the_verifier_is_not_shown_the_tests(self, tmp_path):
        capture: list = []
        _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=True),
            capture=capture,
            judgments=self._VERIFIED,
        )
        (prompt,) = [c["prompt"] for c in capture if c["schema"] == "_Verification"]
        assert "test_returns_a_payment_for_each_month" not in prompt
        assert "payment = principal / months * 3" in prompt

    def test_the_verifier_is_shown_the_surrounding_code(self, tmp_path):
        capture: list = []
        _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=True),
            capture=capture,
            judgments=self._VERIFIED,
        )
        (prompt,) = [c["prompt"] for c in capture if c["schema"] == "_Verification"]
        assert "function amortize — loan.py lines 1-3" in prompt

    _NO_CHANGE: ClassVar[dict] = {
        **_JUDGMENTS,
        "_BehaviourChange": {
            "changes_behaviour": "no_change",
            "reason": "tripling is cancelled further down",
        },
    }

    def test_an_edit_that_changes_nothing_is_refused_by_the_first_question(self, tmp_path):
        """#335: the first question's refusal is recorded as its own, and the
        second question is never asked about that edit."""
        capture: list = []
        review = _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=True),
            capture=capture,
            judgments=self._NO_CHANGE,
        )
        (attempt,) = review.mutation_attempts
        assert attempt.verified is False
        assert attempt.refused_by is VerificationStep.BEHAVIOUR_CHANGE
        assert "tripling is cancelled further down" in attempt.verification_reason
        assert "_BehaviourChange" in _schemas(capture)
        assert "_Verification" not in _schemas(capture)
        assert "_PairVerdicts" in _schemas(capture)

    def test_an_edit_that_changes_the_wrong_thing_is_refused_by_the_second(self, tmp_path):
        review = _review(
            tmp_path, execution=ExecutionSettings(verify_edits=True), judgments=self._REFUSED
        )
        (attempt,) = review.mutation_attempts
        assert attempt.refused_by is VerificationStep.DEFECT_MATCH

    def test_a_verified_edit_carries_no_refusing_question(self, tmp_path):
        review = _review(
            tmp_path, execution=ExecutionSettings(verify_edits=True), judgments=self._VERIFIED
        )
        (attempt,) = review.mutation_attempts
        assert attempt.verified is True
        assert attempt.refused_by is None

    def test_the_first_question_is_shown_neither_the_tests_nor_the_defect(self, tmp_path):
        capture: list = []
        _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=True),
            capture=capture,
            judgments=self._VERIFIED,
        )
        (prompt,) = [c["prompt"] for c in capture if c["schema"] == "_BehaviourChange"]
        assert "payment = principal / months * 3" in prompt
        assert "test_returns_a_payment_for_each_month" not in prompt
        assert "test_loan.py" not in prompt
        assert "The payment amount is wrong" not in prompt


class TestTheBreadthSettingsReachTheRunner:
    def test_a_kill_too_broad_for_the_configured_threshold_is_not_a_kill(self, tmp_path):
        """The edit drops a month, which the one candidate test catches. With
        the floor at 0 and the fraction at 50%, one failure of one test is too
        broad — so this passes only if the pipeline hands the settings on."""
        killing = {
            **_JUDGMENTS,
            "_Descriptor": {
                **_JUDGMENTS["_Descriptor"],
                "start_line": 3,
                "end_line": 3,
                "replacement": "    return [payment for _ in range(months - 1)]\n",
            },
        }
        review = _review(
            tmp_path,
            execution=ExecutionSettings(
                verify_edits=True, max_failing_fraction=0.5, breadth_floor=0
            ),
            judgments=killing,
        )
        (attempt,) = review.mutation_attempts
        assert attempt.outcome is MutationOutcomeKind.NOT_MUTABLE
        assert "candidate tests failed under the edit" in attempt.reason


_REFUSED_VERIFICATION = {
    **_JUDGMENTS,
    "_Verification": {
        "before_does": "expected",
        "after_does": "other",
        "reason": "the edit changes nothing the defect names",
    },
}


class TestAnUnverifiedEditIsNotEvidence:
    """The tier gate, through the real pipeline. An observed result whose edit
    verification refused stays at the static tier and its defect goes to the
    static judge — a bad edit costs compute, not a wrong tier."""

    def _refused(self, tmp_path, capture=None):
        return _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=True),
            judgments=_REFUSED_VERIFICATION,
            capture=capture,
        )

    def test_the_criterion_stays_at_the_static_tier(self, tmp_path):
        review = self._refused(tmp_path)
        (obligation,) = [o for o in review.obligation_map if o.id == "equal-payments"]
        assert obligation.achieved_evidence_tier is EvidenceTier.STATIC

    def test_the_attempt_is_not_settled(self, tmp_path):
        review = self._refused(tmp_path)
        (attempt,) = review.mutation_attempts
        assert attempt.verified is False
        assert attempt.settled is False

    def test_its_defect_still_goes_to_the_static_judge(self, tmp_path):
        capture: list = []
        self._refused(tmp_path, capture=capture)
        assert "_PairVerdicts" in _schemas(capture)

    def test_no_executed_verdict_is_stored(self, tmp_path):
        review = self._refused(tmp_path)
        assert all(v.tier is EvidenceTier.STATIC for v in review.pair_verdicts)

    def test_the_report_says_the_result_is_not_counted(self, tmp_path):
        report = render_report(self._refused(tmp_path))
        assert "edit NOT verified to make the defect true" in report


class TestTheStaticJudgeSeesOnlyTheRemainder:
    def test_the_pair_stage_is_asked_when_execution_is_off(self, tmp_path):
        """The control for the test above: without execution the same review
        does spend that call, so the absence above is the tier working rather
        than the fixture never reaching that stage."""
        capture: list = []
        _review(tmp_path, execution=None, capture=capture)
        assert "_PairVerdicts" in _schemas(capture)

    def test_a_defect_injection_could_not_settle_reaches_the_static_judge(self, tmp_path):
        """The fallback, with execution ON — which is the case the two tests
        above do not cover between them. #45's Gate 2 asked for exactly this:
        one is the tier skipping the model, the other is the tier never having
        run, and neither shows a defect being handed on.
        """
        capture: list = []
        _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=True),
            capture=capture,
            judgments=_DECLINING,
        )
        schemas = _schemas(capture)
        assert "_Descriptor" in schemas, "the tier did not run, so nothing was handed on"
        assert "_PairVerdicts" in schemas

    def test_the_unsettled_defect_is_recorded_with_its_reason(self, tmp_path):
        """The model's own reason, not a generic sentence put in its place."""
        review = _review(
            tmp_path, execution=ExecutionSettings(verify_edits=True), judgments=_DECLINING
        )
        (attempt,) = review.mutation_attempts
        assert attempt.outcome is MutationOutcomeKind.NOT_MUTABLE
        assert attempt.reason == "the behaviour is absent, so there is no span to replace"
        assert attempt.tier is EvidenceTier.STATIC


class TestAnAlreadyPresentDefect:
    def test_it_is_recorded_as_its_own_outcome(self, tmp_path):
        review = _review(
            tmp_path, execution=ExecutionSettings(verify_edits=True), judgments=_ALREADY_PRESENT
        )
        (attempt,) = review.mutation_attempts
        assert attempt.outcome is MutationOutcomeKind.ALREADY_PRESENT
        assert attempt.reason.startswith("line 2 already divides without interest")

    def test_it_still_reaches_the_static_judge(self, tmp_path):
        """Additive: the decline is typed, but the defect is routed exactly as
        any other defect injection could not settle."""
        capture: list = []
        _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=True),
            capture=capture,
            judgments=_ALREADY_PRESENT,
        )
        assert "_PairVerdicts" in _schemas(capture)

    def test_the_report_flags_it_as_a_model_asserted_claim_at_the_static_tier(self, tmp_path):
        report = render_report(
            _review(
                tmp_path, execution=ExecutionSettings(verify_edits=True), judgments=_ALREADY_PRESENT
            )
        )
        heading = (
            "Defects the delivered code already has, as asserted by the model "
            "(static tier; needs human review):"
        )
        assert heading in report
        after = report.split(heading, 1)[1]
        assert "line 2 already divides without interest" in after
        assert "no test run supports or contradicts this claim" in after

    def test_the_block_is_absent_when_nothing_was_already_present(self, tmp_path):
        report = render_report(
            _review(tmp_path, execution=ExecutionSettings(verify_edits=True), judgments=_DECLINING)
        )
        assert "as asserted by the model" not in report

    def test_without_a_repair_the_claim_is_not_run(self, tmp_path):
        review = _review(
            tmp_path, execution=ExecutionSettings(verify_edits=True), judgments=_ALREADY_PRESENT
        )
        (attempt,) = review.mutation_attempts
        assert attempt.repair_corroboration is RepairCorroboration.NOT_RUN

    def test_a_repair_every_test_passes_means_no_test_pins_the_expected_behaviour(self, tmp_path):
        review = _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=True),
            judgments=_ALREADY_PRESENT_WITH_REPAIR,
        )
        (attempt,) = review.mutation_attempts
        assert attempt.outcome is MutationOutcomeKind.ALREADY_PRESENT
        assert attempt.repair_corroboration is RepairCorroboration.NO_TEST_PINS_EXPECTED
        assert attempt.tier is EvidenceTier.STATIC
        assert "That fits no test pinning the expected behaviour, but the repair" in render_report(
            review
        )

    def test_a_repair_a_test_fails_names_the_test_asserting_the_defect(self, tmp_path):
        review = _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=True),
            judgments=_ALREADY_PRESENT_REPAIR_FAILS_A_TEST,
        )
        (attempt,) = review.mutation_attempts
        assert attempt.repair_corroboration is RepairCorroboration.A_TEST_ASSERTS_DEFECTIVE
        assert attempt.repair_failing_tests == [_TEST_ID]
        assert attempt.tier is EvidenceTier.STATIC
        report = render_report(review)
        assert "so this does not confirm the claim" in report

    def test_a_claim_is_never_counted_as_a_kill(self, tmp_path):
        """The repair's failing test is not a kill: it caught a repair, not the
        defect. Nothing about the claim reaches the rating."""
        review = _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=True),
            judgments=_ALREADY_PRESENT_REPAIR_FAILS_A_TEST,
        )
        (attempt,) = review.mutation_attempts
        assert attempt.killing_tests == []
        assert attempt.settled is False
        assert all(v.tier is EvidenceTier.STATIC for v in review.pair_verdicts)

    def test_no_model_call_decides_validity(self, tmp_path):
        """DR-171 Decision 3, structurally: after the descriptor is proposed,
        nothing asks a model whether the mutant is valid or whether it really
        breaks the requirement. The four checks in `validity.py` decide, and
        this pins that no second call creeps in between.
        """
        capture: list = []
        _review(tmp_path, execution=ExecutionSettings(verify_edits=True), capture=capture)
        schemas = _schemas(capture)

        # One call per defect, and this fixture has one defect. A second would
        # mean the mutant was proposed and then asked about again.
        assert schemas.count("_Descriptor") == 1

        # Nothing between proposing the mutant and the first stage that comes
        # after the execution tier: the static pair judgement, which an
        # unverified result still reaches, or the ordinary rest of the review.
        next_call = schemas[schemas.index("_Descriptor") + 1]
        # Verification's first question comes first when verification is on (#335).
        assert next_call in {"_BehaviourChange", "_PairVerdicts", "_Coverage"}, (
            "a model call was made between proposing the mutant and recording its "
            f"outcome: {next_call}"
        )


class TestExecutionOffChangesNothing:
    def test_the_criterion_stays_at_the_static_tier(self, tmp_path):
        """§8.3's graceful degradation reached with no separate mode: a review
        that cannot or does not run tests is simply the case where every verdict
        stays `STATIC`."""
        review = _review(tmp_path, execution=None)
        (obligation,) = [o for o in review.obligation_map if o.id == "equal-payments"]
        assert obligation.achieved_evidence_tier is EvidenceTier.STATIC

    def test_no_descriptor_call_is_made(self, tmp_path):
        """Every consumer off, which since #340 means saying so explicitly."""
        capture: list = []
        settings = ExecutionSettings(verify_edits=False, route_pairs=False)
        _review(tmp_path, execution=settings, capture=capture)
        assert "_Descriptor" not in _schemas(capture)

    def test_the_report_carries_no_execution_headings(self, tmp_path):
        """A review that did not run the tests renders exactly as it did before
        M8.4, rather than carrying empty headings a reader must learn to skip."""
        report = render_report(_review(tmp_path, execution=None))
        assert "Defects injected" not in report
        assert "set aside" not in report


class TestWhatIsPersistedAndRendered:
    def test_the_injected_text_is_stored_on_the_review(self, tmp_path):
        """DR-171 Decision 3 spends no model call confirming the mutant really
        violates the obligation. Recording what was injected is the whole of
        what replaces that, so it has to survive into review state."""
        review = _review(tmp_path, execution=ExecutionSettings(verify_edits=True))
        (attempt,) = review.mutation_attempts
        assert attempt.descriptor is not None
        assert "* 3" in attempt.descriptor.replacement

    def test_the_report_shows_the_injected_text(self, tmp_path):
        report = render_report(_review(tmp_path, execution=ExecutionSettings(verify_edits=True)))
        assert "Defects injected, and which tests caught them:" in report
        assert "payment = principal / months * 3" in report

    def test_the_report_shows_what_the_edit_replaced(self, tmp_path):
        """Removed and added lines both render, as a diff reads."""
        report = render_report(_review(tmp_path, execution=ExecutionSettings(verify_edits=True)))
        assert "      -     payment = principal / months\n" in report
        assert "      +     payment = principal / months * 3" in report

    def test_a_deletion_shows_the_lines_it_removed(self, tmp_path):
        """Before `original` was stored, a deleting mutant rendered as one empty
        line and no sign of what had gone."""
        deleting = {
            **_JUDGMENTS,
            "_Descriptor": {**_JUDGMENTS["_Descriptor"], "replacement": ""},
        }
        report = render_report(
            _review(tmp_path, execution=ExecutionSettings(verify_edits=True), judgments=deleting)
        )
        assert "      -     payment = principal / months" in report
        assert "(lines deleted)" in report

    def test_the_report_says_no_test_caught_it(self, tmp_path):
        report = render_report(_review(tmp_path, execution=ExecutionSettings(verify_edits=True)))
        assert "no test caught it" in report

    def test_a_set_aside_test_is_stored_and_reported(self, tmp_path):
        review = _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=True),
            head_test=TestARedCandidateTestIsSetAside._RED_TEST,
        )
        assert [t.test_id for t in review.set_aside_tests] == [
            "test_loan.py::test_that_is_already_failing"
        ]
        report = render_report(review)
        assert "Candidate tests set aside" in report
        assert "test_that_is_already_failing" in report


class TestTheControlRunComesFirst:
    """The tests run once against the code as delivered BEFORE anything is
    altered. Gate 2 run 3 asked for this directly: the existing coverage proved
    it only indirectly, by showing no descriptor is bought when the control run
    finds nothing usable.

    Asserted on call order, by recording when the control run happens relative
    to the first descriptor request.
    """

    def test_the_baseline_runs_before_any_descriptor_is_asked_for(self, tmp_path, monkeypatch):
        from acceptance import pipeline

        order: list[str] = []
        real_baseline = pipeline.establish_baseline

        def recording_baseline(*args, **kwargs):
            order.append("control run")
            return real_baseline(*args, **kwargs)

        real_descriptors = pipeline.build_descriptors

        def recording_descriptors(*args, **kwargs):
            order.append("descriptor")
            return real_descriptors(*args, **kwargs)

        monkeypatch.setattr(pipeline, "establish_baseline", recording_baseline)
        monkeypatch.setattr(pipeline, "build_descriptors", recording_descriptors)

        _review(tmp_path, execution=ExecutionSettings(verify_edits=True))

        assert order, "neither the control run nor the descriptor stage was reached"
        assert order[0] == "control run"
        assert "descriptor" in order, "the tier stopped before injecting, so the order is vacuous"
        assert order.index("control run") < order.index("descriptor")

    def test_it_runs_once_rather_than_per_defect(self, tmp_path, monkeypatch):
        """One run against the delivered code, not one per injected edit."""
        from acceptance import pipeline

        calls: list[int] = []
        real_baseline = pipeline.establish_baseline

        def counting_baseline(*args, **kwargs):
            calls.append(1)
            return real_baseline(*args, **kwargs)

        monkeypatch.setattr(pipeline, "establish_baseline", counting_baseline)
        _review(tmp_path, execution=ExecutionSettings(verify_edits=True))
        assert len(calls) == 1


class TestARedCandidateTestIsSetAside:
    """A test already failing at head no longer stops anything — the human's
    ruling of 2026-09-18. It is set aside by name, the rest carry on, and the
    review returns normally."""

    _RED_TEST = (
        _TEST
        + """

def test_that_is_already_failing():
    assert amortize(1200.0, 12)[0] == 999.0
"""
    )

    def test_the_review_returns_rather_than_stopping(self, tmp_path):
        review = _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=True),
            head_test=self._RED_TEST,
        )
        assert review.obligation_map, "the review produced nothing"

    def test_the_failing_test_is_named_and_the_others_carry_on(self, tmp_path):
        review = _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=True),
            head_test=self._RED_TEST,
        )
        assert [t.test_id for t in review.set_aside_tests] == [
            "test_loan.py::test_that_is_already_failing"
        ]
        (attempt,) = review.mutation_attempts
        assert attempt.observed is True
        assert attempt.tests_run == [_TEST_ID]

    def test_the_report_says_which_was_set_aside(self, tmp_path):
        report = render_report(
            _review(
                tmp_path,
                execution=ExecutionSettings(verify_edits=True),
                head_test=self._RED_TEST,
            )
        )
        assert "Candidate tests set aside" in report
        assert "test_that_is_already_failing" in report


class TestWhenTheTestsCannotBeRunAtAll:
    def test_no_descriptor_is_bought_when_no_test_can_be_observed(self, tmp_path):
        """#45's Gate 2 run 2 paid $0.2554 for 71 descriptors and threw every
        one away: the control run produced no report, so nothing could be
        observed, and `run_mutations` refused to inject — but only *after* the
        pipeline had already bought the descriptors.

        The runner's own test that it asks for no descriptor passed throughout,
        because the runner does not ask for them; the pipeline does. That is the
        shape CLAUDE.md warns about, so the assertion belongs here.

        Driven with an interpreter that does not exist, which is the cheapest
        way to make a real project's tests unrunnable.
        """
        capture: list = []
        _review(
            tmp_path,
            execution=ExecutionSettings(
                verify_edits=True, sandbox=SandboxConfig(interpreter="/nonexistent/python")
            ),
            capture=capture,
        )
        assert "_Descriptor" not in _schemas(capture)

    def test_the_defects_still_fall_back_to_the_static_judge(self, tmp_path):
        capture: list = []
        review = _review(
            tmp_path,
            execution=ExecutionSettings(
                verify_edits=True, sandbox=SandboxConfig(interpreter="/nonexistent/python")
            ),
            capture=capture,
        )
        assert all(a.outcome is MutationOutcomeKind.NOT_ATTEMPTED for a in review.mutation_attempts)
        assert "_PairVerdicts" in _schemas(capture)


# --- the run decides which pairs are worth a model call (#340) -----------------

#: Two candidate tests, and the edit above (`payment = principal / months * 3`)
#: separates them. The strict one pins the amount and goes red; the loose one
#: asserts length and positivity and does not. That split is the whole point:
#: routing keeps the red test's pair and holds back the other's.
_TWO_TESTS = """from loan import amortize


def test_returns_a_payment_for_each_month():
    schedule = amortize(1200.0, 12)
    assert isinstance(schedule, list)
    assert len(schedule) == 12
    assert all(payment > 0 for payment in schedule)


def test_each_payment_is_the_loan_over_the_term():
    assert amortize(1200.0, 12)[0] == 100.0
"""

_LOOSE_ID = "test_loan.py::test_returns_a_payment_for_each_month"
_STRICT_ID = "test_loan.py::test_each_payment_is_the_loan_over_the_term"
_DEFECT_ID = "equal-payments/wrong-payment-amount"

#: The static judge says the red test does catch the defect. Needed so rule 6
#: does NOT fire: with no kill among the asked pairs the held-back pair would be
#: asked after all, and the saving would be invisible.
_JUDGE_CONFIRMS_THE_KILL = {
    **_JUDGMENTS,
    "_PairVerdicts": {
        "tests": [
            {
                "test_id": _STRICT_ID,
                "defects": [
                    {"defect_id": _DEFECT_ID, "fails": True, "reason": "it pins the amount"}
                ],
            }
        ]
    },
}


def _tests_put_to_the_judge(capture) -> set[str]:
    """Every test the pair stage actually named to the model.

    Read off the request as sent, for the same reason
    `test_the_static_judge_is_told_nothing_about_the_edit` is: the claim is about
    what the model was asked, and only the request settles that. The fixture
    enumerates one defect, so a test absent from every pair prompt is a pair that
    was never offered.
    """
    named: set[str] = set()
    for call in capture:
        if call["schema"] != "_PairVerdicts":
            continue
        for line in call["prompt"].splitlines():
            if line.startswith("### test "):
                named.add(line[len("### test ") :].strip())
    return named


class TestTheRunRoutesPairsThroughTheRealPipeline:
    """#340, asserted on `run_review` rather than on the helper.

    `CLAUDE.md` records this repo's recurring defect shape: a helper with a good
    unit test that the pipeline never calls. `pairs_not_worth_asking` has its own
    unit tests in `tests/test_pair_routing.py`; what is pinned here is that a real
    review computes it, hands it to `judge_pairs`, and the model is not asked.
    """

    def test_the_fixture_really_separates_the_two_tests(self, tmp_path):
        """Not an assertion about the feature — an assertion that the setup can
        show anything at all. Without it every test below passes vacuously on a
        run where the edit killed nothing."""
        review = _review(
            tmp_path,
            execution=ExecutionSettings(),
            head_test=_TWO_TESTS,
            judgments=_JUDGE_CONFIRMS_THE_KILL,
        )
        (attempt,) = review.mutation_attempts
        assert attempt.outcome is MutationOutcomeKind.KILLED
        assert attempt.killing_tests == [_STRICT_ID]
        assert _LOOSE_ID in attempt.tests_run
        assert not attempt.verified, "verification is off, so nothing is settled"

    def test_the_test_that_kept_passing_is_never_put_to_the_model(self, tmp_path):
        capture: list = []
        _review(
            tmp_path,
            execution=ExecutionSettings(),
            head_test=_TWO_TESTS,
            capture=capture,
            judgments=_JUDGE_CONFIRMS_THE_KILL,
        )
        named = _tests_put_to_the_judge(capture)
        assert _STRICT_ID in named, "the red test's pair is still judged"
        assert _LOOSE_ID not in named

    def test_the_held_back_pair_is_recorded_rather_than_dropped(self, tmp_path):
        """A pair nobody records reads exactly like one judged `survives`, which
        is the failure `UnjudgedPair` exists to prevent."""
        review = _review(
            tmp_path,
            execution=ExecutionSettings(),
            head_test=_TWO_TESTS,
            judgments=_JUDGE_CONFIRMS_THE_KILL,
        )
        held = [e for e in review.unjudged_pairs if e.cause is UnjudgedCause.PASSED_UNDER_EDIT]
        assert [(e.defect_id, e.test_id) for e in held] == [(_DEFECT_ID, _LOOSE_ID)]
        assert "not verified" in held[0].reason
        assert _LOOSE_ID not in {v.test_id for v in review.pair_verdicts}

    def test_routing_off_puts_both_tests_to_the_model(self, tmp_path):
        """The control. Without it the two tests above pass on a review whose
        pair stage was never reached at all."""
        capture: list = []
        _review(
            tmp_path,
            execution=ExecutionSettings(verify_edits=False, route_pairs=False),
            head_test=_TWO_TESTS,
            capture=capture,
            judgments=_JUDGE_CONFIRMS_THE_KILL,
        )
        assert _tests_put_to_the_judge(capture) == {_LOOSE_ID, _STRICT_ID}

    def test_the_report_names_where_the_defects_pairs_went(self, tmp_path):
        review = _review(
            tmp_path,
            execution=ExecutionSettings(),
            head_test=_TWO_TESTS,
            judgments=_JUDGE_CONFIRMS_THE_KILL,
        )
        report = render_report(review)
        assert "pairs: 0 settled by the run, 1 put to the model, 1 dropped" in report

    def test_a_defect_with_no_kill_among_its_judged_pairs_gets_them_back(self, tmp_path):
        """#340 rule 6, through the pipeline.

        Here the judge does NOT confirm the kill, so the run demonstrated nothing
        usable about the defect and the saving bought nothing. The held-back pair
        is put to the model after all, before the rating is derived — the same
        call rule 3 makes for an edit no test failed under, arriving one step
        later.
        """
        capture: list = []
        review = _review(
            tmp_path,
            execution=ExecutionSettings(),
            head_test=_TWO_TESTS,
            capture=capture,
            judgments=_JUDGMENTS,  # no `_PairVerdicts` answer: nothing kills
        )
        assert _tests_put_to_the_judge(capture) == {_LOOSE_ID, _STRICT_ID}
        assert not [e for e in review.unjudged_pairs if e.cause is UnjudgedCause.PASSED_UNDER_EDIT]

    def test_the_report_says_a_dropped_pair_is_not_evidence(self, tmp_path):
        """#340's Gate 2 asked for this by name, on two criteria.

        The rendered text is what a reader acts on, and a line saying a test
        "still passed" invites exactly the inference the tier gate forbids. The
        refusal has to be in the report, not only in the enum's docstring.
        """
        report = render_report(
            _review(
                tmp_path,
                execution=ExecutionSettings(),
                head_test=_TWO_TESTS,
                judgments=_JUDGE_CONFIRMS_THE_KILL,
            )
        )
        assert "not evidence that the test fails to catch the defect" in report
        assert "the edit was not verified" in report.lower()

    def test_the_report_names_the_defect_whose_edit_the_decision_rests_on(self, tmp_path):
        """One injection attempt per defect, so naming the defect names the
        attempt. Without it a reader cannot tell which edit produced the skip."""
        report = render_report(
            _review(
                tmp_path,
                execution=ExecutionSettings(),
                head_test=_TWO_TESTS,
                judgments=_JUDGE_CONFIRMS_THE_KILL,
            )
        )
        assert f"[passed_under_edit] {_DEFECT_ID}" in report

    def test_the_dropped_pairs_are_counted_not_listed_one_by_one(self, tmp_path):
        """§16. On #340's own Gate 2 the per-pair listing was 636 KB of a 768 KB
        report — 1,526 pairs at two lines each, burying every finding in it."""
        report = render_report(
            _review(
                tmp_path,
                execution=ExecutionSettings(),
                head_test=_TWO_TESTS,
                judgments=_JUDGE_CONFIRMS_THE_KILL,
            )
        )
        assert "x 1 candidate test(s)" in report
        assert f"{_DEFECT_ID} x {_LOOSE_ID}" not in report

    def test_the_pair_counts_are_stated_even_when_they_are_all_zero(self, tmp_path):
        """ "Nothing to report" and "not reported" are different, which is the
        distinction this project exists to keep. A defect no edit could be built
        for still says so."""
        report = render_report(
            _review(tmp_path, execution=ExecutionSettings(), judgments=_DECLINING)
        )
        assert "pairs: 0 settled by the run, 0 put to the model, 0 dropped" in report

    def test_a_kill_is_never_read_as_naming_the_defect(self, tmp_path):
        """The other criterion #340's Gate 2 flagged. A test going red under an
        unverified edit is a reason to ask fewer questions and nothing else, so
        the pair it belongs to is still judged and its verdict comes from the
        model rather than from the run."""
        review = _review(
            tmp_path,
            execution=ExecutionSettings(),
            head_test=_TWO_TESTS,
            judgments=_JUDGE_CONFIRMS_THE_KILL,
        )
        (attempt,) = review.mutation_attempts
        assert attempt.killing_tests == [_STRICT_ID]
        killing_pair = [v for v in review.pair_verdicts if v.test_id == _STRICT_ID]
        assert killing_pair, "the red test's pair must still carry a judged verdict"
        assert all(v.tier is EvidenceTier.STATIC for v in killing_pair)
        assert all(v.reason == "it pins the amount" for v in killing_pair)

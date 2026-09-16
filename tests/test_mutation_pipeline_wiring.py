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

import pytest

from acceptance.change.diff import extract_change_set
from acceptance.evidence_tier import EvidenceTier
from acceptance.execution.sandbox import SandboxConfig
from acceptance.mutation.attempt import MutationOutcomeKind
from acceptance.mutation.settings import ExecutionSettings, ReviewHalted
from acceptance.pipeline import run_review
from acceptance.report import render_report
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
        "region_label": "loan.py#0",
        "start_line": 2,
        "end_line": 2,
        "replacement": "    payment = principal / months * 3\n",
        "decline": "none",
        "reason": "",
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
        "region_label": "",
        "start_line": 0,
        "end_line": 0,
        "replacement": "",
        "decline": "not_one_contiguous_edit",
        "reason": "the behaviour is absent, so there is no span to replace",
    },
}

#: A descriptor answer saying the delivered code already has the defect.
_ALREADY_PRESENT = {
    **_DECLINING,
    "_Descriptor": {
        **_DECLINING["_Descriptor"],
        "decline": "already_present",
        "reason": "line 2 already divides without interest",
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
        _review(tmp_path, execution=ExecutionSettings(enabled=True), capture=capture)
        (prompt,) = [call["prompt"] for call in capture if call["schema"] == "_Descriptor"]
        assert "EXPECTED: the code behaves as the criterion requires" in prompt
        assert "DEFECTIVE: the code behaves as this defect describes" in prompt

    def test_the_descriptor_stage_is_called(self, tmp_path):
        """Acceptance, by the same path a review run takes: the pipeline asks
        for a mutant, rather than merely being able to."""
        capture: list = []
        _review(tmp_path, execution=ExecutionSettings(enabled=True), capture=capture)
        assert "_Descriptor" in _schemas(capture)

    def test_the_criterion_reaches_the_executed_tier(self, tmp_path):
        """The static "looks weak" becoming an observed "does not
        discriminate", visible in the pipeline's own output."""
        review = _review(tmp_path, execution=ExecutionSettings(enabled=True))
        (obligation,) = [o for o in review.obligation_map if o.id == "equal-payments"]
        assert obligation.achieved_evidence_tier is EvidenceTier.DEFECT_KILLED

    def test_the_surviving_defect_leaves_the_criterion_unsupported(self, tmp_path):
        """The test runs the mutated line and still passes, so it is proven not
        to discriminate — not merely predicted not to."""
        review = _review(tmp_path, execution=ExecutionSettings(enabled=True))
        (obligation,) = [o for o in review.obligation_map if o.id == "equal-payments"]
        assert obligation.evidence_class == "unsupported"
        assert obligation.test_evidence == []


class TestTheStaticJudgeSeesOnlyTheRemainder:
    def test_no_pair_is_judged_when_execution_settled_every_defect(self, tmp_path):
        """Where the saving lives. The one enumerated defect was settled by
        injection, so the expensive stage is asked nothing at all."""
        capture: list = []
        _review(tmp_path, execution=ExecutionSettings(enabled=True), capture=capture)
        assert "_PairVerdicts" not in _schemas(capture)

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
            execution=ExecutionSettings(enabled=True),
            capture=capture,
            judgments=_DECLINING,
        )
        schemas = _schemas(capture)
        assert "_Descriptor" in schemas, "the tier did not run, so nothing was handed on"
        assert "_PairVerdicts" in schemas

    def test_the_unsettled_defect_is_recorded_with_its_reason(self, tmp_path):
        """The model's own reason, not a generic sentence put in its place."""
        review = _review(tmp_path, execution=ExecutionSettings(enabled=True), judgments=_DECLINING)
        (attempt,) = review.mutation_attempts
        assert attempt.outcome is MutationOutcomeKind.NOT_MUTABLE
        assert attempt.reason == "the behaviour is absent, so there is no span to replace"
        assert attempt.tier is EvidenceTier.STATIC


class TestAnAlreadyPresentDefect:
    def test_it_is_recorded_as_its_own_outcome(self, tmp_path):
        review = _review(
            tmp_path, execution=ExecutionSettings(enabled=True), judgments=_ALREADY_PRESENT
        )
        (attempt,) = review.mutation_attempts
        assert attempt.outcome is MutationOutcomeKind.ALREADY_PRESENT
        assert attempt.reason == "line 2 already divides without interest"

    def test_it_still_reaches_the_static_judge(self, tmp_path):
        """Additive: the decline is typed, but the defect is routed exactly as
        any other defect injection could not settle."""
        capture: list = []
        _review(
            tmp_path,
            execution=ExecutionSettings(enabled=True),
            capture=capture,
            judgments=_ALREADY_PRESENT,
        )
        assert "_PairVerdicts" in _schemas(capture)

    def test_the_report_flags_it_for_human_review(self, tmp_path):
        report = render_report(
            _review(tmp_path, execution=ExecutionSettings(enabled=True), judgments=_ALREADY_PRESENT)
        )
        heading = "Defects said to be already present in the delivered code (needs human review):"
        assert heading in report
        after = report.split(heading, 1)[1]
        assert "line 2 already divides without interest" in after

    def test_the_block_is_absent_when_nothing_was_already_present(self, tmp_path):
        report = render_report(
            _review(tmp_path, execution=ExecutionSettings(enabled=True), judgments=_DECLINING)
        )
        assert "already present in the delivered code" not in report

    def test_no_model_call_decides_validity(self, tmp_path):
        """DR-171 Decision 3, structurally: after the descriptor is proposed,
        nothing asks a model whether the mutant is valid or whether it really
        breaks the requirement. The four checks in `validity.py` decide, and
        this pins that no second call creeps in between.
        """
        capture: list = []
        _review(tmp_path, execution=ExecutionSettings(enabled=True), capture=capture)
        schemas = _schemas(capture)

        # One call per defect, and this fixture has one defect. A second would
        # mean the mutant was proposed and then asked about again.
        assert schemas.count("_Descriptor") == 1

        # Nothing at all between proposing the mutant and the first stage that
        # comes after the execution tier. The stages further down (`_Coverage`,
        # `_Detections`, `_Recommendations`) are the ordinary rest of the
        # review, and they run whether or not execution did.
        next_call = schemas[schemas.index("_Descriptor") + 1]
        assert next_call == "_Coverage", (
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
        capture: list = []
        _review(tmp_path, execution=ExecutionSettings(enabled=False), capture=capture)
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
        review = _review(tmp_path, execution=ExecutionSettings(enabled=True))
        (attempt,) = review.mutation_attempts
        assert attempt.descriptor is not None
        assert "* 3" in attempt.descriptor.replacement

    def test_the_report_shows_the_injected_text(self, tmp_path):
        report = render_report(_review(tmp_path, execution=ExecutionSettings(enabled=True)))
        assert "Defects injected, and which tests caught them:" in report
        assert "payment = principal / months * 3" in report

    def test_the_report_shows_what_the_edit_replaced(self, tmp_path):
        """Removed and added lines both render, as a diff reads."""
        report = render_report(_review(tmp_path, execution=ExecutionSettings(enabled=True)))
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
            _review(tmp_path, execution=ExecutionSettings(enabled=True), judgments=deleting)
        )
        assert "      -     payment = principal / months" in report
        assert "(lines deleted)" in report

    def test_the_report_says_no_test_caught_it(self, tmp_path):
        report = render_report(_review(tmp_path, execution=ExecutionSettings(enabled=True)))
        assert "no test caught it" in report

    def test_the_executed_verdicts_are_stored(self, tmp_path):
        """A stored review has to be able to reproduce its own rating, and
        several criteria rest on the executed half."""
        review = _review(tmp_path, execution=ExecutionSettings(enabled=True))
        assert [v.tier for v in review.pair_verdicts] == [EvidenceTier.DEFECT_KILLED]

    def test_a_set_aside_test_is_stored_and_reported(self, tmp_path):
        review = _review(
            tmp_path,
            execution=ExecutionSettings(enabled=True, allow_failing_tests=True),
            head_test=TestTheHaltGate._RED_TEST,
        )
        assert [t.test_id for t in review.set_aside_tests] == [
            "test_loan.py::test_that_is_already_failing"
        ]
        report = render_report(review)
        assert "Candidate tests set aside" in report
        assert "test_that_is_already_failing" in report


class TestTheHaltGate:
    _RED_TEST = (
        _TEST
        + """

def test_that_is_already_failing():
    assert amortize(1200.0, 12)[0] == 999.0
"""
    )

    def test_a_red_candidate_test_halts_the_review(self, tmp_path):
        with pytest.raises(ReviewHalted) as raised:
            _review(
                tmp_path,
                execution=ExecutionSettings(enabled=True),
                head_test=self._RED_TEST,
            )
        assert "test_that_is_already_failing" in raised.value.baseline.halt_reason

    def test_the_override_sets_it_aside_and_carries_on(self, tmp_path):
        review = _review(
            tmp_path,
            execution=ExecutionSettings(enabled=True, allow_failing_tests=True),
            head_test=self._RED_TEST,
        )
        (obligation,) = [o for o in review.obligation_map if o.id == "equal-payments"]
        assert obligation.achieved_evidence_tier is EvidenceTier.DEFECT_KILLED

    def test_a_halt_records_no_attempt_and_renders_no_report(self, tmp_path):
        """#45's Gate 2 asked for the halted case alongside the
        execution-disabled one. Nothing was injected, so there is no injected
        text to record — and no review object either, which is the point of
        raising rather than returning one.
        """
        with pytest.raises(ReviewHalted) as raised:
            _review(
                tmp_path,
                execution=ExecutionSettings(enabled=True),
                head_test=self._RED_TEST,
            )
        assert raised.value.baseline.failing_tests
        assert raised.value.baseline.usable_tests == []

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
                enabled=True, sandbox=SandboxConfig(interpreter="/nonexistent/python")
            ),
            capture=capture,
        )
        assert "_Descriptor" not in _schemas(capture)

    def test_the_defects_still_fall_back_to_the_static_judge(self, tmp_path):
        capture: list = []
        review = _review(
            tmp_path,
            execution=ExecutionSettings(
                enabled=True, sandbox=SandboxConfig(interpreter="/nonexistent/python")
            ),
            capture=capture,
        )
        assert all(a.outcome is MutationOutcomeKind.NOT_ATTEMPTED for a in review.mutation_attempts)
        assert "_PairVerdicts" in _schemas(capture)

    def test_a_halt_costs_nothing_downstream(self, tmp_path):
        """The halt is a refusal to spend. If the pair stage still ran, halting
        would cost more than continuing and the gate would be pointless."""
        capture: list = []
        with pytest.raises(ReviewHalted):
            _review(
                tmp_path,
                execution=ExecutionSettings(enabled=True),
                head_test=self._RED_TEST,
                capture=capture,
            )
        assert "_PairVerdicts" not in _schemas(capture)
        assert "_Descriptor" not in _schemas(capture)

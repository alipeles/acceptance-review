"""What the tests did under an injected edit never reaches a model, or review state.

The mandate's constraint, and the reason for it: roughly half the edits the
edit-building model writes do not make the named defect true. So a test's
reaction to one says nothing reliable about the defect, and a later stage shown
that reaction would be anchored on a fact that is wrong about half the time.

`tests/test_unverified_mutation_is_inert.py::TestThroughTheWholeReview::test_the_static_judge_is_told_nothing_about_the_edit`
already guards one half of this, by asserting the injected replacement and the
words "killed" and "injected" are absent from the judge's request. **That test
cannot see the case this file exists for.** It looks for one fixture's literal
edit text; failure output produced *under* that edit contains none of those
words, so it would pass while the constraint was broken.

The gap is live rather than theoretical. `TestOutcome.detail` records what pytest
said a failure was, and it is populated for mutation runs as well as for the
baseline. Nothing today copies it out of the runner — `MutationAttempt` carries
test ids and no failure text — so the constraint holds by what the code does not
do rather than by anything preventing it. Adding a field to explain a survival,
or putting the set-aside block into a prompt for context, would cross the line
with no existing test failing.

So the assertion here is the positive rule, over a string that can ONLY exist if
a mutant run's output escaped: the candidate test below reports the payment it
observed, and the injected edit triples it. `observed-payment 300.0` appears
nowhere in the source, nowhere in the diff, and nowhere in the unmutated run —
only in the text of a failure under the edit.
"""

from __future__ import annotations

import subprocess

import pytest

from acceptance.change.diff import extract_change_set
from acceptance.mutation.settings import ExecutionSettings
from acceptance.pipeline import run_review
from acceptance.report import render_report
from tests.support import client_dispatching

#: Only ever produced by running the candidate test against the tripled payment.
#: The source carries `{schedule[0]}`, not the value, so a match is an escape.
_MARKER = "observed-payment 300.0"

_TASK = (
    "# Task\nThe schedule pays the loan off in equal monthly payments.\n\n"
    "## Constraints\n- Every monthly payment is the same amount\n"
)

_BASE = "def amortize(principal, months):\n    raise NotImplementedError\n"

_HEAD = """def amortize(principal, months):
    payment = principal / months
    return [payment for _ in range(months)]
"""

#: Fails under the edit, and says what it saw when it does. The message is
#: computed, so the value only exists in the failure, never in the source.
_TEST = """from loan import amortize


def test_each_payment_is_the_loan_over_the_term():
    schedule = amortize(1200.0, 12)
    assert schedule[0] == 100.0, f"observed-payment {schedule[0]}"
"""

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
    # Triples the payment, so the candidate test fails and reports 300.0.
    "_Descriptor": {
        "code_currently_does": "expected",
        "region_label": "loan.py#0",
        "start_line": 2,
        "end_line": 2,
        "replacement": "    payment = principal / months * 3\n",
        "decline": "none",
        "reason": "",
    },
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


def _review(repo, *, execution, capture=None):
    root, base, head = repo
    return run_review(
        task_text=_TASK,
        change_set=extract_change_set(root, base, head),
        repo=root,
        client=client_dispatching(_JUDGMENTS, capture=capture),
        reviewed_revision=head,
        execution=execution,
    )


@pytest.fixture(params=[False, True], ids=["unverified", "verified"])
def verify_edits(request):
    """Both halves of the tier.

    Unverified is today's default and the case where the result is not evidence
    at all. Verified is the case where it IS evidence about the defect — and
    still not something to show a model, because the constraint is about the
    judge reaching its own conclusion rather than about the result's tier.
    """
    return request.param


class TestTheEditsResultsStayInTheRunner:
    def test_the_fixture_really_produces_the_string(self, repo, verify_edits):
        """Not a claim about the feature — a check that the other assertions can
        fail at all. Without it they pass on a run where the test never failed
        under the edit and the string was never produced anywhere."""
        review = _review(repo, execution=ExecutionSettings(verify_edits=verify_edits))
        (attempt,) = review.mutation_attempts
        assert attempt.killing_tests == [
            "test_loan.py::test_each_payment_is_the_loan_over_the_term"
        ]
        assert _MARKER not in _TEST, "the marker must not be in the source, or it proves nothing"

    def test_no_model_request_carries_it(self, repo, verify_edits):
        """Asserted over EVERY request the review issued, not just the pair
        judge's. A later stage shown a mutant's output is anchored on a fact that
        is wrong about half the time, and which stage that is does not matter."""
        capture: list = []
        _review(
            repo,
            execution=ExecutionSettings(verify_edits=verify_edits),
            capture=capture,
        )
        assert capture, "no model call was made, so this asserts nothing"
        offenders = [call["schema"] for call in capture if _MARKER in call["prompt"]]
        assert offenders == []

    def test_persisted_review_state_does_not_carry_it(self, repo, verify_edits):
        """Review state is the other way it could reach a model: a later run
        reads it back, and anything in it can be rendered into a prompt."""
        review = _review(repo, execution=ExecutionSettings(verify_edits=verify_edits))
        assert _MARKER not in review.model_dump_json()

    def test_the_report_does_not_carry_it(self, repo, verify_edits):
        """The rendered report is an input to whoever reads it, including a
        later agent. What a test printed under an edit is not a fact about the
        defect and must not be presented as one."""
        report = render_report(
            _review(repo, execution=ExecutionSettings(verify_edits=verify_edits))
        )
        assert _MARKER not in report

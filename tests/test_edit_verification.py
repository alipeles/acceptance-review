"""Edit verification asks two questions in sequence (#335).

The first asks whether the edit changes behaviour at all, and is not shown the
defect. The second, asked only about an edit that does change behaviour, asks
whether the code went from the defect's expected behaviour to its defective one.
Each refusal names the question that made it.

Pipeline wiring is `tests/test_mutation_pipeline_wiring.py::TestVerification`;
these call `verify_edits` directly, to pin what each question decides.
"""

from __future__ import annotations

import pytest

from acceptance.mutation.attempt import MutationDescriptor, VerificationStep
from acceptance.mutation.verification import verify_edits
from acceptance.review_state import Defect, DefectType
from tests.support import client_dispatching

_SOURCE = """def amortize(principal, months):
    # one equal share per month
    payment = principal / months
    return [payment for _ in range(months)]
"""

_DEFECT = Defect(
    id="equal-payments/wrong-payment-amount",
    obligation_id="equal-payments",
    type=DefectType.OTHER,
    description="The payment amount is wrong, so the loan is not repaid.",
    expected_behavior="each payment is the principal divided by the months",
    defective_behavior="each payment is some other amount",
)


def _edit(replacement: str, start: int = 3, end: int = 3) -> MutationDescriptor:
    original = "".join(_SOURCE.splitlines(keepends=True)[start - 1 : end])
    return MutationDescriptor(
        path="loan.py",
        start_line=start,
        end_line=end,
        replacement=replacement,
        region_label="loan.py#0",
        original=original,
    )


_TRIPLED = _edit("    payment = principal / months * 3\n")


def _verify(edit: MutationDescriptor, answers: dict, capture: list | None = None):
    (verdict,) = verify_edits(
        [(_DEFECT, edit, _SOURCE)], client_dispatching(answers, capture=capture)
    )
    return verdict


def _schemas(capture: list) -> list[str]:
    return [call["schema"] for call in capture]


_CHANGES = {"changes_behaviour": "changes", "reason": "line 3 now triples it"}
_MATCHES = {"before_does": "expected", "after_does": "defective", "reason": "line 3"}


class TestTheFirstQuestion:
    @pytest.mark.parametrize(
        "replacement",
        [
            pytest.param("    payment = principal / months  # tripled? no\n", id="a comment"),
            pytest.param("    payment   =   principal/months\n", id="whitespace"),
        ],
    )
    def test_an_edit_to_comments_or_whitespace_is_refused_with_no_model_call(self, replacement):
        capture: list = []
        verdict = _verify(_edit(replacement), {}, capture)
        assert verdict.verified is False
        assert verdict.refused_by is VerificationStep.BEHAVIOUR_CHANGE
        assert capture == []

    def test_deleting_a_comment_line_is_refused_with_no_model_call(self):
        capture: list = []
        verdict = _verify(_edit("", start=2, end=2), {}, capture)
        assert verdict.refused_by is VerificationStep.BEHAVIOUR_CHANGE
        assert capture == []

    def test_moving_a_statement_out_of_its_block_is_put_to_the_model(self):
        """Indentation is structure in Python. Stripping whitespace must not make
        a dedented statement look identical to the original."""
        capture: list = []
        _verify(_edit("payment = principal / months\n"), {"_Verification": _MATCHES}, capture)
        assert "_BehaviourChange" in _schemas(capture)

    def test_an_edit_the_model_says_changes_nothing_is_refused_there(self):
        capture: list = []
        verdict = _verify(
            _TRIPLED,
            {"_BehaviourChange": {"changes_behaviour": "no_change", "reason": "x"}},
            capture,
        )
        assert verdict.verified is False
        assert verdict.refused_by is VerificationStep.BEHAVIOUR_CHANGE
        assert "_Verification" not in _schemas(capture), "the second question is not asked"

    def test_cannot_tell_goes_on_to_the_second_question(self):
        capture: list = []
        verdict = _verify(
            _TRIPLED,
            {
                "_BehaviourChange": {"changes_behaviour": "cannot_tell", "reason": "x"},
                "_Verification": _MATCHES,
            },
            capture,
        )
        assert _schemas(capture) == ["_BehaviourChange", "_Verification"]
        assert verdict.verified is True

    def test_it_is_not_shown_the_defect(self):
        capture: list = []
        _verify(_TRIPLED, {"_BehaviourChange": _CHANGES, "_Verification": _MATCHES}, capture)
        (prompt,) = [c["prompt"] for c in capture if c["schema"] == "_BehaviourChange"]
        assert _DEFECT.description not in prompt
        assert _DEFECT.expected_behavior not in prompt
        assert _DEFECT.defective_behavior not in prompt

    def test_it_is_shown_the_code_without_comments(self):
        capture: list = []
        _verify(_TRIPLED, {"_BehaviourChange": _CHANGES, "_Verification": _MATCHES}, capture)
        (prompt,) = [c["prompt"] for c in capture if c["schema"] == "_BehaviourChange"]
        assert "payment = principal / months * 3" in prompt
        assert "one equal share per month" not in prompt


class TestTheSecondQuestion:
    def test_expected_before_and_defective_after_is_verified(self):
        verdict = _verify(_TRIPLED, {"_BehaviourChange": _CHANGES, "_Verification": _MATCHES})
        assert verdict.verified is True
        assert verdict.refused_by is None

    @pytest.mark.parametrize(
        ("before", "after"),
        [
            pytest.param("defective", "defective", id="code already had the defect"),
            pytest.param("defective", "expected", id="the edit repairs it"),
            pytest.param("expected", "other", id="changes something else"),
            pytest.param("expected", "expected", id="still expected"),
            pytest.param("cannot_tell", "defective", id="before undecided"),
            pytest.param("expected", "cannot_tell", id="after undecided"),
        ],
    )
    def test_anything_else_is_refused_by_the_second_question(self, before, after):
        verdict = _verify(
            _TRIPLED,
            {
                "_BehaviourChange": _CHANGES,
                "_Verification": {"before_does": before, "after_does": after, "reason": "x"},
            },
        )
        assert verdict.verified is False
        assert verdict.refused_by is VerificationStep.DEFECT_MATCH

    def test_it_is_shown_the_defect_and_the_edit(self):
        capture: list = []
        _verify(_TRIPLED, {"_BehaviourChange": _CHANGES, "_Verification": _MATCHES}, capture)
        (prompt,) = [c["prompt"] for c in capture if c["schema"] == "_Verification"]
        assert _DEFECT.defective_behavior in prompt
        assert "payment = principal / months * 3" in prompt

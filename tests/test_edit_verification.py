"""Edit verification: one model call, and one refusal made without it.

An edit whose code is identical once comments and whitespace are removed is
refused with no model call. Every other edit is put to one call, which asks
whether the code went from the defect's expected behaviour to its defective one.
Each refusal records which of the two refused it.

#335 put a second model call in front of that one, asking whether the edit
changed behaviour at all. It was removed on 2026-09-23: on audit v10 it refused
none of the 52 edits and missed all four that change no behaviour. The tests for
it went with it; what remains below is what the measurement supports.

Pipeline wiring is `tests/test_mutation_pipeline_wiring.py::TestVerification`;
these call `verify_edits` directly.
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


_MATCHES = {"before_does": "expected", "after_does": "defective", "reason": "line 3"}


class TestTheRefusalMadeWithoutAModelCall:
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
        assert _schemas(capture) == ["_Verification"]


class TestTheModelCall:
    def test_it_is_the_only_call_verification_makes(self):
        capture: list = []
        _verify(_TRIPLED, {"_Verification": _MATCHES}, capture)
        assert _schemas(capture) == ["_Verification"]

    def test_expected_before_and_defective_after_is_verified(self):
        verdict = _verify(_TRIPLED, {"_Verification": _MATCHES})
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
    def test_anything_else_is_refused(self, before, after):
        verdict = _verify(
            _TRIPLED,
            {"_Verification": {"before_does": before, "after_does": after, "reason": "x"}},
        )
        assert verdict.verified is False
        assert verdict.refused_by is VerificationStep.DEFECT_MATCH

    def test_it_is_shown_the_defect_and_the_edit(self):
        capture: list = []
        _verify(_TRIPLED, {"_Verification": _MATCHES}, capture)
        (prompt,) = [c["prompt"] for c in capture if c["schema"] == "_Verification"]
        assert _DEFECT.defective_behavior in prompt
        assert "payment = principal / months * 3" in prompt

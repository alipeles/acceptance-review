"""M5.3 acceptance: classify each criterion's §9.3 evidence strength.

Archetype #3 -> superficial test yields Nominal for the rules it never checks;
archetype #6 -> the mocked-out core behavior is Nominal with the mock cited.
Each classification links to the exact mapped tests.

M5.3 is a deterministic reduce over M5.2's discrimination verdicts (no model
call), so these inject the verdicts and assert the resulting class directly.
"""

from acceptance.evidence.discrimination import ObligationDiscrimination, PlausibleDefect
from acceptance.evidence.strength import classify_strength
from acceptance.review_state import Obligation, ObligationType, TestEvidence


def _obligation(obligation_id: str) -> Obligation:
    return Obligation(
        id=obligation_id, description=f"{obligation_id} rule", type=ObligationType.FUNCTIONAL,
        importance="critical", explicit=True, observable_behavior="...",
    )


def _evidence(identifier: str, obligation_ids: list[str], mocks: list[str] | None = None) -> TestEvidence:
    return TestEvidence(
        identifier=identifier, location=identifier.split("::", 1)[0],
        mapped_obligations=obligation_ids, mocks=mocks or [],
    )


def _disc(obligation_id: str, *caught: bool) -> ObligationDiscrimination:
    defects = [
        PlausibleDefect(description=f"defect {i}", would_be_caught=c, reason=".")
        for i, c in enumerate(caught)
    ]
    return ObligationDiscrimination(
        obligation_id=obligation_id, defects=defects,
        discriminating=any(caught),
    )


def _by_id(results):
    return {r.obligation_id: r for r in results}


# --- class-mapping branches ---


def test_all_defects_caught_is_strongly_supported():
    obs = [_obligation("ob")]
    ev = [_evidence("t.py::test", ["ob"])]
    result = classify_strength(obs, ev, [_disc("ob", True, True)])[0]
    assert result.evidence_class == "strongly_supported"
    assert result.test_links == ["t.py::test"]


def test_some_defects_caught_is_partially_supported():
    obs = [_obligation("ob")]
    ev = [_evidence("t.py::test", ["ob"])]
    result = classify_strength(obs, ev, [_disc("ob", True, False)])[0]
    assert result.evidence_class == "partially_supported"
    assert "not others" in result.explanation


def test_no_defects_caught_is_nominally_supported():
    obs = [_obligation("ob")]
    ev = [_evidence("t.py::test", ["ob"])]
    result = classify_strength(obs, ev, [_disc("ob", False, False)])[0]
    assert result.evidence_class == "nominally_supported"


def test_no_mapped_test_is_unsupported():
    obs = [_obligation("ob")]
    result = classify_strength(obs, [], [])[0]
    assert result.evidence_class == "unsupported"
    assert result.test_links == []


def test_mapped_test_but_no_defect_judged_is_indeterminate():
    obs = [_obligation("ob")]
    ev = [_evidence("t.py::test", ["ob"])]
    result = classify_strength(obs, ev, [_disc("ob")])[0]  # zero defects
    assert result.evidence_class == "indeterminate"


# --- archetype #3: superficial test ---


def test_archetype_3_superficial_test_classes():
    obs = [_obligation("one-per-month"), _obligation("equal-payments"), _obligation("fully-amortizing")]
    test_id = "test_loan.py::test_returns_a_payment_for_each_month"
    ev = [_evidence(test_id, ["one-per-month", "equal-payments", "fully-amortizing"])]
    discriminations = [
        # len(schedule)==12 catches a wrong-count defect.
        _disc("one-per-month", True),
        # the test never asserts payments are EQUAL -> that defect survives.
        _disc("equal-payments", False),
        # the test never asserts the loan is fully paid off -> survives.
        _disc("fully-amortizing", False),
    ]

    result = _by_id(classify_strength(obs, ev, discriminations))

    assert result["one-per-month"].evidence_class == "strongly_supported"
    assert result["equal-payments"].evidence_class == "nominally_supported"
    assert result["fully-amortizing"].evidence_class == "nominally_supported"
    assert result["equal-payments"].test_links == [test_id]


# --- archetype #6: mocked-out behavior, mock cited ---


def test_archetype_6_mocked_out_behavior_is_nominal_with_the_mock_cited():
    obs = [_obligation("select-rate"), _obligation("compute-coupon")]
    test_id = "test_coupon.py::test_coupon_uses_selected_rate"
    ev = [_evidence(test_id, ["select-rate", "compute-coupon"], mocks=["Mock"])]
    discriminations = [
        # rate_for is mocked to a constant -> the core select-by-date behavior
        # is bypassed; every defect survives.
        _disc("select-rate", False),
        # coupon(...) == 50.0 catches a multiplication defect, but rounding is
        # not exercised (50.0 is whole) -> partial.
        _disc("compute-coupon", True, False),
    ]

    result = _by_id(classify_strength(obs, ev, discriminations))

    assert result["select-rate"].evidence_class == "nominally_supported"
    assert "Mock" in result["select-rate"].explanation  # the mock is cited
    assert result["compute-coupon"].evidence_class == "partially_supported"


def test_strength_round_trips():
    obs = [_obligation("ob")]
    ev = [_evidence("t.py::test", ["ob"])]
    result = classify_strength(obs, ev, [_disc("ob", True)])[0]
    from acceptance.evidence.strength import EvidenceStrength

    assert EvidenceStrength.from_dict(result.to_dict()) == result

"""M5.4 acceptance: each §9.4 weak-evidence pattern is correctly flagged with
its matching pattern name — the three code examples from the spec verbatim,
plus neutral fixtures for the three prose-described patterns.

Structural (no model call), so these assert real detections directly."""

from acceptance.evidence.discovery import DiscoveredTest, DiscoveryReason
from acceptance.evidence.discrimination import ObligationDiscrimination, PlausibleDefect
from acceptance.evidence.weak_patterns import WeakEvidencePattern, detect_weak_patterns
from acceptance.review_state import TestEvidence


def _test(test_id: str, source: str) -> DiscoveredTest:
    return DiscoveredTest(
        test_id=test_id, file=test_id.split("::", 1)[0],
        reasons=[DiscoveryReason.CALLS_CHANGED_SYMBOL], source=source,
    )


def _evidence(identifier: str, **kwargs) -> TestEvidence:
    return TestEvidence(identifier=identifier, location=identifier.split("::", 1)[0], **kwargs)


def _disc(obligation_id: str, *caught: bool) -> ObligationDiscrimination:
    defects = [
        PlausibleDefect(description=f"defect {i}", would_be_caught=c, reason=".")
        for i, c in enumerate(caught)
    ]
    return ObligationDiscrimination(obligation_id=obligation_id, defects=defects, discriminating=any(caught))


def _patterns(findings, test_id):
    return {f.pattern for f in findings if f.test_id == test_id}


# --- §9.4's own code examples, verbatim ---


def test_non_discriminating_assert_not_none():
    test_id = "t.py::test_result"
    source = (
        "def test_result():\n"
        "    result = calculate_coupon(input)\n"
        "    assert result is not None\n"
    )
    tests = [_test(test_id, source)]

    findings = detect_weak_patterns(tests, [], [])

    assert WeakEvidencePattern.NON_DISCRIMINATING_ASSERTION in _patterns(findings, test_id)


def test_circular_expected_value():
    test_id = "t.py::test_coupon"
    evidence = [_evidence(
        test_id,
        expected_value_provenance="Circular: both sides derive from calculate_coupon.",
    )]

    findings = detect_weak_patterns([], evidence, [])

    assert WeakEvidencePattern.CIRCULAR_EXPECTED_VALUE in _patterns(findings, test_id)


def test_incomplete_error_assertion():
    test_id = "t.py::test_error"
    source = (
        "def test_error():\n"
        "    with pytest.raises(Exception):\n"
        "        calculate_coupon(input_with_missing_rate)\n"
    )
    tests = [_test(test_id, source)]

    findings = detect_weak_patterns(tests, [], [])

    assert WeakEvidencePattern.INCOMPLETE_ERROR_ASSERTION in _patterns(findings, test_id)


def test_specific_exception_type_with_message_check_is_not_flagged():
    test_id = "t.py::test_error_specific"
    source = (
        "def test_error_specific():\n"
        "    with pytest.raises(MissingRateError) as exc:\n"
        "        calculate_coupon(input_with_missing_rate)\n"
        "    assert 'missing rate' in str(exc.value)\n"
    )
    tests = [_test(test_id, source)]

    findings = detect_weak_patterns(tests, [], [])

    assert WeakEvidencePattern.INCOMPLETE_ERROR_ASSERTION not in _patterns(findings, test_id)


# --- prose-described patterns, neutral fixtures ---


def test_requirement_not_exercised_no_mocks_nominal():
    # Archetype #4's shape: a nominal test whose INPUT coincides with the defect.
    test_id = "t.py::test_partial_month"
    evidence = [_evidence(test_id, mapped_obligations=["daily-rate"], mocks=[])]
    discriminations = [_disc("daily-rate", False, False)]

    findings = detect_weak_patterns([], evidence, discriminations)

    assert WeakEvidencePattern.REQUIREMENT_NOT_EXERCISED in _patterns(findings, test_id)
    assert WeakEvidencePattern.CRITICAL_BEHAVIOR_MOCKED not in _patterns(findings, test_id)


def test_critical_behavior_mocked_out_nominal_with_mocks():
    # Archetype #6's shape: mocking the component the obligation claims to test.
    test_id = "t.py::test_rate_selection"
    evidence = [_evidence(test_id, mapped_obligations=["select-rate"], mocks=["Mock"])]
    discriminations = [_disc("select-rate", False)]

    findings = detect_weak_patterns([], evidence, discriminations)

    assert WeakEvidencePattern.CRITICAL_BEHAVIOR_MOCKED in _patterns(findings, test_id)
    assert WeakEvidencePattern.REQUIREMENT_NOT_EXERCISED not in _patterns(findings, test_id)


def test_discriminating_test_is_not_flagged_nominal():
    test_id = "t.py::test_strong"
    evidence = [_evidence(test_id, mapped_obligations=["ob"], mocks=[])]
    discriminations = [_disc("ob", True, True)]  # all caught -> strongly supported

    findings = detect_weak_patterns([], evidence, discriminations)

    assert _patterns(findings, test_id) == set()


def test_unvalidated_snapshot():
    test_id = "t.py::test_output_unchanged"
    source = (
        "def test_output_unchanged(snapshot):\n"
        "    result = render(report)\n"
        "    assert result == snapshot\n"
    )
    tests = [_test(test_id, source)]

    findings = detect_weak_patterns(tests, [], [])

    assert WeakEvidencePattern.UNVALIDATED_SNAPSHOT in _patterns(findings, test_id)


def test_comparison_to_independently_derived_value_is_not_a_snapshot():
    test_id = "t.py::test_normal"
    source = "def test_normal():\n    assert calculate_total(10, 2) == 20\n"
    tests = [_test(test_id, source)]

    findings = detect_weak_patterns(tests, [], [])

    assert WeakEvidencePattern.UNVALIDATED_SNAPSHOT not in _patterns(findings, test_id)


def test_finding_round_trips():
    test_id = "t.py::test_result"
    source = "def test_result():\n    assert calc(1) is not None\n"
    finding = detect_weak_patterns([_test(test_id, source)], [], [])[0]
    from acceptance.evidence.weak_patterns import WeakEvidenceFinding

    assert WeakEvidenceFinding.from_dict(finding.to_dict()) == finding

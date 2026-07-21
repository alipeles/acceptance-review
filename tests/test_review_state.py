import json

import pytest

from acceptance.review_state import (
    BuilderDeclaration,
    ChangeSet,
    Component,
    EvidenceTier,
    ExecutionEvidence,
    Finding,
    Link,
    MandateInterpretation,
    Obligation,
    ObligationType,
    Project,
    Review,
    TaskSource,
    TestEvidence,
    TextSpan,
)


def _round_trip(instance):
    cls = type(instance)
    persisted = json.loads(json.dumps(instance.to_dict()))
    return cls.from_dict(persisted)


def test_project_round_trips():
    project = Project(
        repo="acceptance-tool",
        default_branch="main",
        test_framework="pytest",
        source_locations=["src/"],
        test_locations=["tests/"],
        test_command="pytest -q",
        execution_feasible=True,
        review_policy="advisory",
    )
    assert _round_trip(project) == project


def test_task_source_round_trips():
    task_source = TaskSource(
        kind="local_file",
        identifier="current-task.md",
        snapshot="abc123",
        text="## Deliverable\n...",
        references=["docs/spec.md"],
    )
    assert _round_trip(task_source) == task_source


def test_mandate_interpretation_round_trips():
    mandate = MandateInterpretation(
        interpreted_outcome="Add floating-rate bonds.",
        constraints=["Fixed-rate behavior must not change."],
        explicit_obligations=["Coupons use index + spread."],
        inferred_obligations=["Missing observations must error."],
        ambiguities=["Which index source applies?"],
        user_confirmations=[],
    )
    assert _round_trip(mandate) == mandate


def test_builder_declaration_round_trips():
    declaration = BuilderDeclaration(
        mandate_as_understood="...",
        implementation_summary="...",
        scope_exclusions="none",
        assumptions="...",
        changed_components="...",
        test_evidence="...",
        regression_evidence="...",
        known_limitations="...",
        additional_behavioral_changes="none",
    )
    assert _round_trip(declaration) == declaration


def test_change_set_round_trips():
    change_set = ChangeSet(
        base_revision="abc123",
        head_revision="def456",
        changed_files=["src/foo.py"],
        source_diff="--- a/src/foo.py\n+++ b/src/foo.py\n",
        test_diff="",
        config_dependency_changes=[],
    )
    assert _round_trip(change_set) == change_set


def test_obligation_round_trips_with_tier():
    obligation = Obligation(
        id="coupons-use-spread",
        description="Coupons use index + contractual spread.",
        type=ObligationType.FUNCTIONAL,
        importance="critical",
        explicit=True,
        observable_behavior="calculate_coupon returns index + spread",
        source_spans=[TextSpan(text="index curve plus contractual spread", start=20, end=55)],
        achieved_evidence_tier=EvidenceTier.STATIC,
        test_evidence=["test_coupon_uses_spread"],
    )
    assert _round_trip(obligation) == obligation


def test_obligation_round_trips_without_tier():
    obligation = Obligation(
        id="fixed-rate-unchanged",
        description="Fixed-rate results unchanged.",
        type=ObligationType.REGRESSION,
        importance="critical",
        explicit=True,
        observable_behavior="fixed-rate coupons identical to pre-change output",
    )
    assert obligation.achieved_evidence_tier is None
    assert _round_trip(obligation) == obligation


def test_test_evidence_round_trips():
    test_evidence = TestEvidence(
        identifier="tests/test_bond.py::test_coupon_uses_spread",
        location="tests/test_bond.py:42",
        inputs=["index=0.03", "spread=0.01"],
        fixtures=["bond_fixture"],
        assertions=["result == 0.04"],
        expected_value_provenance="hand-calculated",
        mocks=[],
        relevant_path=True,
        mapped_obligations=["Coupons use index + contractual spread."],
        static_assessment="strongly_supported",
    )
    assert _round_trip(test_evidence) == test_evidence


def test_execution_evidence_round_trips():
    execution_evidence = ExecutionEvidence(
        run_id="run-1",
        command="pytest tests/test_bond.py::test_coupon_uses_spread",
        result="pass",
        reviewed_revision="def456",
        coverage_of_obligation_lines=True,
        mutation_descriptor="flip index + spread to index - spread",
        outcome="killed",
    )
    assert _round_trip(execution_evidence) == execution_evidence


def test_finding_round_trips():
    finding = Finding(
        type="weak_test_evidence",
        severity="high",
        description="Test asserts only that a result exists.",
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="test", ref="tests/test_bond.py:42")],
        related_obligation="Coupons use index + contractual spread.",
        supporting_evidence=["tests/test_bond.py::test_coupon_uses_spread"],
        uncertainty=None,
        recommended_action="Add a discriminating-input test.",
    )
    assert _round_trip(finding) == finding


def test_finding_requires_evidence_tier():
    with pytest.raises(ValueError):
        Finding(
            type="weak_test_evidence",
            severity="high",
            description="...",
            evidence_tier=None,
            produced_by=Component.STATIC_ANALYZER,
            links=[Link(kind="test", ref="tests/test_bond.py:42")],
        )


def test_finding_requires_at_least_one_link():
    with pytest.raises(ValueError):
        Finding(
            type="weak_test_evidence",
            severity="high",
            description="...",
            evidence_tier=EvidenceTier.STATIC,
            produced_by=Component.STATIC_ANALYZER,
            links=[],
        )


def test_finding_cannot_be_constructed_without_evidence_tier_arg():
    with pytest.raises(ValueError):
        Finding(
            type="weak_test_evidence",
            severity="high",
            description="...",
            produced_by=Component.STATIC_ANALYZER,
            links=[Link(kind="test", ref="tests/test_bond.py:42")],
        )


def test_finding_cannot_be_constructed_without_links_arg():
    with pytest.raises(ValueError):
        Finding(
            type="weak_test_evidence",
            severity="high",
            description="...",
            evidence_tier=EvidenceTier.STATIC,
            produced_by=Component.STATIC_ANALYZER,
        )


def test_finding_requires_authorized_producer():
    with pytest.raises(ValueError):
        Finding(
            type="weak_test_evidence",
            severity="high",
            description="A static analyzer cannot claim a defect-killed tier.",
            evidence_tier=EvidenceTier.DEFECT_KILLED,
            produced_by=Component.STATIC_ANALYZER,
            links=[Link(kind="test", ref="tests/test_bond.py:42")],
        )


def test_review_round_trips_empty():
    review = Review(mode="local", reviewed_revision="def456")
    assert _round_trip(review) == review


def test_review_round_trips_populated():
    obligation = Obligation(
        id="coupons-use-spread",
        description="Coupons use index + contractual spread.",
        type=ObligationType.FUNCTIONAL,
        importance="critical",
        explicit=True,
        observable_behavior="...",
        achieved_evidence_tier=EvidenceTier.STATIC,
    )
    finding = Finding(
        type="weak_test_evidence",
        severity="high",
        description="...",
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="code", ref="src/bond.py:10")],
    )
    review = Review(
        mode="local",
        reviewed_revision="def456",
        mandate=MandateInterpretation(interpreted_outcome="Add floating-rate bonds."),
        declaration=None,
        change_set=ChangeSet(base_revision="abc123", head_revision="def456"),
        obligation_map=[obligation],
        findings=[finding],
        limitations=["Could not resolve dynamic dispatch in pricer.py"],
        recommendation="Add a discriminating-input test.",
    )
    assert _round_trip(review) == review


def test_review_evidence_tier_summary_is_derived_not_stored():
    obligation = Obligation(
        id="obligation-1",
        description="...",
        type=ObligationType.FUNCTIONAL,
        importance="critical",
        explicit=True,
        observable_behavior="...",
        achieved_evidence_tier=EvidenceTier.COVERAGE_CONFIRMED,
    )
    finding = Finding(
        type="weak_test_evidence",
        severity="high",
        description="...",
        evidence_tier=EvidenceTier.STATIC,
        produced_by=Component.STATIC_ANALYZER,
        links=[Link(kind="code", ref="src/bond.py:10")],
    )
    review = Review(
        mode="local",
        reviewed_revision="def456",
        obligation_map=[obligation],
        findings=[finding],
    )

    assert review.evidence_tier_summary() == {"COVERAGE_CONFIRMED": 1, "STATIC": 1}
    assert "evidence_tiers" not in review.to_dict()

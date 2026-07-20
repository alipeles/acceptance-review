import pytest

from acceptance.evidence_tier import (
    Component,
    EvidenceTier,
    UnauthorizedTierError,
    authorize_tier,
)


def test_evidence_tier_ordering():
    assert EvidenceTier.BUILDER_CLAIM < EvidenceTier.STATIC
    assert EvidenceTier.STATIC < EvidenceTier.COVERAGE_CONFIRMED
    assert EvidenceTier.COVERAGE_CONFIRMED < EvidenceTier.DEFECT_KILLED
    assert EvidenceTier.DEFECT_KILLED < EvidenceTier.CI_CONFIRMED


def test_static_analyzer_cannot_produce_defect_killed():
    with pytest.raises(UnauthorizedTierError):
        authorize_tier(Component.STATIC_ANALYZER, EvidenceTier.DEFECT_KILLED)


@pytest.mark.parametrize(
    ("component", "max_tier"),
    [
        (Component.BUILDER_DECLARATION, EvidenceTier.BUILDER_CLAIM),
        (Component.STATIC_ANALYZER, EvidenceTier.STATIC),
        (Component.COVERAGE_RUNNER, EvidenceTier.COVERAGE_CONFIRMED),
        (Component.MUTATION_RUNNER, EvidenceTier.DEFECT_KILLED),
        (Component.CI_INGESTION, EvidenceTier.CI_CONFIRMED),
    ],
)
def test_component_authorized_up_to_its_own_ceiling(component, max_tier):
    for tier in EvidenceTier:
        if tier <= max_tier:
            assert authorize_tier(component, tier) == tier
        else:
            with pytest.raises(UnauthorizedTierError):
                authorize_tier(component, tier)


def test_unauthorized_tier_error_is_a_value_error():
    assert issubclass(UnauthorizedTierError, ValueError)

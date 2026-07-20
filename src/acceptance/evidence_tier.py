"""Evidence-tier primitives (§8.1).

`EvidenceTier` orders the evidence ladder. `Component` names the parts of the
checker authorized to produce each tier, and `authorize_tier` enforces that a
component can't raise a Finding above its authorized ceiling — a static
analyzer can never emit `defect-killed` (CLAUDE.md invariant, M0.3).
"""

from __future__ import annotations

from enum import Enum, IntEnum


class EvidenceTier(IntEnum):
    """§8.1 evidence ladder, weakest to strongest."""

    BUILDER_CLAIM = 1
    STATIC = 2
    COVERAGE_CONFIRMED = 3
    DEFECT_KILLED = 4
    CI_CONFIRMED = 5


class Component(str, Enum):
    """The checker component authorized to produce a given evidence tier."""

    BUILDER_DECLARATION = "builder_declaration"
    STATIC_ANALYZER = "static_analyzer"
    COVERAGE_RUNNER = "coverage_runner"
    MUTATION_RUNNER = "mutation_runner"
    CI_INGESTION = "ci_ingestion"


_MAX_TIER_BY_COMPONENT: dict[Component, EvidenceTier] = {
    Component.BUILDER_DECLARATION: EvidenceTier.BUILDER_CLAIM,
    Component.STATIC_ANALYZER: EvidenceTier.STATIC,
    Component.COVERAGE_RUNNER: EvidenceTier.COVERAGE_CONFIRMED,
    Component.MUTATION_RUNNER: EvidenceTier.DEFECT_KILLED,
    Component.CI_INGESTION: EvidenceTier.CI_CONFIRMED,
}


class UnauthorizedTierError(ValueError):
    """Raised when a component attempts to produce a tier above its ceiling."""


def authorize_tier(component: Component, tier: EvidenceTier) -> EvidenceTier:
    max_tier = _MAX_TIER_BY_COMPONENT[component]
    if tier > max_tier:
        raise UnauthorizedTierError(
            f"{component.value} is not authorized to produce tier {tier.name} "
            f"(max: {max_tier.name})"
        )
    return tier

"""Review-state data model (§15).

Typed, persisted review state: obligations, mappings, findings, and evidence
tiers are explicit fields, not free text (CLAUDE.md invariant). Findings also
record which component produced them and are validated against that
component's authorized tier ceiling (evidence_tier.py, M0.3). Benchmark case
is out of scope (M-B0).

Schemas are pydantic models: validation and round-trip (de)serialization come
from the library rather than hand-rolled per class.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acceptance.evidence_tier import Component, EvidenceTier, authorize_tier
from acceptance.serialization import canonical_json

__all__ = [
    "Component",
    "EvidenceTier",
    "Project",
    "TaskSource",
    "MandateInterpretation",
    "BuilderDeclaration",
    "ChangeSet",
    "Obligation",
    "TestEvidence",
    "ExecutionEvidence",
    "Link",
    "Finding",
    "ReviewProvenance",
    "Review",
]


class _Model(BaseModel):
    """Base for all review-state schemas: strict fields, uniform persistence."""

    model_config = ConfigDict(extra="forbid")

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict):
        return cls.model_validate(data)


class Project(_Model):
    repo: str
    default_branch: str
    test_framework: str
    source_locations: list[str] = Field(default_factory=list)
    test_locations: list[str] = Field(default_factory=list)
    test_command: str | None = None
    execution_feasible: bool | None = None
    review_policy: str | None = None


class TaskSource(_Model):
    kind: Literal["local_file", "issue"]
    identifier: str
    snapshot: str
    text: str
    references: list[str] = Field(default_factory=list)


class MandateInterpretation(_Model):
    interpreted_outcome: str
    constraints: list[str] = Field(default_factory=list)
    explicit_obligations: list[str] = Field(default_factory=list)
    inferred_obligations: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    user_confirmations: list[str] = Field(default_factory=list)


class BuilderDeclaration(_Model):
    """The nine §7.4 template sections, as raw text."""

    mandate_as_understood: str
    implementation_summary: str
    scope_exclusions: str
    assumptions: str
    changed_components: str
    test_evidence: str
    regression_evidence: str
    known_limitations: str
    additional_behavioral_changes: str


class ChangeSet(_Model):
    base_revision: str
    head_revision: str
    changed_files: list[str] = Field(default_factory=list)
    source_diff: str = ""
    test_diff: str = ""
    config_dependency_changes: list[str] = Field(default_factory=list)


class Obligation(_Model):
    description: str
    type: str
    source_text: str
    importance: str
    explicit: bool
    observable_behavior: str
    achieved_evidence_tier: EvidenceTier | None = None
    test_evidence: list[str] = Field(default_factory=list)


class TestEvidence(_Model):
    __test__ = False  # not a pytest test class; name matches §15's "Test evidence"

    identifier: str
    location: str
    inputs: list[str] = Field(default_factory=list)
    fixtures: list[str] = Field(default_factory=list)
    assertions: list[str] = Field(default_factory=list)
    expected_value_provenance: str | None = None
    mocks: list[str] = Field(default_factory=list)
    relevant_path: bool | None = None
    mapped_obligations: list[str] = Field(default_factory=list)
    static_assessment: str | None = None


class ExecutionEvidence(_Model):
    run_id: str
    command: str
    result: Literal["pass", "fail", "skip"]
    reviewed_revision: str
    coverage_of_obligation_lines: bool | None = None
    mutation_descriptor: str | None = None
    outcome: Literal["killed", "survived"] | None = None


class Link(_Model):
    """A finding's link to exact requirement text / code lines / test locations."""

    kind: Literal["requirement", "code", "test"]
    ref: str
    text: str | None = None


class Finding(_Model):
    """Typed and linked (CLAUDE.md invariant): cannot be built without an
    evidence tier and at least one link target, and the producing component
    must be authorized for the claimed tier (§8.1, M0.3)."""

    type: str
    severity: str
    description: str
    evidence_tier: EvidenceTier
    produced_by: Component
    links: list[Link]
    related_obligation: str | None = None
    supporting_evidence: list[str] = Field(default_factory=list)
    uncertainty: str | None = None
    recommended_action: str | None = None

    @field_validator("links")
    @classmethod
    def _require_at_least_one_link(cls, value: list[Link]) -> list[Link]:
        if not value:
            raise ValueError("Finding requires at least one link target")
        return value

    @model_validator(mode="after")
    def _require_authorized_tier(self) -> "Finding":
        authorize_tier(self.produced_by, self.evidence_tier)
        return self


class ReviewProvenance(_Model):
    """How a review was produced (§13.6 trustworthiness). Stored so a reader
    can tell what determinism controls were in force — a fixed-seed replay is
    reproducible in a way a live sampled run is not, and M-B0.4's variance
    disclosure reads this. Mode is stored as its string value, not the harness
    `Mode` enum, so the data model stays independent of the LLM harness.
    """

    determinism_mode: Literal["record", "replay"]
    model: str
    temperature: float
    seed: int | None = None


class Review(_Model):
    mode: str
    reviewed_revision: str
    provenance: ReviewProvenance | None = None
    mandate: MandateInterpretation | None = None
    declaration: BuilderDeclaration | None = None
    change_set: ChangeSet | None = None
    obligation_map: list[Obligation] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    recommendation: str | None = None

    def to_canonical_json(self) -> str:
        """Byte-stable persisted form: identical review state serializes to
        identical bytes across runs (M0.5 acceptance). Distinct from the
        human-readable CLI report rendered in M0.6."""
        return canonical_json(self.to_dict())

    def evidence_tier_summary(self) -> dict[str, int]:
        """Tier counts derived from obligations/findings, not stored — the
        achieved tier lives on each Obligation/Finding; a separate stored
        copy here would be a second source of truth that can drift."""
        counts: dict[str, int] = {}
        for obligation in self.obligation_map:
            if obligation.achieved_evidence_tier is not None:
                key = obligation.achieved_evidence_tier.name
                counts[key] = counts.get(key, 0) + 1
        for finding in self.findings:
            key = finding.evidence_tier.name
            counts[key] = counts.get(key, 0) + 1
        return counts

"""Benchmark-case schema (§15 Benchmark case, §11.1 metrics; M-B0.1).

A case pairs a real (or offline-mutated, or hand-curated) input with
human-verified ground truth, so the checker's output can be scored against
it. The four ground-truth categories on `GroundTruthLabels` map directly to
§11.1's metrics:

    gaps          -> gap-detection recall / false-alarm precision
    decomposition -> obligation-decomposition accuracy
    mappings      -> test-to-obligation mapping accuracy
    evidence_classes -> evidence-classification agreement

`reviewer_output` and `score` start empty and are filled in by later
milestones (M-B0.2's checker-under-test runner, M-B0.3's scoring) — a case is
valid the moment it carries real ground truth, before it has ever been run.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from acceptance.model_base import PersistableModel
from acceptance.review_state import Review

# §9.3 test-evidence strength classifications. Distinct from EvidenceTier
# (evidence_tier.py), which grades *how* evidence was produced, not how
# strong it is.
EvidenceClassification = Literal[
    "strongly_supported",
    "partially_supported",
    "nominally_supported",
    "unsupported",
    "requires_other_evidence",
    "indeterminate",
]


class BenchmarkCaseSource(PersistableModel):
    kind: Literal["dataset", "real_pr", "mutant", "agent_run", "archetype"]
    identifier: str


class BenchmarkCaseInputs(PersistableModel):
    """What the checker-under-test runner (M-B0.2) feeds to the checker."""

    repo: str
    task_text: str
    base_revision: str
    head_revision: str
    declaration_text: str | None = None


class GroundTruthGap(PersistableModel):
    description: str
    obligation_ref: str | None = None
    severity: str | None = None


class GroundTruthDecompositionItem(PersistableModel):
    description: str
    explicit: bool


class GroundTruthMapping(PersistableModel):
    test_id: str
    obligation_ref: str


class GroundTruthEvidenceClass(PersistableModel):
    obligation_ref: str
    classification: EvidenceClassification


class GroundTruthLabels(PersistableModel):
    gaps: list[GroundTruthGap] = Field(default_factory=list)
    decomposition: list[GroundTruthDecompositionItem] = Field(default_factory=list)
    mappings: list[GroundTruthMapping] = Field(default_factory=list)
    evidence_classes: list[GroundTruthEvidenceClass] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_at_least_one_label(self) -> "GroundTruthLabels":
        if not (self.gaps or self.decomposition or self.mappings or self.evidence_classes):
            raise ValueError(
                "GroundTruthLabels requires at least one label "
                "(gaps, decomposition, mappings, or evidence_classes)"
            )
        return self


class BenchmarkScore(PersistableModel):
    """§11.1 metrics computed for a case, once scored (M-B0.3)."""

    gap_recall: float | None = None
    gap_precision: float | None = None
    decomposition_accuracy: float | None = None
    mapping_accuracy: float | None = None
    evidence_agreement: float | None = None


class BenchmarkCase(PersistableModel):
    case_id: str
    source: BenchmarkCaseSource
    inputs: BenchmarkCaseInputs
    ground_truth: GroundTruthLabels
    reviewer_output: Review | None = None
    score: BenchmarkScore | None = None

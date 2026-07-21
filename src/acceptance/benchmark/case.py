"""Benchmark-case schema (§15 Benchmark case, §11.1 metrics; M-B0.1, revised M-B5a.2).

A case pairs a real (or offline-mutated, or hand-curated) input with
human-verified ground truth, so the checker's output can be scored against
it.

The ground truth is an **obligation tree**: the obligation is the spine
(CLAUDE.md — "obligations are the spine everything maps to"), and each one
carries its own stable `id`, the tests relevant to it (`candidate_tests`), how
strong that evidence is (`evidence_class`, a §9.3 class), and why
(`evidence_rationale`). `gaps` are the findings a good reviewer should raise,
each linked to the obligation it concerns. This mirrors exactly the tree the
tool must show a user — obligation -> candidate tests -> evidence strength (with
a reason) — and makes the §11.1 metrics fall out of it:

    obligations                 -> obligation-decomposition accuracy
    obligation.candidate_tests  -> test-to-obligation mapping accuracy
    obligation.evidence_class   -> evidence-classification agreement
    gaps                        -> gap-detection recall / false-alarm precision

Identifiers, not prose, are the join keys: `obligation_id` on a gap and the
test ids in `candidate_tests` are validated to resolve, so ground truth can't
carry a dangling reference, an obligation with no evidence class, or a weak
result with no stated reason.

`reviewer_output` and `score` start empty and are filled in by the runner
(M-B0.2) and scorer (M-B0.3) — a case is valid the moment it carries real
ground truth, before it has ever been run.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from acceptance.model_base import PersistableModel
from acceptance.review_state import Review

# §9.3 test-evidence strength classifications. Distinct from EvidenceTier
# (evidence_tier.py), which grades *how* evidence was produced, not how strong
# it is. Defined over the plausible-violation space — the §8.2 mapped mutants —
# with one bright line: does the mapped test catch at least one plausible
# violation? These are static PREDICTIONS of which mutants a mapped test would
# kill, validated against executed ground truth (§8.2); that agreement is what
# §11.1 scores. Keep in sync with spec §9.3 (the full definitions live there):
#   strongly_supported      - kills all mapped mutants
#   partially_supported     - kills at least one, but not all, mapped mutants
#   nominally_supported     - a present, relevant-looking test survives all
#                             mapped mutants (zero discriminating power); with
#                             no relevant test it is unsupported, not nominal
#   unsupported             - no mapped, obligation-relevant test at all
#   requires_other_evidence - needs non-test evidence (docs, visual, deploy)
#   indeterminate           - cannot run / cannot decide statically
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


class GroundTruthObligation(PersistableModel):
    """One obligation in the expected decomposition, with the tests a reviewer
    would examine for it, its evidence strength, and why — a node in the
    obligation tree.

    `candidate_tests` are the tests relevant to this obligation (§9.1 "candidate
    tests"); a test can be a candidate yet establish nothing (mocked, circular,
    non-discriminating), which is exactly what `evidence_class` records.
    `evidence_rationale` states *why* the class is what it is — required so a
    weak or negative result can never appear without an explanation (§13.6)."""

    id: str
    description: str
    explicit: bool
    evidence_class: EvidenceClassification
    evidence_rationale: str
    candidate_tests: list[str] = Field(default_factory=list)  # test ids (pytest nodeids)


class GroundTruthGap(PersistableModel):
    """A finding a good reviewer should raise. `obligation_id` links it to the
    obligation it concerns, or is None when the gap is not about a task
    obligation (e.g. a declaration overclaim the task never requested)."""

    id: str
    description: str
    obligation_id: str | None = None
    severity: str | None = None


class GroundTruthLabels(PersistableModel):
    obligations: list[GroundTruthObligation] = Field(default_factory=list)
    gaps: list[GroundTruthGap] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_tree_integrity(self) -> "GroundTruthLabels":
        if not self.obligations:
            raise ValueError("GroundTruthLabels requires at least one obligation")

        obligation_ids = [o.id for o in self.obligations]
        if any(not oid.strip() for oid in obligation_ids):
            raise ValueError("every obligation id must be a non-empty string")
        if len(set(obligation_ids)) != len(obligation_ids):
            raise ValueError("obligation ids must be unique")

        gap_ids = [g.id for g in self.gaps]
        if any(not gid.strip() for gid in gap_ids):
            raise ValueError("every gap id must be a non-empty string")
        if len(set(gap_ids)) != len(gap_ids):
            raise ValueError("gap ids must be unique")

        known = set(obligation_ids)
        for gap in self.gaps:
            if gap.obligation_id is not None and gap.obligation_id not in known:
                raise ValueError(
                    f"gap {gap.id!r} references unknown obligation {gap.obligation_id!r}"
                )
        for obligation in self.obligations:
            if any(not test_id.strip() for test_id in obligation.candidate_tests):
                raise ValueError(
                    f"obligation {obligation.id!r} has an empty test id in candidate_tests"
                )
            if not obligation.evidence_rationale.strip():
                raise ValueError(
                    f"obligation {obligation.id!r} must have a non-empty evidence_rationale"
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
